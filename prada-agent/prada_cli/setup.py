"""
PRADA CLI Setup Wizard
Interactive setup for configuring providers, models, and platforms
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

import click
import yaml

from prada_cli.config import (
    DEFAULT_CONFIG,
    get_prada_home,
    load_config,
    save_config,
    OPTIONAL_ENV_VARS,
)


async def run_setup_wizard(provider: Optional[str] = None, model: Optional[str] = None):
    """Run interactive setup wizard"""
    prada_home = get_prada_home()
    prada_home.mkdir(parents=True, exist_ok=True)
    
    click.echo("\n🎯 PRADA Agent Setup Wizard\n")
    click.echo("=" * 50)
    
    # Load existing config or start with defaults
    config = load_config()
    
    # Step 1: LLM Provider
    click.echo("\n📡 Step 1: Configure LLM Provider")
    click.echo("-" * 40)
    
    if provider is None:
        available_providers = list(DEFAULT_CONFIG.get("providers", {}).keys())
        click.echo("\nAvailable providers:")
        for i, p in enumerate(available_providers, 1):
            click.echo(f"  {i}. {p}")
        
        current_provider = config.get("profiles", {}).get("default", {}).get("provider", "openrouter")
        choice = click.prompt(
            f"\nSelect provider [{current_provider}]",
            default=current_provider,
            type=str
        )
        provider = choice
    
    # Configure provider credentials
    click.echo(f"\n✓ Selected provider: {provider}")
    
    provider_config = config.get("providers", {}).get(provider, {})
    api_key_env = provider_config.get("api_key_env", f"{provider.upper()}_API_KEY")
    
    click.echo(f"\n🔑 API Key Environment Variable: {api_key_env}")
    api_key = click.prompt(
        f"Enter your {provider} API key",
        default=os.environ.get(api_key_env, ""),
        hide_input=True
    )
    
    if api_key:
        # Save to .env file
        env_file = prada_home / ".env"
        env_content = ""
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()
        
        # Update or add API key
        if api_key_env in env_content:
            env_content = "\n".join(
                line if not line.startswith(f"{api_key_env}=") else f"{api_key_env}={api_key}"
                for line in env_content.splitlines()
            )
        else:
            env_content += f"\n{api_key_env}={api_key}\n"
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        # Set secure permissions
        try:
            os.chmod(env_file, 0o600)
        except OSError:
            pass
        
        click.echo(f"✓ API key saved to {env_file}")
    
    # Step 2: Model selection
    click.echo("\n🤖 Step 2: Select Model")
    click.echo("-" * 40)
    
    if model is None:
        current_model = config.get("profiles", {}).get("default", {}).get("model", "")
        model = click.prompt(
            "Enter model name",
            default=current_model or "nousresearch/hermes-3-llama-3.1-70b",
            type=str
        )
    
    click.echo(f"✓ Selected model: {model}")
    
    # Update config
    if "profiles" not in config:
        config["profiles"] = {}
    if "default" not in config["profiles"]:
        config["profiles"]["default"] = {}
    
    config["profiles"]["default"]["provider"] = provider
    config["profiles"]["default"]["model"] = model
    
    # Step 3: Terminal backend
    click.echo("\n💻 Step 3: Configure Terminal Backend")
    click.echo("-" * 40)
    
    backends = ["local", "docker", "ssh", "modal", "daytona", "singularity"]
    current_backend = config.get("terminal", {}).get("backend", "local")
    
    click.echo("\nAvailable backends:")
    for i, b in enumerate(backends, 1):
        marker = " ✓" if b == current_backend else ""
        click.echo(f"  {i}. {b}{marker}")
    
    backend_choice = click.prompt(
        f"\nSelect terminal backend [{current_backend}]",
        default=current_backend,
        type=click.Choice(backends)
    )
    
    config["terminal"] = config.get("terminal", {})
    config["terminal"]["backend"] = backend_choice
    
    if backend_choice == "ssh":
        click.echo("\nSSH Configuration:")
        ssh_host = click.prompt("SSH host", default=config.get("terminal", {}).get("ssh", {}).get("host", ""))
        ssh_user = click.prompt("SSH user", default=config.get("terminal", {}).get("ssh", {}).get("user", ""))
        ssh_port = click.prompt("SSH port", default=22)
        
        config["terminal"]["ssh"] = {
            "host": ssh_host,
            "user": ssh_user,
            "port": ssh_port,
        }
    
    click.echo(f"✓ Terminal backend: {backend_choice}")
    
    # Step 4: Memory configuration
    click.echo("\n🧠 Step 4: Memory Configuration")
    click.echo("-" * 40)
    
    enable_memory = click.confirm(
        "Enable built-in memory (MEMORY.md + USER.md)?",
        default=config.get("memory", {}).get("builtin_enabled", True)
    )
    
    config["memory"] = config.get("memory", {})
    config["memory"]["builtin_enabled"] = enable_memory
    config["memory"]["char_limit"] = 2200
    config["memory"]["user_profile_enabled"] = True
    config["memory"]["user_char_limit"] = 1375
    
    # External memory provider
    click.echo("\nExternal memory providers (optional):")
    external_providers = ["none", "mem0", "honcho", "openviking", "hindsight"]
    current_external = config.get("plugins", {}).get("memory_provider", "none")
    
    for i, p in enumerate(external_providers, 1):
        marker = " ✓" if p == current_external else ""
        click.echo(f"  {i}. {p}{marker}")
    
    external_choice = click.prompt(
        "Select external memory provider",
        default=current_external,
        type=click.Choice(external_providers)
    )
    
    if "plugins" not in config:
        config["plugins"] = {}
    
    config["plugins"]["memory_provider"] = None if external_choice == "none" else external_choice
    
    click.echo(f"✓ External memory: {external_choice}")
    
    # Step 5: Message platforms
    click.echo("\n📨 Step 5: Message Platforms (Optional)")
    click.echo("-" * 40)
    
    platforms = [
        "telegram", "discord", "slack", "whatsapp", "signal",
        "email", "matrix", "mattermost", "feishu", "wecom"
    ]
    
    enabled_platforms = config.get("gateway", {}).get("enabled_platforms", [])
    
    click.echo("\nEnable any of these platforms? (comma-separated, or skip)")
    for i, p in enumerate(platforms, 1):
        marker = " ✓" if p in enabled_platforms else ""
        click.echo(f"  {i}. {p}{marker}")
    
    platform_input = click.prompt(
        "Platforms to enable",
        default=",".join(enabled_platforms),
        type=str
    )
    
    if platform_input.strip():
        config["gateway"] = config.get("gateway", {})
        config["gateway"]["enabled_platforms"] = [p.strip() for p in platform_input.split(",") if p.strip()]
    else:
        config["gateway"] = config.get("gateway", {})
        config["gateway"]["enabled_platforms"] = []
    
    # Save configuration
    click.echo("\n💾 Saving configuration...")
    save_config(config)
    
    config_file = prada_home / "config.yaml"
    click.echo(f"✓ Configuration saved to {config_file}")
    
    # Initialize memory files
    if enable_memory:
        memories_dir = prada_home / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        
        memory_file = memories_dir / "MEMORY.md"
        user_file = memories_dir / "USER.md"
        
        if not memory_file.exists():
            with open(memory_file, 'w') as f:
                f.write("# MEMORY (your personal notes)\n\n")
            click.echo(f"✓ Created {memory_file}")
        
        if not user_file.exists():
            with open(user_file, 'w') as f:
                f.write("# USER PROFILE (who you are)\n\n")
            click.echo(f"✓ Created {user_file}")
    
    # Summary
    click.echo("\n" + "=" * 50)
    click.echo("✅ Setup Complete!\n")
    click.echo("Configuration summary:")
    click.echo(f"  • Provider: {provider}")
    click.echo(f"  • Model: {model}")
    click.echo(f"  • Terminal: {backend_choice}")
    click.echo(f"  • Memory: {'Enabled' if enable_memory else 'Disabled'}")
    click.echo(f"  • External Memory: {external_choice}")
    click.echo(f"  • Platforms: {', '.join(config['gateway']['enabled_platforms']) or 'None'}")
    
    click.echo("\nNext steps:")
    click.echo("  1. Run 'prada start' to begin an interactive session")
    click.echo("  2. Run 'prada gateway start --all' to start message gateways")
    click.echo("  3. Run 'prada doctor' to verify system health")
    click.echo("")


if __name__ == "__main__":
    asyncio.run(run_setup_wizard())
