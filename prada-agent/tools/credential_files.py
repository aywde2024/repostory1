"""
Credential Files Tool - Secure credential file passthrough
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


async def credential_files_impl(
    action: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
) -> dict:
    """
    Manage credential files securely.
    
    Args:
        action: One of "read", "write", "delete"
        file_path: Path to credential file
        content: File content (for write action)
        
    Returns:
        dict with success status and result
    """
    from tools.registry import registry
    
    if action == "read":
        if not file_path:
            return {"success": False, "error": "file_path required for read"}
        
        path = Path(file_path).expanduser()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Security check: only allow specific extensions
        allowed_extensions = {".env", ".key", ".pem", ".crt", ".txt"}
        if path.suffix not in allowed_extensions:
            return {"success": False, "error": f"Extension {path.suffix} not allowed"}
        
        try:
            content = path.read_text(encoding="utf-8")
            # Mask sensitive content in logs
            logger.info(f"Read credential file: {file_path}")
            return {"success": True, "output": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "write":
        if not file_path or not content:
            return {"success": False, "error": "file_path and content required for write"}
        
        path = Path(file_path).expanduser()
        
        # Security check
        allowed_extensions = {".env", ".key", ".pem", ".crt", ".txt"}
        if path.suffix not in allowed_extensions:
            return {"success": False, "error": f"Extension {path.suffix} not allowed"}
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            # Set secure permissions (owner read/write only)
            path.chmod(0o600)
            logger.info(f"Wrote credential file: {file_path}")
            return {"success": True, "output": f"Written to {file_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "delete":
        if not file_path:
            return {"success": False, "error": "file_path required for delete"}
        
        path = Path(file_path).expanduser()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        try:
            path.unlink()
            logger.info(f"Deleted credential file: {file_path}")
            return {"success": True, "output": f"Deleted {file_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# Register tool
CREDENTIAL_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["read", "write", "delete"],
            "description": "Action to perform"
        },
        "file_path": {
            "type": "string",
            "description": "Path to credential file"
        },
        "content": {
            "type": "string",
            "description": "File content (for write action)"
        }
    },
    "required": ["action"]
}

registry = None  # Will be set on import
try:
    from tools.registry import registry as _registry
    registry = _registry
    registry.register(
        name="credential_files",
        func=credential_files_impl,
        schema=CREDENTIAL_FILES_SCHEMA,
        description="Manage credential files securely",
        toolsets=["credentials", "core"],
        dangerous=True,
    )
except Exception:
    pass
