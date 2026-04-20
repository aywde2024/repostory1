"""
File Tools - read_file, write_file, patch, search_files, list_dir
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from .registry import registry

# JSON Schema definitions
READ_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to file to read"}
    },
    "required": ["path"]
}

WRITE_FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to file to write"},
        "content": {"type": "string", "description": "Content to write"}
    },
    "required": ["path", "content"]
}

PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Path to file to patch"},
        "old_text": {"type": "string", "description": "Text to find and replace"},
        "new_text": {"type": "string", "description": "Replacement text"}
    },
    "required": ["path", "old_text", "new_text"]
}

LIST_DIR_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Directory path to list"},
        "recursive": {"type": "boolean", "description": "List recursively"}
    },
    "required": ["path"]
}

SEARCH_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {"type": "string", "description": "Search pattern (glob or regex)"},
        "path": {"type": "string", "description": "Base directory to search"},
        "file_pattern": {"type": "string", "description": "File name pattern to filter"}
    },
    "required": ["pattern"]
}


async def read_file_impl(path: str) -> Dict:
    """Read file content"""
    try:
        file_path = Path(path).expanduser()
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if not file_path.is_file():
            return {"success": False, "error": f"Not a file: {path}"}
        
        content = file_path.read_text(encoding='utf-8')
        return {"success": True, "output": content, "lines": len(content.splitlines())}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def write_file_impl(path: str, content: str) -> Dict:
    """Write file content"""
    try:
        file_path = Path(path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return {"success": True, "output": f"Written {len(content)} chars to {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def patch_file_impl(path: str, old_text: str, new_text: str) -> Dict:
    """Patch file content (find and replace)"""
    try:
        file_path = Path(path).expanduser()
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        
        content = file_path.read_text(encoding='utf-8')
        if old_text not in content:
            return {"success": False, "error": "Pattern not found in file"}
        
        new_content = content.replace(old_text, new_text, 1)
        file_path.write_text(new_content, encoding='utf-8')
        return {"success": True, "output": "File patched successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_dir_impl(path: str, recursive: bool = False) -> Dict:
    """List directory contents"""
    try:
        dir_path = Path(path).expanduser()
        if not dir_path.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        if not dir_path.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}
        
        entries = []
        if recursive:
            for item in dir_path.rglob('*'):
                rel_path = item.relative_to(dir_path)
                entry_type = "dir" if item.is_dir() else "file"
                entries.append({"path": str(rel_path), "type": entry_type})
        else:
            for item in dir_path.iterdir():
                entry_type = "dir" if item.is_dir() else "file"
                entries.append({"name": item.name, "type": entry_type})
        
        return {"success": True, "output": entries, "count": len(entries)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def search_files_impl(pattern: str, path: str = ".", file_pattern: str = None) -> Dict:
    """Search for text in files"""
    try:
        base_path = Path(path).expanduser()
        if not base_path.exists():
            return {"success": False, "error": f"Path not found: {path}"}
        
        results = []
        import re
        
        # Compile pattern as regex or use glob
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            is_regex = True
        except re.error:
            is_regex = False
        
        # Find matching files
        if file_pattern:
            files = list(base_path.rglob(file_pattern))
        else:
            files = list(base_path.rglob('*'))
        
        for file_path in files:
            if not file_path.is_file():
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                if is_regex:
                    matches = regex.findall(content)
                else:
                    matches = [pattern] if pattern.lower() in content.lower() else []
                
                if matches:
                    results.append({
                        "file": str(file_path.relative_to(base_path)),
                        "matches": len(matches)
                    })
            except Exception:
                continue
        
        return {"success": True, "output": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Register tools
registry.register(
    name="read_file",
    func=read_file_impl,
    schema=READ_FILE_SCHEMA,
    description="Read content of a file",
    toolsets=["file", "core"],
    platforms=["linux", "macos", "windows"],
)

registry.register(
    name="write_file",
    func=write_file_impl,
    schema=WRITE_FILE_SCHEMA,
    description="Write content to a file (creates parent directories)",
    toolsets=["file"],
    platforms=["linux", "macos", "windows"],
    dangerous=True,
)

registry.register(
    name="patch",
    func=patch_file_impl,
    schema=PATCH_SCHEMA,
    description="Find and replace text in a file",
    toolsets=["file"],
    platforms=["linux", "macos", "windows"],
    dangerous=True,
)

registry.register(
    name="list_dir",
    func=list_dir_impl,
    schema=LIST_DIR_SCHEMA,
    description="List directory contents",
    toolsets=["file"],
    platforms=["linux", "macos", "windows"],
)

registry.register(
    name="search_files",
    func=search_files_impl,
    schema=SEARCH_FILES_SCHEMA,
    description="Search for text pattern in files",
    toolsets=["file"],
    platforms=["linux", "macos", "windows"],
)
