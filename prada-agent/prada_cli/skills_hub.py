"""
PRADA CLI Skills Hub
Skill management commands: list, view, enable, disable
"""

import click
from pathlib import Path
from typing import List, Dict, Any

from prada_cli.config import get_prada_home


def get_skills_list() -> List[Dict[str, Any]]:
    """Get list of all available skills (Level 0 - summaries only)
    
    Returns:
        List of dicts with keys: name, description, category
    """
    prada_home = get_prada_home()
    skills_dir = prada_home / "skills"
    
    if not skills_dir.exists():
        return []
    
    skills_found = []
    
    # Scan skill directories
    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir():
            skill_md = skill_path / "SKILL.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding='utf-8')
                    name = skill_path.name
                    
                    # Extract metadata from YAML frontmatter
                    description = "No description"
                    category = "general"
                    tags = []
                    
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            import yaml
                            frontmatter = yaml.safe_load(parts[1])
                            description = frontmatter.get("description", "No description")
                            category = frontmatter.get("metadata", {}).get("hermes", {}).get("category", "general")
                            tags = frontmatter.get("metadata", {}).get("hermes", {}).get("tags", [])
                    
                    skills_found.append({
                        "name": name,
                        "description": description,
                        "category": category,
                        "tags": tags
                    })
                except Exception as e:
                    skills_found.append({
                        "name": skill_path.name,
                        "description": f"Error reading: {e}",
                        "category": "unknown",
                        "tags": []
                    })
    
    return sorted(skills_found, key=lambda x: x["name"])


def list_skills():
    """List all available skills"""
    prada_home = get_prada_home()
    skills_dir = prada_home / "skills"
    
    if not skills_dir.exists():
        click.echo("No skills directory found. Run 'prada setup' first.")
        return
    
    click.echo("\n📚 Available Skills\n")
    click.echo("=" * 50)
    
    skills_found = get_skills_list()
    
    if not skills_found:
        click.echo("No skills found. Create skills with the skill_manage tool.")
        return
    
    # Group by category
    categories = {}
    for skill in skills_found:
        cat = skill["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(skill)
    
    for cat in sorted(categories.keys()):
        click.echo(f"\n{cat.upper()}")
        click.echo("-" * 30)
        for skill in categories[cat]:
            click.echo(f"\n• {skill['name']}")
            click.echo(f"  {skill['description']}")
            if skill['tags']:
                click.echo(f"  Tags: {', '.join(skill['tags'])}")
    
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
