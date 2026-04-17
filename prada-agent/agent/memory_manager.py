"""
Memory Manager - Handles built-in MEMORY.md and USER.md
Supports add, replace, remove operations with substring matching
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages PRADA's built-in two-layer memory system.
    
    - MEMORY.md: Agent personal notes (environment facts, project conventions, lessons)
    - USER.md: User profile (preferences, identity, habits)
    
    Features:
    - Substring-based entry matching for updates
    - Character limits with overflow handling
    - Thread-safe file operations
    - Automatic entry separation with § delimiter
    """
    
    def __init__(self, prada_home: Path):
        self.prada_home = prada_home
        self.memories_dir = prada_home / "memories"
        self.memory_file = self.memories_dir / "MEMORY.md"
        self.user_file = self.memories_dir / "USER.md"
        
        # Limits
        self.memory_char_limit = 2200
        self.user_char_limit = 1375
        
        # In-memory cache
        self._memory_entries: List[str] = []
        self._user_entries: List[str] = []
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize memory manager - create directories and load existing memories"""
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default files if they don't exist
        if not self.memory_file.exists():
            self.memory_file.write_text("", encoding='utf-8')
        
        if not self.user_file.exists():
            self.user_file.write_text("", encoding='utf-8')
        
        # Load existing entries
        await self._load_memories()
        
        logger.info("Memory manager initialized")
    
    async def _load_memories(self) -> None:
        """Load memory entries from disk"""
        async with self._lock:
            # Load MEMORY.md
            content = self.memory_file.read_text(encoding='utf-8')
            self._memory_entries = self._parse_entries(content)
            
            # Load USER.md
            content = self.user_file.read_text(encoding='utf-8')
            self._user_entries = self._parse_entries(content)
    
    def _parse_entries(self, content: str) -> List[str]:
        """Parse memory content into entries (split by §)"""
        if not content.strip():
            return []
        
        entries = []
        for line in content.split('\n'):
            line = line.strip()
            if line and line != '§':
                entries.append(line)
        
        return entries
    
    def _format_entries(self, entries: List[str]) -> str:
        """Format entries back to file content"""
        return '\n§\n'.join(entries)
    
    async def add(self, target: str, content: str) -> Dict:
        """
        Add new memory entry.
        
        Args:
            target: "memory" or "user"
            content: New entry content
            
        Returns:
            Result dict with success status and message
        """
        async with self._lock:
            if target == "memory":
                entries = self._memory_entries
                char_limit = self.memory_char_limit
            elif target == "user":
                entries = self._user_entries
                char_limit = self.user_char_limit
            else:
                return {"success": False, "error": f"Invalid target: {target}"}
            
            # Check character limit
            current_chars = sum(len(e) + 1 for e in entries)  # +1 for separator
            if current_chars + len(content) > char_limit:
                # Try to make room by removing oldest entries
                while entries and current_chars + len(content) > char_limit:
                    removed = entries.pop(0)
                    current_chars -= len(removed) + 1
                
                if current_chars + len(content) > char_limit:
                    return {
                        "success": False,
                        "error": f"Memory limit exceeded ({char_limit} chars). Remove some entries first."
                    }
            
            entries.append(content)
            
            # Save to disk
            await self._save(target)
            
            return {
                "success": True,
                "message": f"Added entry to {target}",
                "entry_count": len(entries),
            }
    
    async def replace(self, target: str, old_text: str, content: str) -> Dict:
        """
        Replace existing memory entry (substring match).
        
        Args:
            target: "memory" or "user"
            old_text: Unique substring to find the entry
            content: New content
            
        Returns:
            Result dict with success status
        """
        async with self._lock:
            if target == "memory":
                entries = self._memory_entries
            elif target == "user":
                entries = self._user_entries
            else:
                return {"success": False, "error": f"Invalid target: {target}"}
            
            # Find entry containing old_text
            found_idx = None
            for i, entry in enumerate(entries):
                if old_text in entry:
                    found_idx = i
                    break
            
            if found_idx is None:
                return {
                    "success": False,
                    "error": f"No entry found containing: {old_text}"
                }
            
            # Replace the entry
            entries[found_idx] = content
            
            # Save to disk
            await self._save(target)
            
            return {
                "success": True,
                "message": f"Replaced entry in {target}",
            }
    
    async def remove(self, target: str, old_text: str) -> Dict:
        """
        Remove memory entry (substring match).
        
        Args:
            target: "memory" or "user"
            old_text: Unique substring to find the entry
            
        Returns:
            Result dict with success status
        """
        async with self._lock:
            if target == "memory":
                entries = self._memory_entries
            elif target == "user":
                entries = self._user_entries
            else:
                return {"success": False, "error": f"Invalid target: {target}"}
            
            # Find entry containing old_text
            found_idx = None
            for i, entry in enumerate(entries):
                if old_text in entry:
                    found_idx = i
                    break
            
            if found_idx is None:
                return {
                    "success": False,
                    "error": f"No entry found containing: {old_text}"
                }
            
            # Remove the entry
            removed = entries.pop(found_idx)
            
            # Save to disk
            await self._save(target)
            
            return {
                "success": True,
                "message": f"Removed entry from {target}",
                "removed": removed[:50] + "..." if len(removed) > 50 else removed,
            }
    
    async def _save(self, target: str) -> None:
        """Save entries to disk"""
        if target == "memory":
            content = self._format_entries(self._memory_entries)
            self.memory_file.write_text(content, encoding='utf-8')
        elif target == "user":
            content = self._format_entries(self._user_entries)
            self.user_file.write_text(content, encoding='utf-8')
    
    def get_memory_content(self) -> str:
        """Get formatted MEMORY.md content"""
        return self._format_entries(self._memory_entries)
    
    def get_user_content(self) -> str:
        """Get formatted USER.md content"""
        return self._format_entries(self._user_entries)
    
    def get_all_memories(self) -> Dict[str, List[str]]:
        """Get all memory entries"""
        return {
            "memory": self._memory_entries.copy(),
            "user": self._user_entries.copy(),
        }
    
    def get_stats(self) -> Dict:
        """Get memory usage statistics"""
        memory_chars = sum(len(e) + 1 for e in self._memory_entries)
        user_chars = sum(len(e) + 1 for e in self._user_entries)
        
        return {
            "memory": {
                "entries": len(self._memory_entries),
                "chars": memory_chars,
                "limit": self.memory_char_limit,
                "usage_pct": round(memory_chars / self.memory_char_limit * 100, 1),
            },
            "user": {
                "entries": len(self._user_entries),
                "chars": user_chars,
                "limit": self.user_char_limit,
                "usage_pct": round(user_chars / self.user_char_limit * 100, 1),
            }
        }
    
    async def save(self) -> None:
        """Explicit save (called on shutdown)"""
        async with self._lock:
            await self._save("memory")
            await self._save("user")
    
    def search(self, query: str, target: Optional[str] = None) -> List[Dict]:
        """
        Search memories by keyword.
        
        Args:
            query: Search query (case-insensitive)
            target: "memory", "user", or None for both
            
        Returns:
            List of matching entries with metadata
        """
        results = []
        query_lower = query.lower()
        
        if target is None or target == "memory":
            for entry in self._memory_entries:
                if query_lower in entry.lower():
                    results.append({
                        "target": "memory",
                        "content": entry,
                    })
        
        if target is None or target == "user":
            for entry in self._user_entries:
                if query_lower in entry.lower():
                    results.append({
                        "target": "user",
                        "content": entry,
                    })
        
        return results
