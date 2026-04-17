"""
PRADA Agent - Unit Tests for Core Components
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestToolRegistry:
    """Test tool registry functionality"""
    
    def test_register_tool(self):
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        def dummy_func():
            pass
        
        schema = {"type": "object", "properties": {}}
        
        registry.register(
            name="test_tool",
            func=dummy_func,
            schema=schema,
            toolsets=["test"],
        )
        
        assert "test_tool" in registry.list_tools()
        assert registry.get_tool("test_tool") is not None
    
    def test_get_nonexistent_tool(self):
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None
    
    def test_list_tools_by_toolset(self):
        from tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        
        def dummy_func():
            pass
        
        registry.register("tool1", dummy_func, {}, toolsets=["set1"])
        registry.register("tool2", dummy_func, {}, toolsets=["set2"])
        registry.register("tool3", dummy_func, {}, toolsets=["set1", "set2"])
        
        set1_tools = registry.list_tools(toolset="set1")
        assert "tool1" in set1_tools
        assert "tool3" in set1_tools
        assert "tool2" not in set1_tools


class TestMemoryManager:
    """Test memory manager functionality"""
    
    def test_add_memory(self, tmp_path):
        from agent.memory_manager import MemoryManager
        
        manager = MemoryManager(str(tmp_path))
        
        result = manager.add("memory", "Test memory entry")
        assert result["success"]
        assert "Test memory entry" in manager.get_memory()
    
    def test_replace_memory(self, tmp_path):
        from agent.memory_manager import MemoryManager
        
        manager = MemoryManager(str(tmp_path))
        manager.add("memory", "Original text")
        
        result = manager.replace("memory", "Original", "Replaced text")
        assert result["success"]
        assert "Replaced text" in manager.get_memory()
        assert "Original text" not in manager.get_memory()
    
    def test_remove_memory(self, tmp_path):
        from agent.memory_manager import MemoryManager
        
        manager = MemoryManager(str(tmp_path))
        manager.add("memory", "Entry to remove")
        
        result = manager.remove("memory", "Entry to remove")
        assert result["success"]
        assert "Entry to remove" not in manager.get_memory()
    
    def test_user_profile(self, tmp_path):
        from agent.memory_manager import MemoryManager
        
        manager = MemoryManager(str(tmp_path))
        
        result = manager.add("user", "User prefers Python")
        assert result["success"]
        assert "User prefers Python" in manager.get_user_profile()


class TestTerminalBackend:
    """Test terminal backend functionality"""
    
    def test_local_backend_available(self):
        from tools.terminal_tool import LocalBackend
        
        backend = LocalBackend()
        assert backend.is_available()
    
    def test_local_backend_execute(self):
        from tools.terminal_tool import LocalBackend
        
        backend = LocalBackend()
        result = backend.execute("echo hello", "/tmp", {}, 30)
        
        assert result.exit_code == 0
        assert "hello" in result.stdout
    
    def test_local_backend_timeout(self):
        from tools.terminal_tool import LocalBackend
        
        backend = LocalBackend()
        result = backend.execute("sleep 5", "/tmp", {}, 1)
        
        assert result.exit_code == -1
        assert "timed out" in result.stderr.lower()
    
    def test_get_working_dir(self):
        from tools.terminal_tool import LocalBackend
        
        backend = LocalBackend("/custom/dir")
        assert backend.get_working_dir() == "/custom/dir"


class TestWebTools:
    """Test web tools functionality"""
    
    def test_http_request_schema(self):
        from tools.web_tools import HTTP_REQUEST_SCHEMA
        
        assert HTTP_REQUEST_SCHEMA["type"] == "object"
        assert "method" in HTTP_REQUEST_SCHEMA["required"]
        assert "url" in HTTP_REQUEST_SCHEMA["required"]
    
    def test_web_search_schema(self):
        from tools.web_tools import WEB_SEARCH_SCHEMA
        
        assert "query" in WEB_SEARCH_SCHEMA["required"]
        assert "limit" in WEB_SEARCH_SCHEMA["properties"]


class TestCronScheduler:
    """Test cron scheduler functionality"""
    
    def test_calculate_next_run_cron(self, tmp_path):
        from cron.scheduler import JobScheduler, CronJob
        
        scheduler = JobScheduler(tmp_path)
        
        job = CronJob(
            id="test-job",
            name="Test Job",
            schedule_type="cron",
            expression="* * * * *",  # Every minute
            timezone="UTC",
            prompt="Test prompt",
            toolsets=[],
            skills=[],
            delivery={},
            timeout_minutes=30,
            retry={},
            enabled=True,
        )
        
        next_run = scheduler._calculate_next_run(job)
        assert next_run is not None
        assert next_run > 0
    
    def test_add_job(self, tmp_path):
        from cron.scheduler import JobScheduler, CronJob
        
        scheduler = JobScheduler(tmp_path)
        
        job = CronJob(
            id="test-job-2",
            name="Test Job 2",
            schedule_type="interval",
            expression="3600",  # Every hour
            timezone="UTC",
            prompt="Test",
            toolsets=[],
            skills=[],
            delivery={},
            timeout_minutes=30,
            retry={},
            enabled=True,
        )
        
        job_id = scheduler.add_job(job)
        assert job_id == "test-job-2"
        assert scheduler.get_job(job_id) is not None
    
    def test_disable_job(self, tmp_path):
        from cron.scheduler import JobScheduler, CronJob
        
        scheduler = JobScheduler(tmp_path)
        
        job = CronJob(
            id="test-job-3",
            name="Test Job 3",
            schedule_type="cron",
            expression="0 * * * *",
            timezone="UTC",
            prompt="Test",
            toolsets=[],
            skills=[],
            delivery={},
            timeout_minutes=30,
            retry={},
            enabled=True,
        )
        
        scheduler.add_job(job)
        assert scheduler.disable_job("test-job-3")
        assert scheduler.get_job("test-job-3").enabled is False


class TestSkillSystem:
    """Test skill system functionality"""
    
    def test_load_skill_metadata(self, tmp_path):
        import yaml
        
        skill_content = """---
