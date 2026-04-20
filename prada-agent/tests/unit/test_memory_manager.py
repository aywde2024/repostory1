"""Unit tests for memory manager system"""

import pytest
import asyncio
import tempfile
from pathlib import Path


@pytest.fixture
def temp_prada_home():
    """Create temporary PRADA home directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_memory_manager_init(temp_prada_home):
    """Test memory manager initialization"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    assert (temp_prada_home / "memories").exists()
    assert (temp_prada_home / "memories" / "MEMORY.md").exists()
    assert (temp_prada_home / "memories" / "USER.md").exists()


@pytest.mark.asyncio
async def test_memory_add(temp_prada_home):
    """Test adding memory entries"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    await mm.add("memory", "Test entry 1")
    await mm.add("memory", "Test entry 2")
    
    assert len(mm._memory_entries) == 2
    assert "Test entry 1" in mm._memory_entries
    assert "Test entry 2" in mm._memory_entries


@pytest.mark.asyncio
async def test_user_add(temp_prada_home):
    """Test adding user profile entries"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    await mm.add("user", "User prefers dark mode")
    
    assert len(mm._user_entries) == 1
    assert "User prefers dark mode" in mm._user_entries


@pytest.mark.asyncio
async def test_memory_replace(temp_prada_home):
    """Test replacing memory entries via substring match"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    await mm.add("memory", "User likes Python")
    await mm.replace("memory", "Python", "User loves Rust")
    
    assert len(mm._memory_entries) == 1
    assert "User loves Rust" in mm._memory_entries


@pytest.mark.asyncio
async def test_memory_remove(temp_prada_home):
    """Test removing memory entries via substring match"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    await mm.add("memory", "Entry to remove")
    await mm.add("memory", "Entry to keep")
    await mm.remove("memory", "to remove")
    
    assert len(mm._memory_entries) == 1
    assert "Entry to keep" in mm._memory_entries
    assert "Entry to remove" not in mm._memory_entries


@pytest.mark.asyncio
async def test_memory_persistence(temp_prada_home):
    """Test that memories persist to disk"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    await mm.add("memory", "Persistent entry")
    await mm.save()
    
    # Create new instance and reload
    mm2 = MemoryManager(temp_prada_home)
    await mm2.initialize()
    
    assert "Persistent entry" in mm2._memory_entries


@pytest.mark.asyncio
async def test_memory_char_limit(temp_prada_home):
    """Test memory character limit enforcement"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    # Add entry exceeding limit
    long_entry = "x" * 3000
    result = await mm.add("memory", long_entry)
    
    # Should fail due to limit
    assert result["success"] is False
    assert "limit exceeded" in result["error"].lower()


@pytest.mark.asyncio
async def test_get_content_format(temp_prada_home):
    """Test memory content format with § delimiter"""
    from agent.memory_manager import MemoryManager
    
    mm = MemoryManager(temp_prada_home)
    await mm.initialize()
    
    await mm.add("memory", "Entry 1")
    await mm.add("memory", "Entry 2")
    
    content = mm.get_memory_content()
    assert "Entry 1" in content
    assert "Entry 2" in content
    assert "§" in content or "\\n" in content  # Entries separated
