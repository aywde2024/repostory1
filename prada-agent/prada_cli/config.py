"""
PRADA CLI Configuration Management
Handles DEFAULT_CONFIG, OPTIONAL_ENV_VARS, and migration logic
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG = {
    "profiles": {
        "default": {
            "provider": "openrouter",
            "model": "nousresearch/hermes-3-llama-3.1-70b",
            "reasoning_effort": "medium",
            "toolsets": ["core", "file", "terminal", "web", "skills"],
        }
    },
    "memory": {
        "builtin_enabled": True,
        "char_limit": 2200,
        "user_profile_enabled": True,
        "user_char_limit": 1375,
    },
    "terminal": {
        "backend": "local",
        "working_dir": "~/projects",
        "env_passthrough": ["PATH", "HOME", "USER"],
    },
    "display": {
        "tool_progress": "all",
        "spinner_style": "kawaii",
        "background_process_notifications": "all",
    },
    "skills": {
        "external_dirs": [],
        "auto_create_enabled": True,
        "max_skills_in_prompt": 50,
    },
    "gateway": {
        "enabled_platforms": [],
        "reset_policy": {
            "mode": "both",
            "daily_hour": 4,
            "idle_minutes": 1440,
        },
        "reset_by_platform": {},
    },
    "providers": {
        "openrouter": {
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1",
        },
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "enable_prompt_caching": True,
        },
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1",
        },
    },
    "plugins": {
        "memory_provider": None,
        "context_engine": None,
        "discovery_paths": [
            "~/.prada/plugins",
            ".prada/plugins",
        ],
    },
    "cron": {
        "enabled": True,
        "timezone": "UTC",
        "max_concurrent_jobs": 3,
    },
    "security": {
        "command_approval": {
            "enabled": True,
            "auto_approve_patterns": ["git status", "ls -la", "echo .*"],
        },
        "memory_scanning": {
            "enabled": True,
            "block_invisible_unicode": True,
        },
        "credential_files": {
            "allowed_extensions": [".env", ".key", ".pem", ".crt"],
            "max_file_size_mb": 1,
        },
    },
}


OPTIONAL_ENV_VARS = [
    # LLM Providers
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "MOONSHOT_API_KEY",
    "MINIMAX_API_KEY",
    "ZHIPU_API_KEY",
    "TOGETHER_API_KEY",
    "FIREWORKS_API_KEY",
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "COHERE_API_KEY",
    "CUSTOM_API_KEY",
    "CUSTOM_BASE_URL",
    
    # Message Platforms
    "TELEGRAM_BOT_TOKEN",
    "DISCORD_BOT_TOKEN",
    "SLACK_BOT_TOKEN",
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_ID",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_PHONE_NUMBER",
    "SIGNAL_PHONE_NUMBER",
    "EMAIL_IMAP_SERVER",
    "EMAIL_SMTP_SERVER",
    "EMAIL_ADDRESS",
    "EMAIL_PASSWORD",
    "MATRIX_HOMESERVER_URL",
    "MATRIX_USER_ID",
    "MATRIX_ACCESS_TOKEN",
    "MATTERMOST_BASE_URL",
    "MATTERMOST_TOKEN",
    "HOMEASSISTANT_URL",
    "HOMEASSISTANT_TOKEN",
    "BLUEBUBBLES_URL",
    "BLUEBUBBLES_TOKEN",
    "WECOM_CORP_ID",
    "WECOM_AGENT_ID",
    "WECOM_SECRET",
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "DINGTALK_ACCESS_TOKEN",
    
    # Terminal Backends
    "TERMINAL_SSH_HOST",
    "TERMINAL_SSH_USER",
    "TERMINAL_SSH_PORT",
    "TERMINAL_SSH_KEY_PATH",
    "TERMINAL_DOCKER_IMAGE",
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
    "DAYTONA_API_KEY",
    "DAYTONA_WORKSPACE_ID",
    "SINGULARITY_IMAGE_PATH",
    
    # Memory Providers
    "MEM0_VECTOR_DB",
    "MEM0_COLLECTION",
    "MEM0_EMBEDDING_MODEL",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "CHROMADB_HOST",
    "CHROMADB_PORT",
    "WEAVIATE_URL",
    "WEAVIATE_API_KEY",
    "POSTGRES_CONNECTION_STRING",
    
    # Gateway
    "GATEWAY_HOME_CHAT_PLATFORM",
    "GATEWAY_HOME_CHAT_ID",
    "GATEWAY_ALLOW_ALL_USERS",
    
    # Custom
    "PRADA_HOME",
    "PRADA_PROFILE",
    "SKILLS_REPO",
    "PRADA_DEBUG",
]


def get_prada_home() -> Path:
    """Get PRADA home directory"""
    env_home = os.environ.get("PRADA_HOME")
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".prada"


def load_config(profile: str = "default") -> Dict[str, Any]:
    """Load configuration from file with defaults"""
    config_file = get_prada_home() / "config.yaml"
    
    # Start with defaults
    config = DEFAULT_CONFIG.copy()
    
    # Load user config if exists
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}
        
        # Deep merge
        config = deep_merge(config, user_config)
    
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file"""
    config_file = get_prada_home() / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    # Set secure permissions
    try:
        os.chmod(config_file, 0o600)
    except OSError:
        pass  # May fail in container environments


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def get_env_value(key: str) -> Optional[str]:
    """Get environment variable value"""
    return os.environ.get(key)


def validate_config() -> bool:
    """Validate configuration file syntax"""
    config_file = get_prada_home() / "config.yaml"
    
    if not config_file.exists():
        print(f"Config file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"✓ Config file is valid YAML: {config_file}")
        return True
    except yaml.YAMLError as e:
        print(f"✗ Config file has YAML errors: {e}")
        return False


def show_config() -> None:
    """Display current configuration (sanitized)"""
    config = load_config()
    
    # Sanitize sensitive values
    sanitized = sanitize_config(config)
    
    print(yaml.dump(sanitized, default_flow_style=False, sort_keys=False))


def sanitize_config(config: Dict) -> Dict:
    """Remove or mask sensitive configuration values"""
    sanitized = config.copy()
    
    # Mask API keys in providers section
    if 'providers' in sanitized:
        for provider in sanitized['providers'].values():
            if 'api_key' in provider:
                provider['api_key'] = "***REDACTED***"
    
    # Mask gateway tokens
    if 'gateway' in sanitized:
        if 'allowed_users' in sanitized['gateway']:
            # Keep structure but note it's configured
            pass
    
    return sanitized


def migrate_config(old_version: str, new_version: str) -> Dict[str, Any]:
    """Migrate configuration between versions"""
    # Placeholder for future migration logic
    config = load_config()
    
    # Example migration: add new default fields
    if old_version < "0.2.0":
        if 'security' not in config:
            config['security'] = DEFAULT_CONFIG['security']
    
    return config
