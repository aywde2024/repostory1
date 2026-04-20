"""
Toolsets Definition - 19 toolsets with 47 tools
Platform-specific presets and default combinations
"""

TOOLSETS = {
    # Core toolsets
    "core": ["memory", "skill_manage", "session_search", "usage"],
    
    # File operations
    "file": ["read_file", "write_file", "patch", "search_files", "list_dir"],
    
    # Terminal execution (6 backends)
    "terminal": ["terminal", "process_list", "process_kill", "process_wait"],
    
    # Network & Search
    "web": ["web_search", "web_extract", "http_request"],
    
    # Browser automation (5 backends, 10 tools)
    "browser": [
        "browser_navigate", "browser_click", "browser_fill", 
        "browser_evaluate", "browser_screenshot", "browser_download",
        "browser_upload", "browser_tab_manage", "browser_history",
        "browser_cookies"
    ],
    
    # Code execution
    "code": ["execute_code", "code_analyze", "code_fix"],
    
    # Delegation & Parallel
    "delegate": ["delegate", "subagent_status", "subagent_cancel"],
    
    # MCP integration
    "mcp": ["mcp_list_tools", "mcp_call_tool", "mcp_list_resources"],
    
    # Credential management
    "credentials": ["credential_files", "env_passthrough"],
    
    # Vision & Multimedia
    "vision": ["image_analyze", "image_generate", "audio_transcribe", "audio_speak"],
    
    # Message delivery
    "delivery": ["send_message", "send_file", "send_image"],
    
    # Home Assistant specific
    "homeassistant": [
        "ha_list_entities", "ha_get_state", 
        "ha_call_service", "ha_list_services"
    ],
    
    # Skills system
    "skills": ["skills_list", "skill_view", "skill_manage"],
    
    # Memory operations
    "memory_ops": ["memory_add", "memory_replace", "memory_remove"],
    
    # Session management
    "session": ["session_list", "session_search", "session_compress"],
    
    # Debug & Diagnostics
    "debug": ["doctor", "logs_tail", "config_show"],
    
    # RL training
    "rl": ["rl_step", "rl_reward", "rl_trajectory"],
    
    # Schedule & Automation
    "cron": ["cron_list", "cron_create", "cron_delete"],
}

# Merge platform presets into TOOLSETS for unified access
PLATFORM_TOOLSET_PRESETS = {
    "hermes-cli": ["core", "file", "terminal", "web", "code", "delegate", "skills", "memory_ops"],
    "hermes-telegram": ["core", "file", "terminal", "web", "delivery", "skills"],
    "hermes-discord": ["core", "file", "terminal", "web", "delivery", "skills", "vision"],
    "hermes-slack": ["core", "file", "terminal", "web", "delivery", "skills"],
    "hermes-whatsapp": ["core", "file", "web", "delivery", "skills"],
    "hermes-signal": ["core", "file", "web", "delivery"],
    "hermes-email": ["core", "file", "web", "delivery"],
    "hermes-homeassistant": ["core", "homeassistant", "file", "terminal"],
    "hermes-mattermost": ["core", "file", "terminal", "web", "delivery", "skills"],
    "hermes-matrix": ["core", "file", "terminal", "web", "delivery", "skills"],
    "hermes-dingtalk": ["core", "file", "web", "delivery"],
    "hermes-feishu": ["core", "file", "terminal", "web", "delivery", "skills"],
    "hermes-wecom": ["core", "file", "web", "delivery", "skills"],
    "hermes-weixin": ["core", "file", "web", "delivery"],
    "hermes-bluebubbles": ["core", "file", "web", "delivery"],
    "hermes-qqbot": ["core", "file", "web", "delivery"],
    "hermes-webhook": ["core", "file", "web", "delivery"],
    "hermes-api-server": ["core", "file", "terminal", "web", "code", "delegate", "skills", "memory_ops", "vision"],
}

# Add platform presets to TOOLSETS with prada- prefix for unified access
for platform, toolsets in PLATFORM_TOOLSET_PRESETS.items():
    prada_key = platform.replace("hermes-", "prada-")
    TOOLSETS[prada_key] = toolsets


def get_toolset_tools(toolset_name: str) -> list:
    """Get list of tool names in a toolset"""
    return TOOLSETS.get(toolset_name, [])


def get_platform_preset(platform: str) -> list:
    """Get toolset preset for a platform"""
    key = f"hermes-{platform}"
    return PLATFORM_TOOLSET_PRESETS.get(key, PLATFORM_TOOLSET_PRESETS.get("hermes-cli", []))


def get_all_toolsets() -> list:
    """Get all available toolset names"""
    return list(TOOLSETS.keys())


def validate_toolset(toolset_name: str) -> bool:
    """Check if toolset exists"""
    return toolset_name in TOOLSETS
