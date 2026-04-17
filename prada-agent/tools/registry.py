"""
Tool Registry - Central tool registration and discovery
Auto-discovery pattern: tools register themselves on import
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central tool registry with auto-discovery pattern.
    
    Tools register themselves on module import, no central import list needed.
    Supports:
    - Dynamic availability checking
    - Toolset grouping
    - Platform restrictions
    - Environment variable requirements
    - Dangerous operation marking
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._toolsets = {}
            cls._instance._initialized = False
        return cls._instance
    
    def register(
        self,
        name: str,
        func: Callable,
        schema: dict,
        description: Optional[str] = None,
        toolsets: Optional[List[str]] = None,
        platforms: Optional[List[str]] = None,
        requires_env: Optional[List[str]] = None,
        dangerous: bool = False,
        check_fn: Optional[Callable] = None,
    ) -> None:
        """
        Register a tool.
        
        Args:
            name: Unique tool identifier
            func: Tool implementation function (sync or async)
            schema: JSON Schema for tool parameters
            description: Human-readable description
            toolsets: List of toolsets this tool belongs to
            platforms: OS/platform restrictions (linux, macos, windows)
            requires_env: Required environment variables
            dangerous: Whether tool requires approval
            check_fn: Optional availability check function
        """
        self._tools[name] = {
            "func": func,
            "schema": schema,
            "description": description or schema.get("description", ""),
            "toolsets": toolsets or [],
            "platforms": platforms,
            "requires_env": requires_env or [],
            "dangerous": dangerous,
            "check_fn": check_fn or (lambda: True),
        }
        
        # Add to toolsets
        for toolset in (toolsets or []):
            if toolset not in self._toolsets:
                self._toolsets[toolset] = []
            if name not in self._toolsets[toolset]:
                self._toolsets[toolset].append(name)
        
        logger.debug(f"Registered tool: {name}")
    
    async def initialize(self, toolsets: List[str]) -> None:
        """
        Initialize registry by importing tool modules.
        
        Args:
            toolsets: List of toolsets to load
        """
        if self._initialized:
            return
        
        # Import core tool modules
        await self._import_tool_modules()
        
        self._initialized = True
        logger.info(f"Tool registry initialized with {len(self._tools)} tools")
    
    async def _import_tool_modules(self) -> None:
        """Import all tool modules for auto-registration"""
        # File tools
        try:
            from tools import file_tools
        except ImportError as e:
            logger.warning(f"Could not import file_tools: {e}")
        
        # Web tools
        try:
            from tools import web_tools
        except ImportError as e:
            logger.warning(f"Could not import web_tools: {e}")
        
        # Terminal tool
        try:
            from tools import terminal_tool
        except ImportError as e:
            logger.warning(f"Could not import terminal_tool: {e}")
        
        # Code execution
        try:
            from tools import code_execution_tool
        except ImportError as e:
            logger.warning(f"Could not import code_execution_tool: {e}")
        
        # Browser tool
        try:
            from tools import browser_tool
        except ImportError as e:
            logger.warning(f"Could not import browser_tool: {e}")
        
        # Delegate tool
        try:
            from tools import delegate_tool
        except ImportError as e:
            logger.warning(f"Could not import delegate_tool: {e}")
        
        # MCP tool
        try:
            from tools import mcp_tool
        except ImportError as e:
            logger.warning(f"Could not import mcp_tool: {e}")
        
        # Credential files
        try:
            from tools import credential_files
        except ImportError as e:
            logger.warning(f"Could not import credential_files: {e}")
        
        # Memory operations
        try:
            from tools import memory_tools
        except ImportError as e:
            logger.warning(f"Could not import memory_tools: {e}")
        
        # Skill management
        try:
            from tools import skill_tools
        except ImportError as e:
            logger.warning(f"Could not import skill_tools: {e}")
        
        # Session tools
        try:
            from tools import session_tools
        except ImportError as e:
            logger.warning(f"Could not import session_tools: {e}")
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get tool function by name"""
        tool = self._tools.get(name)
        if not tool:
            return None
        return tool["func"]
    
    def get_tool_schema(self, name: str) -> Optional[dict]:
        """Get tool JSON schema by name"""
        tool = self._tools.get(name)
        if not tool:
            return None
        return tool["schema"]
    
    def get_tools_for_toolsets(self, toolsets: List[str]) -> List[dict]:
        """
        Get all tools for given toolsets in OpenAI function calling format.
        
        Returns list of:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        result = []
        seen = set()
        
        for toolset in toolsets:
            tool_names = self._toolsets.get(toolset, [])
            
            for name in tool_names:
                if name in seen:
                    continue
                seen.add(name)
                
                tool = self._tools.get(name)
                if not tool:
                    continue
                
                # Check availability
                if not tool["check_fn"]():
                    continue
                
                # Check platform
                if tool["platforms"]:
                    import sys
                    current_platform = sys.platform
                    platform_map = {"darwin": "macos", "win32": "windows", "linux": "linux"}
                    if platform_map.get(current_platform, current_platform) not in tool["platforms"]:
                        continue
                
                # Check required env vars
                if tool["requires_env"]:
                    import os
                    if not all(os.environ.get(var) for var in tool["requires_env"]):
                        continue
                
                result.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool["description"],
                        "parameters": tool["schema"],
                    }
                })
        
        return result
    
    def list_tools(self, toolsets: Optional[List[str]] = None) -> List[dict]:
        """List all registered tools with metadata"""
        result = []
        
        for name, tool in self._tools.items():
            # Filter by toolsets if specified
            if toolsets:
                if not any(ts in toolsets for ts in tool["toolsets"]):
                    continue
            
            result.append({
                "name": name,
                "description": tool["description"],
                "toolsets": tool["toolsets"],
                "dangerous": tool["dangerous"],
                "requires_env": tool["requires_env"],
                "platforms": tool["platforms"],
            })
        
        return result
    
    def list_toolsets(self) -> List[str]:
        """List all available toolsets"""
        return list(self._toolsets.keys())
    
    def get_toolset_tools(self, toolset: str) -> List[str]:
        """Get all tool names in a toolset"""
        return self._toolsets.get(toolset, [])
    
    def is_dangerous(self, tool_name: str) -> bool:
        """Check if tool is marked as dangerous"""
        tool = self._tools.get(tool_name)
        return tool.get("dangerous", False) if tool else False


# Global registry instance
registry = ToolRegistry()


def register_tool(
    name: str,
    schema: dict,
    toolsets: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
    requires_env: Optional[List[str]] = None,
    dangerous: bool = False,
):
    """
    Decorator for registering tools.
    
    Usage:
        @register_tool(
            name="read_file",
            schema=READ_FILE_SCHEMA,
            toolsets=["file", "core"],
        )
        async def read_file(path: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        registry.register(
            name=name,
            func=func,
            schema=schema,
            toolsets=toolsets,
            platforms=platforms,
            requires_env=requires_env,
            dangerous=dangerous,
        )
        return func
    
    return decorator
