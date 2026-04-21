"""
PRADA CLI Usage Statistics
Show token usage statistics for current session
"""

import click
from pathlib import Path

from prada_cli.config import get_prada_home


def show_usage():
    """Show token usage statistics"""
    prada_home = get_prada_home()
    
    click.echo("\n📊 PRADA Agent Token Usage\n")
    click.echo("=" * 50)
    
    # Try to load session store
    try:
        from gateway.run import SessionStore
        store = SessionStore()
        
        # Get current session (most recent)
        sessions = store.list_sessions(limit=1)
        if not sessions:
            click.echo("No sessions found. Start a session with 'prada start' first.")
            return
        
        session = sessions[0]
        messages = session.get("messages", [])
        
        total_input_tokens = 0
        total_output_tokens = 0
        tool_calls = 0
        
        for msg in messages:
            role = msg.get("role", "")
            if role == "user":
                # Estimate tokens (rough approximation)
                content = msg.get("content", "")
                total_input_tokens += len(content) // 4
            elif role == "assistant":
                content = msg.get("content", "")
                total_output_tokens += len(content) // 4
                
                # Count tool calls
                if "tool_calls" in msg:
                    tool_calls += len(msg["tool_calls"])
            elif role == "tool":
                content = msg.get("content", "")
                total_input_tokens += len(content) // 4
        
        click.echo(f"\nSession: {session.get('id', 'N/A')[:8]}...")
        click.echo(f"Started: {session.get('created_at', 'N/A')}")
        click.echo(f"Messages: {len(messages)}")
        click.echo(f"Tool Calls: {tool_calls}")
        click.echo("\nToken Usage:")
        click.echo(f"  • Input tokens:  ~{total_input_tokens:,}")
        click.echo(f"  • Output tokens: ~{total_output_tokens:,}")
        click.echo(f"  • Total:         ~{total_input_tokens + total_output_tokens:,}")
        
        # Estimated cost (varies by provider)
        click.echo("\nEstimated Cost (OpenRouter example):")
        click.echo(f"  • At $0.50/1M input:  ${total_input_tokens * 0.50 / 1_000_000:.4f}")
        click.echo(f"  • At $1.50/1M output: ${total_output_tokens * 1.50 / 1_000_000:.4f}")
        click.echo(f"  • Total:              ${(total_input_tokens * 0.50 + total_output_tokens * 1.50) / 1_000_000:.4f}")
        
    except ImportError:
        click.echo("Session store not available.")
        click.echo("Usage statistics will be shown after running sessions.")
    
    click.echo("\n" + "=" * 50)
    click.echo("Note: Token counts are estimates. Actual counts depend on the LLM provider.")


if __name__ == "__main__":
    show_usage()
