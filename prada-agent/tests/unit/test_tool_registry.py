"""Unit tests for tool registry system"""

import pytest


def test_file_tools_registered():
    """Test that file tools are registered"""
    import tools.file_tools
    from tools.registry import registry
    
    assert len(registry._tools) >= 5
    assert "read_file" in registry._tools
    assert "write_file" in registry._tools
    assert "patch" in registry._tools
    assert "list_dir" in registry._tools
    assert "search_files" in registry._tools


def test_terminal_tools_registered():
    """Test that terminal tools are registered"""
    import tools.terminal_tool
    from tools.registry import registry
    
    assert "terminal" in registry._tools
    assert "process_list" in registry._tools
    assert "process_kill" in registry._tools
    assert "process_wait" in registry._tools


def test_web_tools_registered():
    """Test that web tools are registered"""
    import tools.web_tools
    from tools.registry import registry
    
    assert "web_search" in registry._tools
    assert "web_extract" in registry._tools
    assert "http_request" in registry._tools


def test_browser_tools_registered():
    """Test that browser tools are registered"""
    import tools.browser_tool
    from tools.registry import registry
    
    assert "browser_navigate" in registry._tools
    assert "browser_click" in registry._tools
    assert "browser_fill" in registry._tools
    assert "browser_screenshot" in registry._tools


def test_code_tools_registered():
    """Test that code execution tools are registered"""
    import tools.code_execution_tool
    from tools.registry import registry
    
    assert "execute_code" in registry._tools
    assert "code_analyze" in registry._tools
    assert "code_fix" in registry._tools


def test_tool_schema_valid():
    """Test that registered tools have valid JSON schema"""
    import tools.file_tools
    from tools.registry import registry
    
    for tool_name, tool_data in registry._tools.items():
        assert "schema" in tool_data
        assert isinstance(tool_data["schema"], dict)
        assert "type" in tool_data["schema"]


def test_get_tool():
    """Test getting a tool from registry"""
    import tools.file_tools
    from tools.registry import registry
    
    tool = registry.get_tool("read_file")
    assert tool is not None
    assert callable(tool)  # Tool is a function


def test_list_tools():
    """Test listing all tools"""
    import tools.file_tools
    from tools.registry import registry
    
    tools = registry.list_tools()
    assert len(tools) >= 5
    assert isinstance(tools, list)


def test_tool_availability_check():
    """Test tool availability check function"""
    import tools.file_tools
    from tools.registry import registry
    
    # File tools should be available
    tool = registry._tools.get("read_file", {})
    check_fn = tool.get("availability_check", lambda: True)
    assert callable(check_fn)
    assert check_fn() is True
