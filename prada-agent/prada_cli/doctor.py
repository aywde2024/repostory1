"""
PRADA CLI Doctor
System health check command
"""

import asyncio
import os
import sys
from pathlib import Path

import click


async def run_doctor():
    """Run system health check"""
    click.echo("\n🔍 PRADA Agent Health Check\n")
    click.echo("=" * 50)
    
    issues = []
    warnings = []
    ok_count = 0
    
    # 1. Check Python version
    click.echo("\n1. Python Environment")
    click.echo("-" * 40)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 10):
        click.echo(f"  ✓ Python {python_version}")
        ok_count += 1
    else:
        click.echo(f"  ✗ Python {python_version} (requires 3.10+)")
        issues.append("Python version too old")
    
    # 2. Check PRADA home directory
    click.echo("\n2. Configuration Directory")
    click.echo("-" * 40)
    prada_home = Path.home() / ".prada"
    if prada_home.exists():
        click.echo(f"  ✓ {prada_home}")
        ok_count += 1
        
        # Check config file
        config_file = prada_home / "config.yaml"
        if config_file.exists():
            click.echo(f"  ✓ config.yaml exists")
            ok_count += 1
        else:
            click.echo(f"  ⚠ config.yaml not found (run 'prada setup')")
            warnings.append("No configuration file")
        
        # Check .env file
        env_file = prada_home / ".env"
        if env_file.exists():
            click.echo(f"  ✓ .env exists")
            
            # Check permissions
            mode = oct(env_file.stat().st_mode)[-3:]
            if mode in ["600", "400"]:
                click.echo(f"  ✓ .env permissions: {mode} (secure)")
                ok_count += 1
            else:
                click.echo(f"  ⚠ .env permissions: {mode} (should be 600)")
                warnings.append(".env file has insecure permissions")
        else:
            click.echo(f"  ⚠ .env not found (API keys not configured)")
            warnings.append("No .env file")
        
        # Check memory files
        memories_dir = prada_home / "memories"
        if memories_dir.exists():
            memory_md = memories_dir / "MEMORY.md"
            user_md = memories_dir / "USER.md"
            if memory_md.exists() and user_md.exists():
                click.echo(f"  ✓ Memory files initialized")
                ok_count += 1
            else:
                click.echo(f"  ⚠ Memory files incomplete")
                warnings.append("Memory files not fully initialized")
    else:
        click.echo(f"  ✗ {prada_home} not found (run 'prada setup')")
        issues.append("PRADA home directory not found")
    
    # 3. Check required dependencies
    click.echo("\n3. Required Dependencies")
    click.echo("-" * 40)
    required_packages = [
        "click", "pyyaml", "httpx", "aiosqlite", "tiktoken", "croniter"
    ]
    
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
            click.echo(f"  ✓ {pkg}")
            ok_count += 1
        except ImportError:
            click.echo(f"  ✗ {pkg} (missing)")
            issues.append(f"Missing package: {pkg}")
    
    # 4. Check optional dependencies
    click.echo("\n4. Optional Dependencies")
    click.echo("-" * 40)
    optional_packages = {
        "discord": "discord.py",
        "telegram": "python-telegram-bot",
        "slack": "slack_bolt",
        "paramiko": "paramiko",
        "docker": "docker",
    }
    
    for name, pkg in optional_packages.items():
        try:
            __import__(pkg.replace("-", "_").replace(".", "_"))
            click.echo(f"  ✓ {name}")
        except ImportError:
            click.echo(f"  - {name} (not installed)")
    
    # 5. Check environment variables
    click.echo("\n5. Environment Variables")
    click.echo("-" * 40)
    
    provider_keys = [
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    
    keys_found = 0
    for key in provider_keys:
        if os.environ.get(key):
            value = os.environ[key]
            masked = value[:8] + "..." if len(value) > 8 else "***"
            click.echo(f"  ✓ {key}={masked}")
            keys_found += 1
    
    if keys_found == 0:
        # Check .env file
        env_file = prada_home / ".env"
        if env_file.exists():
            content = env_file.read_text()
            for key in provider_keys:
                if key in content:
                    click.echo(f"  ✓ {key} (in .env)")
                    keys_found += 1
    
    if keys_found > 0:
        ok_count += 1
    else:
        click.echo(f"  ⚠ No API keys configured")
        warnings.append("No LLM API keys configured")
    
    # 6. Check terminal backends
    click.echo("\n6. Terminal Backends")
    click.echo("-" * 40)
    
    # Local backend
    import subprocess
    try:
        result = subprocess.run(["echo", "test"], capture_output=True, timeout=5)
        if result.returncode == 0:
            click.echo(f"  ✓ local (available)")
            ok_count += 1
        else:
            click.echo(f"  ✗ local (failed)")
            issues.append("Local terminal backend failed")
    except Exception as e:
        click.echo(f"  ✗ local ({e})")
        issues.append(f"Local terminal backend error: {e}")
    
    # Docker backend
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.decode().strip()
            click.echo(f"  ✓ docker ({version})")
        else:
            click.echo(f"  - docker (not available)")
    except FileNotFoundError:
        click.echo(f"  - docker (not installed)")
    except Exception:
        click.echo(f"  - docker (error checking)")
    
    # SSH backend
    try:
        result = subprocess.run(["ssh", "-V"], capture_output=True, timeout=5)
        if result.returncode == 0 or "OpenSSH" in result.stderr.decode():
            click.echo(f"  ✓ ssh (available)")
        else:
            click.echo(f"  - ssh (not available)")
    except FileNotFoundError:
        click.echo(f"  - ssh (not installed)")
    
    # 7. Check skills directory
    click.echo("\n7. Skills")
    click.echo("-" * 40)
    skills_dir = prada_home / "skills"
    if skills_dir.exists():
        skill_count = sum(1 for d in skills_dir.iterdir() if d.is_dir())
        click.echo(f"  ✓ {skill_count} skill(s) installed")
        ok_count += 1
    else:
        click.echo(f"  - No skills directory (will be created on first use)")
    
    # Summary
    click.echo("\n" + "=" * 50)
    click.echo("📊 Health Check Summary")
    click.echo("-" * 40)
    click.echo(f"  Checks passed: {ok_count}")
    
    if warnings:
        click.echo(f"  Warnings: {len(warnings)}")
        for w in warnings:
            click.echo(f"    ⚠️  {w}")
    
    if issues:
        click.echo(f"  Issues: {len(issues)}")
        for i in issues:
            click.echo(f"    ✗  {i}")
        
        click.echo("\n❌ Health check FAILED - please fix the issues above")
        click.echo("Run 'prada setup' to configure PRADA Agent")
        return False
    elif warnings:
        click.echo("\n⚠️  Health check PASSED with warnings")
        click.echo("PRADA Agent should work, but consider addressing warnings")
        return True
    else:
        click.echo("\n✅ All checks passed! PRADA Agent is ready.")
        click.echo("Run 'prada start' to begin an interactive session")
        return True


if __name__ == "__main__":
    asyncio.run(run_doctor())
