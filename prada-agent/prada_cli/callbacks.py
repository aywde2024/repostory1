"""
PRADA CLI Callbacks
Terminal interaction callbacks for approval, clarification, and escalation
"""

import asyncio
from typing import Any, Dict, Optional

import click


class CLIController:
    """CLI session controller with interactive callbacks"""
    
    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.pending_approval: Optional[Dict[str, Any]] = None
    
    async def run(self, provider: Optional[str] = None, model: Optional[str] = None):
        """Run interactive CLI session"""
        from run_agent import AIAgent
        from prada_cli.config import get_prada_home, load_config
        
        prada_home = get_prada_home()
        config = load_config(self.profile)
        
        # Get provider/model from args or config
        if provider is None:
            provider = config.get("profiles", {}).get(self.profile, {}).get("provider", "openrouter")
        if model is None:
            model = config.get("profiles", {}).get(self.profile, {}).get("model", "")
        
        click.echo(f"\n🤖 PRADA Agent starting...")
        click.echo(f"Profile: {self.profile}")
        click.echo(f"Provider: {provider}")
        click.echo(f"Model: {model}")
        click.echo("=" * 50)
        click.echo("Type 'exit' or Ctrl+D to end session")
        click.echo("Type '/help' for available commands\n")
        
        agent = AIAgent(
            prada_home=prada_home,
            provider=provider,
            model=model,
            profile=self.profile,
            callback=self,
        )
        
        await agent.initialize()
        
        try:
            while True:
                try:
                    user_input = click.prompt(click.style("You", bold=True) + " >", type=str)
                except EOFError:
                    break
                
                if not user_input.strip():
                    continue
                
                # Handle special commands
                if user_input.strip().lower() == "exit":
                    break
                
                if user_input.strip().startswith("/"):
                    result = await self._handle_command(user_input.strip(), agent)
                    if result:
                        click.echo(result)
                    continue
                
                # Regular message
                response = await agent.chat(user_input)
                click.echo("\n" + click.style("PRADA", bold=True, fg="green") + " > " + response)
                
        finally:
            await agent.cleanup()
        
        click.echo("\n👋 Session ended.")
    
    async def _handle_command(self, command: str, agent: Any) -> Optional[str]:
        """Handle slash commands"""
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/help":
            return self._show_help()
        elif cmd == "/model":
            return await self._switch_model(agent, args)
        elif cmd == "/memory":
            return self._show_memory(agent)
        elif cmd == "/tools":
            return self._list_tools(agent)
        elif cmd == "/skills":
            return self._list_skills()
        elif cmd == "/clear":
            click.clear()
            return "Screen cleared."
        elif cmd == "/approve":
            return await self._approve_pending(agent)
        elif cmd == "/deny":
            return self._deny_pending()
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."
    
    def _show_help(self) -> str:
        """Show help message"""
        return """
Available commands:
  /help           Show this help message
  /model [name]   Switch to a different model
  /memory         Show current memory contents
  /tools          List available tools
  /skills         List available skills
  /clear          Clear the screen
  /approve        Approve pending action
  /deny           Deny pending action
  exit            End the session
"""
    
    async def _switch_model(self, agent: Any, model_name: str) -> str:
        """Switch to a different model"""
        if not model_name:
            return "Usage: /model <model-name>"
        
        await agent.switch_model(model_name)
        return f"✓ Switched to model: {model_name}"
    
    def _show_memory(self, agent: Any) -> str:
        """Show current memory contents"""
        if hasattr(agent, 'memory_manager'):
            memory = agent.memory_manager.get_memory_content()
            user = agent.memory_manager.get_user_content()
            return f"=== MEMORY ===\n{memory}\n\n=== USER ===\n{user}"
        return "Memory not initialized."
    
    def _list_tools(self, agent: Any) -> str:
        """List available tools"""
        if hasattr(agent, 'tool_registry'):
            tools = list(agent.tool_registry.list_tools().keys())
            return f"Available tools ({len(tools)}):\n  " + "\n  ".join(sorted(tools))
        return "Tool registry not available."
    
    def _list_skills(self) -> str:
        """List available skills"""
        from prada_cli.skills_hub import list_skills as hub_list_skills
        # This would need to be implemented
        return "Skills listing not yet implemented."
    
    async def _approve_pending(self, agent: Any) -> str:
        """Approve pending action"""
        if self.pending_approval:
            # Implement approval logic
            self.pending_approval = None
            return "✓ Action approved."
        return "No pending actions to approve."
    
    def _deny_pending(self) -> str:
        """Deny pending action"""
        if self.pending_approval:
            self.pending_approval = None
            return "✗ Action denied."
        return "No pending actions to deny."
    
    # Callback methods for AIAgent
    async def request_approval(self, tool_name: str, args: Dict[str, Any], risk_level: str) -> bool:
        """Request user approval for a tool call"""
        self.pending_approval = {
            "tool": tool_name,
            "args": args,
            "risk_level": risk_level,
        }
        
        click.echo("\n" + click.style("⚠️  APPROVAL REQUIRED", fg="yellow", bold=True))
        click.echo(f"Tool: {tool_name}")
        click.echo(f"Risk Level: {risk_level}")
        click.echo(f"Arguments: {args}")
        click.echo("\nType /approve to proceed, /deny to cancel")
        
        # Wait for user input (simplified - in real implementation would block)
        return False
    
    def show_tool_progress(self, tool_name: str, status: str, details: Optional[str] = None):
        """Show tool execution progress"""
        icon = "⏳" if status == "running" else "✅" if status == "success" else "❌"
        click.echo(f"\n{icon} {tool_name}: {status}")
        if details:
            click.echo(f"   {details}")
    
    def show_error(self, message: str):
        """Show error message"""
        click.echo(click.style(f"Error: {message}", fg="red"))
    
    def show_info(self, message: str):
        """Show info message"""
        click.echo(click.style(message, fg="cyan"))


if __name__ == "__main__":
    controller = CLIController()
    asyncio.run(controller.run())
