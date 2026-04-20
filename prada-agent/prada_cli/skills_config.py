"""
PRADA CLI Skills Configuration
Enable/disable skills per platform
"""

import click
import yaml
from pathlib import Path

from prada_cli.config import get_prada_home, load_config, save_config


def enable_skill(name: str):
    """Enable a skill"""
    config = load_config()
    
    if "skills" not in config:
        config["skills"] = {}
    
    # Get currently disabled skills
    disabled = config["skills"].get("disabled", [])
    
    if name in disabled:
        disabled.remove(name)
        config["skills"]["disabled"] = disabled
        save_config(config)
        click.echo(f"✓ Skill '{name}' enabled")
    else:
        click.echo(f"Skill '{name}' is already enabled")


def disable_skill(name: str):
    """Disable a skill"""
    config = load_config()
    
    if "skills" not in config:
        config["skills"] = {}
    
    # Get currently disabled skills
    disabled = config["skills"].get("disabled", [])
    
    if name not in disabled:
        disabled.append(name)
        config["skills"]["disabled"] = disabled
        save_config(config)
        click.echo(f"✓ Skill '{name}' disabled")
    else:
        click.echo(f"Skill '{name}' is already disabled")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python skills_config.py <enable|disable> <skill_name>")
        sys.exit(1)
    
    action = sys.argv[1]
    name = sys.argv[2]
    
    if action == "enable":
        enable_skill(name)
    elif action == "disable":
        disable_skill(name)
    else:
        print(f"Unknown action: {action}")