name: test-skill
description: Test skill description
version: 1.0.0
metadata:
  prada:
    tags: [test]
    category: testing
---

# Test Skill Content
"""
        
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(skill_content)
        
        # Parse frontmatter
        content = skill_file.read_text()
        parts = content.split("---", 2)
        metadata = yaml.safe_load(parts[1])
        
        assert metadata["name"] == "test-skill"
        assert metadata["version"] == "1.0.0"


class TestGatewaySessionStore:
    """Test gateway session store functionality"""
    
    def test_create_session(self, tmp_path):
        from gateway.run import SessionStore
        
        store = SessionStore(tmp_path)
        session = store.get_or_create_session("user123", "telegram")
        
        assert session.user_id == "user123"
        assert session.platform == "telegram"
        assert session.session_id.startswith("sess_")
    
    def test_session_persistence(self, tmp_path):
        from gateway.run import SessionStore
        
        store = SessionStore(tmp_path)
        session1 = store.get_or_create_session("user456", "discord")
        session_id = session1.session_id
        
        # Create new store instance (simulates reload)
        store2 = SessionStore(tmp_path)
        session2 = store2.get_session(session_id)
        
        assert session2 is not None
        assert session2.user_id == "user456"
    
    def test_add_message_to_session(self, tmp_path):
        from gateway.run import SessionStore
        
        store = SessionStore(tmp_path)
        session = store.get_or_create_session("user789", "slack")
        
        store.add_message(session.session_id, "user", "Hello!")
        store.add_message(session.session_id, "assistant", "Hi there!")
        
        assert len(session.message_history) == 2
        assert session.message_history[0]["role"] == "user"
        assert session.message_history[1]["role"] == "assistant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
