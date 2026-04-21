"""
PRADA CLI Tools Configuration
List and configure tools per platform
"""

import click
from tools.registry import ToolRegistry


def list_tools():
    """List all available tools"""
    registry = ToolRegistry()
    tools = registry.list_tools()
    
    click.echo("\n🔧 Available Tools\n")
    click.echo("=" * 50)
    
    # Group by toolset
    toolsets = {}
    for name, info in tools.items():
        sets = info.get("toolsets", ["unknown"])
        for ts in sets:
            if ts not in toolsets:
                toolsets[ts] = []
            toolsets[ts].append((name, info))
    
    for toolset_name in sorted(toolsets.keys()):
        click.echo(f"\n📦 {toolset_name.upper()}")
        click.echo("-" * 40)
        
        for name, info in sorted(toolsets[toolset_name]):
            dangerous = " ⚠️" if info.get("dangerous", False) else ""
            platforms = info.get("platforms", ["all"])
            platform_str = ", ".join(platforms) if isinstance(platforms, list) else str(platforms)
            
            click.echo(f"  • {name}{dangerous}")
            click.echo(f"    Platforms: {platform_str}")
    
    click.echo(f"\nTotal: {len(tools)} tool(s)")
    click.echo("\n⚠️  Tools marked with ⚠️ require approval before execution")


if __name__ == "__main__":
    list_tools()
