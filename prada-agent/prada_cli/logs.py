"""
PRADA CLI Logs Viewer
View and follow log files
"""

import time
from pathlib import Path

import click

from prada_cli.config import get_prada_home


def view_logs(tail: bool = False, level: str = "info", grep: str = None):
    """View and follow log files"""
    prada_home = get_prada_home()
    logs_dir = prada_home / "logs"
    
    if not logs_dir.exists():
        click.echo("No logs directory found. Run PRADA Agent first to generate logs.")
        return
    
    # Find main log file
    log_file = logs_dir / "prada.log"
    if not log_file.exists():
        # Try to find any log file
        log_files = list(logs_dir.glob("*.log"))
        if not log_files:
            click.echo("No log files found.")
            return
        log_file = log_files[0]
    
    level_map = {
        "debug": 10,
        "info": 20,
        "warning": 30,
        "error": 40,
        "critical": 50,
    }
    min_level = level_map.get(level.lower(), 20)
    
    if tail:
        click.echo(f"Following log file: {log_file}")
        click.echo(f"Level filter: {level}")
        if grep:
            click.echo(f"Grep pattern: {grep}")
        click.echo("-" * 50)
        
        # Follow mode (like tail -f)
        with open(log_file, 'r', encoding='utf-8') as f:
            # Go to end of file
            f.seek(0, 2)
            
            try:
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    
                    # Apply filters
                    if should_show_line(line, min_level, grep):
                        print(line.rstrip())
            except KeyboardInterrupt:
                click.echo("\nLog following stopped.")
    else:
        # Display last N lines
        click.echo(f"Reading log file: {log_file}")
        click.echo(f"Level filter: {level}")
        if grep:
            click.echo(f"Grep pattern: {grep}")
        click.echo("=" * 50)
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            shown_count = 0
            for line in lines[-200:]:  # Last 200 lines
                if should_show_line(line, min_level, grep):
                    click.echo(line.rstrip())
                    shown_count += 1
            
            if shown_count == 0:
                click.echo("No matching log entries found.")
            else:
                click.echo(f"\nShown {shown_count} log entries")


def should_show_line(line: str, min_level: int, grep: str = None) -> bool:
    """Check if a log line should be shown based on filters"""
    # Level filter
    level_markers = [
        ("CRITICAL", 50),
        ("ERROR", 40),
        ("WARNING", 30),
        ("INFO", 20),
        ("DEBUG", 10),
    ]
    
    line_level = 0
    for marker, level_val in level_markers:
        if marker in line:
            line_level = level_val
            break
    
    if line_level < min_level:
        return False
    
    # Grep filter
    if grep and grep.lower() not in line.lower():
        return False
    
    return True


if __name__ == "__main__":
    import sys
    
    tail = "--tail" in sys.argv or "-f" in sys.argv
    level = "info"
    grep = None
    
    for i, arg in enumerate(sys.argv):
        if arg == "--level" and i + 1 < len(sys.argv):
            level = sys.argv[i + 1]
        elif arg == "--grep" and i + 1 < len(sys.argv):
            grep = sys.argv[i + 1]
    
    view_logs(tail=tail, level=level, grep=grep)
