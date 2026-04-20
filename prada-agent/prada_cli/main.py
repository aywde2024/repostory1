"""
PRADA CLI - Command Line Interface
Main entry point for all prada subcommands
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import click

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="prada")
@click.option(
    "--profile", "-p",
    default="default",
    help="Configuration profile to use"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
@click.pass_context
def cli(ctx: click.Context, profile: str, verbose: bool):
    """PRADA Agent - Self-evolving multi-platform AI agent"""
    ctx.ensure_object(dict)
    ctx.obj['profile'] = profile
    ctx.obj['verbose'] = verbose
    
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option(
    "--provider",
    default=None,
    help="LLM provider to configure"
)
@click.option(
    "--model",
    default=None,
    help="Model to use"
)
def setup(provider: Optional[str], model: Optional[str]):
    """Interactive setup wizard"""
    from prada_cli.setup import run_setup_wizard
    asyncio.run(run_setup_wizard(provider, model))


@cli.command()
@click.option(
    "--provider", "-P",
    default=None,
    help="Override provider from config"
)
@click.option(
    "--model", "-m",
    default=None,
    help="Override model from config"
)
def start(provider: Optional[str], model: Optional[str]):
    """Start interactive CLI session"""
    from prada_cli.callbacks import CLIController
    controller = CLIController(profile=click.get_current_context().obj['profile'])
    asyncio.run(controller.run(provider, model))


@cli.group()
def gateway():
    """Message gateway management"""
    pass


@gateway.command(name="start")
@click.argument('platforms', nargs=-1)
@click.option(
    "--all", "all_platforms",
    is_flag=True,
    help="Start all configured platforms"
)
def gateway_start(platforms: tuple, all_platforms: bool):
    """Start message gateway for specified platforms"""
    from gateway.run import GatewayRunner
    runner = GatewayRunner()
    asyncio.run(runner.start(platforms, all_platforms=all_platforms))


@gateway.command()
def gateway_stop():
    """Stop running gateway"""
    from gateway.run import GatewayRunner
    runner = GatewayRunner()
    asyncio.run(runner.stop())


@gateway.command()
def status():
    """Show gateway status"""
    from gateway.status import show_gateway_status
    show_gateway_status()


@cli.group()
def memory():
    """Memory management"""
    pass


@memory.command()
@click.argument('provider')
def setup(provider: str):
    """Setup external memory provider"""
    from prada_cli.memory_setup import setup_memory_provider
    asyncio.run(setup_memory_provider(provider))


@memory.command()
def show():
    """Display current memory contents"""
    from agent.memory_manager import MemoryManager
    from pathlib import Path
    
    prada_home = Path.home() / ".prada"
    manager = MemoryManager(prada_home)
    asyncio.run(manager.initialize())
    
    click.echo("\n=== MEMORY.md ===")
    click.echo(manager.get_memory_content())
    click.echo("\n=== USER.md ===")
    click.echo(manager.get_user_content())


@cli.group()
def skills():
    """Skill management"""
    pass


@skills.command(name="list")
def skills_list():
    """List all available skills"""
    from prada_cli.skills_hub import list_skills
    list_skills()


@skills.command()
@click.argument('name')
def view(name: str):
    """View skill details"""
    from prada_cli.skills_hub import view_skill
    view_skill(name)


@skills.command()
@click.argument('name')
def enable(name: str):
    """Enable a skill"""
    from prada_cli.skills_config import enable_skill
    enable_skill(name)


@skills.command()
@click.argument('name')
def disable(name: str):
    """Disable a skill"""
    from prada_cli.skills_config import disable_skill
    disable_skill(name)


@cli.group()
def tools():
    """Tool management"""
    pass


@tools.command(name="list")
def tools_list():
    """List all available tools"""
    from prada_cli.tools_config import list_tools
    list_tools()


@cli.command()
def doctor():
    """System health check"""
    from prada_cli.doctor import run_doctor
    asyncio.run(run_doctor())


@cli.command()
@click.option("--tail", is_flag=True, help="Follow log output")
@click.option("--level", default="info", help="Log level filter")
@click.option("--grep", default=None, help="Filter by pattern")
def logs(tail: bool, level: str, grep: Optional[str]):
    """View and follow logs"""
    from prada_cli.logs import view_logs
    view_logs(tail=tail, level=level, grep=grep)


@cli.group()
def sessions():
    """Session management"""
    pass


@sessions.command(name="list")
@click.option("--limit", default=20, help="Number of sessions to show")
def sessions_list(limit: int):
    """List recent sessions"""
    from hermes_state import SessionStore
    store = SessionStore()
    sessions = store.list_sessions(limit=limit)
    
    for sess in sessions:
        click.echo(f"{sess['id']} - {sess['created_at']} - {sess.get('platform', 'cli')}")


@sessions.command()
@click.argument('session_id')
def view(session_id: str):
    """View session details"""
    from hermes_state import SessionStore
    store = SessionStore()
    session = store.get_session(session_id)
    
    if session:
        click.echo(f"Session: {session_id}")
        click.echo(f"Created: {session.get('created_at')}")
        click.echo(f"Platform: {session.get('platform')}")
        click.echo(f"Messages: {len(session.get('messages', []))}")
    else:
        click.echo(f"Session not found: {session_id}")


@sessions.command()
@click.argument('query')
@click.option("--limit", default=10, help="Max results")
def search(query: str, limit: int):
    """Search sessions"""
    from hermes_state import SessionStore
    store = SessionStore()
    results = store.search_sessions(query, limit=limit)
    
    for result in results:
        click.echo(f"\n{result['session_id']} (score: {result['relevance_score']:.2f})")
        click.echo(f"  {result['summary']}")


@cli.command()
def usage():
    """Show token usage statistics"""
    from prada_cli.usage import show_usage
    show_usage()


@cli.command()
@click.option("--days", default=7, help="Number of days to analyze")
def insights(days: int):
    """Show usage insights"""
    from prada_cli.insights import show_insights
    show_insights(days)


@cli.group()
def config():
    """Configuration management"""
    pass


@config.command(name="show")
def config_show():
    """Show current configuration"""
    from prada_cli.config import show_config
    show_config()


@config.command()
def validate():
    """Validate configuration file"""
    from prada_cli.config import validate_config
    validate_config()


@cli.group()
def batch():
    """Batch processing"""
    pass


@batch.command()
@click.option("--input", "input_file", required=True, help="Input JSONL file")
@click.option("--output", "output_file", required=True, help="Output JSONL file")
@click.option("--parallel", default=4, help="Parallel workers")
@click.option("--model", default=None, help="Model to use")
@click.option("--toolsets", default="core,file,terminal", help="Toolsets to enable")
@click.option("--max-turns", default=20, help="Max turns per trajectory")
@click.option("--timeout-seconds", default=300, help="Timeout per prompt")
def run(input_file: str, output_file: str, parallel: int, model: Optional[str],
        toolsets: str, max_turns: int, timeout_seconds: int):
    """Run batch trajectory generation"""
    from batch_runner import run_batch
    asyncio.run(run_batch(
        input_file=input_file,
        output_file=output_file,
        parallel=parallel,
        model=model,
        toolsets=toolsets.split(','),
        max_turns=max_turns,
        timeout_seconds=timeout_seconds,
    ))


@batch.command()
@click.option("--input", "input_file", required=True, help="Input trajectories")
@click.option("--output", "output_file", required=True, help="Output file")
@click.option("--target-tokens", default=4096, help="Target token count")
@click.option("--strategy", default="lossy-summary", help="Compression strategy")
def compress(input_file: str, output_file: str, target_tokens: int, strategy: str):
    """Compress trajectories for training"""
    from trajectory_compressor import compress_trajectories
    asyncio.run(compress_trajectories(
        input_file=input_file,
        output_file=output_file,
        target_tokens=target_tokens,
        strategy=strategy,
    ))


@cli.group()
def plugins():
    """Plugin management"""
    pass


@plugins.command(name="list")
def plugins_list():
    """List loaded plugins"""
    from prada_cli.plugins import list_plugins
    list_plugins()


@plugins.command()
@click.argument('name')
def enable(name: str):
    """Enable a plugin"""
    from prada_cli.plugins import enable_plugin
    enable_plugin(name)


@plugins.command()
@click.argument('name')
def disable(name: str):
    """Disable a plugin"""
    from prada_cli.plugins import disable_plugin
    disable_plugin(name)


@plugins.command()
def reload():
    """Reload all plugins"""
    from prada_cli.plugins import reload_plugins
    reload_plugins()


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
