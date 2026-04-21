"""
Skill Tools - Skill management operations
"""

import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


async def skills_list_impl() -> dict:
    """List all available skills (Level 0 - summary only)."""
    from pathlib import Path
    
    prada_home = Path.home() / ".prada"
    skills_dir = prada_home / "skills"
    
    skills = []
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    try:
                        content = skill_file.read_text(encoding="utf-8")
                        # Parse frontmatter
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 2:
                                import yaml
                                metadata = yaml.safe_load(parts[1])
                                skills.append({
                                    "name": metadata.get("name", skill_dir.name),
                                    "description": metadata.get("description", ""),
                                    "version": metadata.get("version", "0.0.0"),
                                    "category": metadata.get("metadata", {}).get("prada", {}).get("category", "general"),
                                })
                    except Exception as e:
                        logger.warning(f"Could not parse skill {skill_dir.name}: {e}")
    
    return {"success": True, "output": skills}


async def skill_view_impl(name: str, path: Optional[str] = None) -> dict:
    """View skill content (Level 1/2 - full content or specific file)."""
    prada_home = Path.home() / ".prada"
    skill_dir = prada_home / "skills" / name
    
    if not skill_dir.exists():
        return {"success": False, "error": f"Skill '{name}' not found"}
    
    if path:
        # Level 2: Load specific reference file
        file_path = skill_dir / path
        if not file_path.exists():
            return {"success": False, "error": f"File '{path}' not found in skill '{name}'"}
        
        try:
            content = file_path.read_text(encoding="utf-8")
            return {"success": True, "file_path": str(file_path), "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        # Level 1: Load full SKILL.md
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            return {"success": False, "error": f"SKILL.md not found for '{name}'"}
        
        try:
            content = skill_file.read_text(encoding="utf-8")
            
            # Parse frontmatter
            metadata = {}
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    metadata = yaml.safe_load(parts[1])
                    body = parts[2]
            
            # List references and templates
            references = []
            templates = []
            
            refs_dir = skill_dir / "references"
            if refs_dir.exists():
                references = [f.name for f in refs_dir.iterdir() if f.is_file()]
            
            templates_dir = skill_dir / "templates"
            if templates_dir.exists():
                templates = [f.name for f in templates_dir.iterdir() if f.is_file()]
            
            return {
                "success": True,
                "name": name,
                "metadata": metadata,
                "content": body.strip(),
                "references": references,
                "templates": templates,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def skill_manage_impl(
    action: str,
    name: Optional[str] = None,
    content: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    file_path: Optional[str] = None,
    file_content: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """Manage skills (create/patch/edit/delete/write_file/remove_file)."""
    prada_home = Path.home() / ".prada"
    skills_dir = prada_home / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    if action == "create":
        if not name or not content:
            return {"success": False, "error": "name and content required for create"}
        
        skill_dir = skills_dir / name
        if skill_dir.exists():
            return {"success": False, "error": f"Skill '{name}' already exists"}
        
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        
        # Create minimal frontmatter
        frontmatter = f"""---
name: {name}
description: Auto-generated skill
version: 1.0.0
metadata:
  prada:
    tags: [auto-generated]
    category: {category or "general"}
---

"""
        try:
            skill_file.write_text(frontmatter + content, encoding="utf-8")
            return {"success": True, "output": f"Created skill '{name}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "patch":
        if not name or not old_string or not new_string:
            return {"success": False, "error": "name, old_string, new_string required for patch"}
        
        skill_file = skills_dir / name / "SKILL.md"
        if not skill_file.exists():
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        try:
            content = skill_file.read_text(encoding="utf-8")
            if old_string not in content:
                return {"success": False, "error": "old_string not found in skill"}
            
            new_content = content.replace(old_string, new_string, 1)
            skill_file.write_text(new_content, encoding="utf-8")
            return {"success": True, "output": f"Patched skill '{name}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "edit":
        if not name or not content:
            return {"success": False, "error": "name and content required for edit"}
        
        skill_file = skills_dir / name / "SKILL.md"
        if not skill_file.exists():
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        try:
            skill_file.write_text(content, encoding="utf-8")
            return {"success": True, "output": f"Edited skill '{name}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "delete":
        if not name:
            return {"success": False, "error": "name required for delete"}
        
        skill_dir = skills_dir / name
        if not skill_dir.exists():
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        try:
            import shutil
            shutil.rmtree(skill_dir)
            return {"success": True, "output": f"Deleted skill '{name}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "write_file":
        if not name or not file_path or not file_content:
            return {"success": False, "error": "name, file_path, file_content required"}
        
        skill_dir = skills_dir / name
        if not skill_dir.exists():
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        try:
            target_file = skill_dir / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(file_content, encoding="utf-8")
            return {"success": True, "output": f"Written {file_path} to skill '{name}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    elif action == "remove_file":
        if not name or not file_path:
            return {"success": False, "error": "name and file_path required"}
        
        skill_dir = skills_dir / name
        if not skill_dir.exists():
            return {"success": False, "error": f"Skill '{name}' not found"}
        
        target_file = skill_dir / file_path
        if not target_file.exists():
            return {"success": False, "error": f"File '{file_path}' not found"}
        
        try:
            target_file.unlink()
            return {"success": True, "output": f"Removed {file_path} from skill '{name}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# Register tools
try:
    from tools.registry import registry as _registry
    
    _registry.register(
        name="skills_list",
        func=skills_list_impl,
        schema={"type": "object", "properties": {}, "description": "List all available skills"},
        description="List all available skills (Level 0 summary)",
        toolsets=["skills", "core"],
    )
    
    _registry.register(
        name="skill_view",
        func=skill_view_impl,
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name"},
                "path": {"type": "string", "description": "Optional file path within skill"}
            },
            "required": ["name"]
        },
        description="View skill content or specific file",
        toolsets=["skills", "core"],
    )
    
    _registry.register(
        name="skill_manage",
        func=skill_manage_impl,
        schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "patch", "edit", "delete", "write_file", "remove_file"]},
                "name": {"type": "string", "description": "Skill name"},
                "content": {"type": "string", "description": "Skill content"},
                "old_string": {"type": "string", "description": "Text to replace (for patch)"},
                "new_string": {"type": "string", "description": "Replacement text (for patch)"},
                "file_path": {"type": "string", "description": "File path within skill directory"},
                "file_content": {"type": "string", "description": "File content (for write_file)"},
                "category": {"type": "string", "description": "Skill category (for create)"}
            },
            "required": ["action"]
        },
        description="Manage skills (create/patch/edit/delete/write_file/remove_file)",
        toolsets=["skills", "core"],
        dangerous=True,
    )
except Exception:
    pass
