"""
Memory Tools - Memory operations for the agent
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def memory_add_impl(target: str, content: str) -> dict:
    """Add a new memory entry."""
    from agent.memory_manager import MemoryManager
    from pathlib import Path
    
    prada_home = Path.home() / ".prada"
    manager = MemoryManager(str(prada_home))
    await manager.initialize()
    
    result = await manager.add(target, content)
    return result


async def memory_replace_impl(target: str, old_text: str, content: str) -> dict:
    """Replace existing memory entry (substring match)."""
    from agent.memory_manager import MemoryManager
    from pathlib import Path
    
    prada_home = Path.home() / ".prada"
    manager = MemoryManager(str(prada_home))
    await manager.initialize()
    
    result = await manager.replace(target, old_text, content)
    return result


async def memory_remove_impl(target: str, old_text: str) -> dict:
    """Remove memory entry (substring match)."""
    from agent.memory_manager import MemoryManager
    from pathlib import Path
    
    prada_home = Path.home() / ".prada"
    manager = MemoryManager(str(prada_home))
    await manager.initialize()
    
    result = await manager.remove(target, old_text)
    return result


# Register tools
MEMORY_OPS_SCHEMA = {
    "type": "object",
    "properties": {
        "target": {"type": "string", "enum": ["memory", "user"], "description": "Target memory type"},
        "content": {"type": "string", "description": "Memory content"},
        "old_text": {"type": "string", "description": "Text to match for replace/remove"}
    },
    "required": ["target"]
}

try:
    from tools.registry import registry as _registry
    
    _registry.register(
        name="memory_add",
        func=memory_add_impl,
        schema={**MEMORY_OPS_SCHEMA, "required": ["target", "content"]},
        description="Add a new memory entry",
        toolsets=["memory_ops", "core"],
    )
    
    _registry.register(
        name="memory_replace",
        func=memory_replace_impl,
        schema={**MEMORY_OPS_SCHEMA, "required": ["target", "old_text", "content"]},
        description="Replace existing memory entry (substring match)",
        toolsets=["memory_ops", "core"],
    )
    
    _registry.register(
        name="memory_remove",
        func=memory_remove_impl,
        schema={**MEMORY_OPS_SCHEMA, "required": ["target", "old_text"]},
        description="Remove memory entry (substring match)",
        toolsets=["memory_ops", "core"],
    )
except Exception:
    pass
