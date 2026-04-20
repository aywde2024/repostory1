"""
PRADA CLI Skills Hub
Skill management commands: list, view, enable, disable
"""

import click
from pathlib import Path

from prada_cli.config import get_prada_home


def list_skills():
    """List all available skills"""
    prada_home = get_prada_home()
    skills_dir = prada_home / "skills"
    
    if not skills_dir.exists():
        click.echo("No skills directory found. Run 'prada setup' first.")
        return
    
    click.echo("\n📚 Available Skills\n")
    click.echo("=" * 50)
    
    skills_found = []
    
    # Scan skill directories
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir():
            skill_md = skill_path / "SKILL.md"
            if skill_md.exists():
                # Parse basic metadata from SKILL.md
                try:
                    content = skill_md.read_text(encoding='utf-8')
                    name = skill_path.name
                    
                    # Extract description from YAML frontmatter
                    description = "No description"
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            import yaml
                            frontmatter = yaml.safe_load(parts[1])
                            description = frontmatter.get("description", "No description")
                    
                    skills_found.append((name, description))
                except Exception as e:
                    skills_found.append((skill_path.name, f"Error reading: {e}"))
    
    if not skills_found:
        click.echo("No skills found. Create skills with the skill_manage tool.")
        return
    
    # Group by category (from subdirectories or tags)
    for name, desc in sorted(skills_found):
        click.echo(f"\n• {name}")
        click.echo(f"  {desc}")
    
    click.echo(f"\nTotal: {len(skills_found)} skill(s)")
    click.echo("\nUse 'prada skills view <name>' to see full details")


def view_skill(name: str):
    """View skill details"""
    prada_home = get_prada_home()
    skill_path = prada_home / "skills" / name
    
    if not skill_path.exists():
        click.echo(f"Skill not found: {name}")
        return
    
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        click.echo(f"Invalid skill (missing SKILL.md): {name}")
        return
    
    click.echo(f"\n📖 Skill: {name}\n")
    click.echo("=" * 50)
    
    content = skill_md.read_text(encoding='utf-8')
    click.echo(content)
    
    # Show additional files
    click.echo("\n" + "=" * 50)
    click.echo("Additional files:")
    
    for subdir in ["references", "templates", "scripts", "assets"]:
        subpath = skill_path / subdir
        if subpath.exists():
            click.echo(f"\n  📁 {subdir}/")
            for file in subpath.iterdir():
                if file.is_file():
                    click.echo(f"     - {file.name}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        view_skill(sys.argv[1])
    else:
        list_skills()
