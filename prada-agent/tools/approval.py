"""
Command Approval System
Detects dangerous command patterns and requires user confirmation
"""

import re
from typing import Any, Dict, List, Optional


# Dangerous command patterns (extensible)
DANGEROUS_PATTERNS = [
    # Filesystem destruction
    r"rm\s+-rf\s+/",
    r"dd\s+if=.*of=/dev/",
    r"mkfs\.",
    r">\s*/dev/sd",
    
    # Database operations
    r"DROP\s+(TABLE|DATABASE)",
    r"DELETE\s+FROM\s+\w+\s*;",
    r"TRUNCATE\s+",
    
    # Permission changes
    r"chmod\s+777",
    r"chown\s+root",
    r"sudo\s+(passwd|visudo)",
    
    # Network/Firewall
    r"iptables\s+-F",
    r"systemctl\s+(disable|stop)\s+firewalld",
    r"ufw\s+(disable|reset)",
    
    # Process killing
    r"kill\s+-9\s+1",
    r"pkill\s+-9\s+init",
    r"killall\s+-9",
    
    # Credential exposure
    r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?[a-zA-Z0-9]{16,}",
    r"cat\s+.*\.env",
    r"echo\s+.*PASSWORD",
    
    # Disk operations
    r"fdisk\s+",
    r"parted\s+",
    r"lvremove",
    r"vgremove",
    
    # Container/VM destruction
    r"docker\s+rm\s+-f",
    r"kubectl\s+delete\s+--all",
    r"vagrant\s+destroy\s+-f",
]


# Tool-specific approval requirements
TOOL_APPROVAL_RULES = {
    "terminal": {
        "check_args": True,  # Check command content
        "patterns": DANGEROUS_PATTERNS,
    },
    "write_file": {
        "check_path": True,
        "dangerous_paths": ["/etc/", "/usr/", "/bin/", "/sbin/", "/boot/"],
    },
    "patch": {
        "check_path": True,
        "dangerous_paths": ["/etc/", "/usr/", "/bin/", "/sbin/"],
    },
    "execute_code": {
        "always_approve": False,  # Can be configured
    },
    "delegate": {
        "always_approve": True,  # Always require approval for subagent creation
    },
}


class ApprovalChecker:
    """
    Checks if tool execution requires user approval.
    
    Features:
    - Pattern matching for dangerous commands
    - Path-based checks for file operations
    - Configurable auto-approve patterns
    - Platform-specific rules
    """
    
    def __init__(self, auto_approve_patterns: Optional[List[str]] = None):
        self.auto_approve_patterns = auto_approve_patterns or []
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS
        ]
        self._auto_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.auto_approve_patterns
        ]
    
    def requires_approval(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        Check if tool execution requires approval.
        
        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments
            
        Returns:
            True if approval is required
        """
        # Check tool-specific rules
        rules = TOOL_APPROVAL_RULES.get(tool_name, {})
        
        # Always approve rules
        if rules.get("always_approve"):
            return True
        
        # Check auto-approve patterns first
        if self._matches_auto_approve(tool_name, tool_args):
            return False
        
        # Check dangerous patterns
        if rules.get("check_args") and tool_name == "terminal":
            command = tool_args.get("command", "")
            if self._is_dangerous_command(command):
                return True
        
        # Check dangerous paths
        if rules.get("check_path"):
            path = tool_args.get("path", "")
            dangerous_paths = rules.get("dangerous_paths", [])
            if any(path.startswith(dp) for dp in dangerous_paths):
                return True
        
        # Check if tool is inherently dangerous
        from tools.registry import registry
        if registry.is_dangerous(tool_name):
            return True
        
        return False
    
    def _matches_auto_approve(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """Check if command matches auto-approve patterns"""
        if not self._auto_compiled:
            return False
        
        # Get command string to check
        command = ""
        if tool_name == "terminal":
            command = tool_args.get("command", "")
        elif tool_name in ("write_file", "patch", "read_file"):
            command = f"{tool_name} {tool_args.get('path', '')}"
        else:
            command = tool_name
        
        # Check against auto-approve patterns
        for pattern in self._auto_compiled:
            if pattern.search(command):
                return True
        
        return False
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command matches dangerous patterns"""
        for pattern in self._compiled_patterns:
            if pattern.search(command):
                return True
        return False
    
    def get_danger_level(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Get danger level of operation.
        
        Returns: "safe", "caution", "dangerous", "critical"
        """
        if not self.requires_approval(tool_name, tool_args):
            return "safe"
        
        # Critical: filesystem destruction, database drops
        if tool_name == "terminal":
            command = tool_args.get("command", "")
            critical_patterns = [
                r"rm\s+-rf\s+/",
                r"DROP\s+DATABASE",
                r"mkfs\.",
                r">/dev/sd",
            ]
            for pattern in critical_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return "critical"
        
        # Dangerous: permission changes, service stops
        if tool_name == "terminal":
            command = tool_args.get("command", "")
            dangerous_patterns = [
                r"chmod\s+777",
                r"systemctl\s+stop",
                r"iptables",
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return "dangerous"
        
        # Caution: file writes, patches
        if tool_name in ("write_file", "patch"):
            return "caution"
        
        return "caution"
    
    def get_approval_message(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Generate human-readable approval request message"""
        danger_level = self.get_danger_level(tool_name, tool_args)
        
        if tool_name == "terminal":
            command = tool_args.get("command", "")
            return f"⚠️ Execute command ({danger_level}):\n```\n{command}\n```"
        
        elif tool_name == "write_file":
            path = tool_args.get("path", "")
            return f"⚠️ Write to file ({danger_level}):\n`{path}`"
        
        elif tool_name == "patch":
            path = tool_args.get("path", "")
            return f"⚠️ Patch file ({danger_level}):\n`{path}`"
        
        else:
            return f"⚠️ Execute {tool_name} ({danger_level})"


def check_approval_required(tool_name: str, tool_args: Dict[str, Any]) -> bool:
    """Convenience function for checking approval"""
    checker = ApprovalChecker()
    return checker.requires_approval(tool_name, tool_args)


def get_dangerous_patterns() -> List[str]:
    """Get list of dangerous patterns (for configuration)"""
    return DANGEROUS_PATTERNS.copy()
