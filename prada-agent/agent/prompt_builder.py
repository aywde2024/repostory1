"""
Prompt Builder - Dynamically assembles system prompts
Injects memory, skills, tools, and context into system prompt
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds system prompts dynamically for each session.
    
    Components:
    1. Core identity and instructions
    2. Available tools (from toolsets)
    3. Memory content (MEMORY.md + USER.md)
    4. Skills list (Level 0 - summaries only)
    5. Platform-specific instructions
    
    Design principle: System prompt is immutable during session
    Only explicit operations (/model, /personality) trigger rebuild
    """
    
    def __init__(
        self,
        prada_home: Path,
        tool_registry=None,
        memory_manager=None,
    ):
        self.prada_home = prada_home
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager
        
        # Load templates
        self.templates_dir = prada_home / "templates"
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load prompt templates from disk"""
        self.core_prompt = """You are PRADA, a highly capable AI assistant with tool execution capabilities.

## Your Capabilities

You can interact with the real world through tools:
- Execute terminal commands on local/remote systems
- Read, write, and modify files
- Search the web and extract information
- Run code in sandboxed environments
- Automate browsers for complex tasks
- Send messages across multiple platforms
- Manage your own skills and memories

## How to Use Tools

When you need to accomplish a task:
1. Think step-by-step about what needs to be done
2. Call appropriate tools with correct parameters
3. Wait for tool results before proceeding
4. If a tool fails, analyze the error and try again
5. Report progress to the user after each significant step

## Important Guidelines

- **Safety First**: Never execute destructive commands without confirming with the user
- **Transparency**: Always explain what you're doing and why
- **Error Handling**: If something goes wrong, explain the issue and suggest alternatives
- **Efficiency**: Use the most direct approach, but don't skip important steps
- **Learning**: Remember important facts about the user's environment and preferences

## Memory System

You have access to two types of persistent memory:
- MEMORY.md: Your personal notes about projects, environments, and lessons learned
- USER.md: Information about the user's preferences, identity, and habits

These memories persist across sessions and help you provide personalized assistance.

## Skills

Skills are reusable procedures for common tasks. You can:
- View available skills with the skills_list tool
- Load full skill instructions with skill_view
- Create new skills when you discover effective workflows
- Update skills when you learn better approaches

## Response Format

- Be concise but thorough
- Use markdown formatting for clarity
- Show command outputs in code blocks
- Explain your reasoning for non-trivial decisions
- Ask clarifying questions when requirements are ambiguous
"""
        
        self.tools_header = "\n\n## Available Tools\n\nYou have access to these tools:\n"
        self.skills_header = "\n\n## Available Skills\n\nUse skill_view to load full instructions:\n"
    
    async def build_system_prompt(
        self,
        toolsets: List[str],
        session_id: Optional[str] = None,
        platform: str = "cli",
    ) -> str:
        """
        Build complete system prompt.
        
        Args:
            toolsets: List of toolset names to include
            session_id: Optional session identifier
            platform: Platform type (cli, telegram, discord, etc.)
            
        Returns:
            Complete system prompt string
        """
        parts = [self.core_prompt]
        
        # Add tools section
        if self.tool_registry:
            tools_section = self._build_tools_section(toolsets)
            if tools_section:
                parts.append(tools_section)
        
        # Add memory section
        if self.memory_manager:
            memory_section = self._build_memory_section()
            if memory_section:
                parts.append(memory_section)
        
        # Add skills section
        skills_section = await self._build_skills_section()
        if skills_section:
            parts.append(skills_section)
        
        # Add platform-specific instructions
        platform_instructions = self._get_platform_instructions(platform)
        if platform_instructions:
            parts.append(platform_instructions)
        
        return "\n".join(parts)
    
    def _build_tools_section(self, toolsets: List[str]) -> str:
        """Build tools section of system prompt"""
        if not self.tool_registry:
            return ""
        
        tools = self.tool_registry.get_tools_for_toolsets(toolsets)
        
        if not tools:
            return ""
        
        lines = [self.tools_header.strip()]
        
        for tool in tools:
            func = tool['function']
            name = func['name']
            desc = func.get('description', 'No description')
            params = func.get('parameters', {})
            
            # Format tool info
            lines.append(f"\n### {name}")
            lines.append(f"{desc}")
            
            if params.get('properties'):
                lines.append("\nParameters:")
                for param_name, param_info in params['properties'].items():
                    required = param_name in params.get('required', [])
                    req_marker = "*" if required else " "
                    param_desc = param_info.get('description', 'No description')
                    lines.append(f"  {req_marker} {param_name}: {param_desc}")
        
        return "\n".join(lines)
    
    def _build_memory_section(self) -> str:
        """Build memory section of system prompt"""
        if not self.memory_manager:
            return ""
        
        stats = self.memory_manager.get_stats()
        memory_content = self.memory_manager.get_memory_content()
        user_content = self.memory_manager.get_user_content()
        
        lines = ["\n\n## Your Memory\n"]
        
        # Memory stats
        mem_pct = stats['memory']['usage_pct']
        user_pct = stats['user']['usage_pct']
        
        lines.append(f"MEMORY ({mem_pct}% — {stats['memory']['chars']}/{stats['memory']['limit']} chars):")
        if memory_content:
            lines.append(memory_content)
        else:
            lines.append("(empty)")
        
        lines.append(f"\nUSER PROFILE ({user_pct}% — {stats['user']['chars']}/{stats['user']['limit']} chars):")
        if user_content:
            lines.append(user_content)
        else:
            lines.append("(empty)")
        
        return "\n".join(lines)
    
    async def _build_skills_section(self) -> str:
        """Build skills list section (Level 0 - summaries only)"""
        from prada_cli.skills_hub import get_skills_list
        
        try:
            skills = get_skills_list()
        except Exception as e:
            logger.warning(f"Could not load skills: {e}")
            return ""
        
        if not skills:
            return ""
        
        lines = [self.skills_header.strip()]
        
        for skill in skills[:50]:  # Limit to 50 skills in prompt
            name = skill.get('name', 'unknown')
            desc = skill.get('description', 'No description')
            category = skill.get('category', 'general')
            
            lines.append(f"- **{name}** ({category}): {desc[:100]}...")
        
        return "\n".join(lines)
    
    def _get_platform_instructions(self, platform: str) -> str:
        """Get platform-specific instructions"""
        platform_instructions = {
            "cli": """
## Interaction Mode

You are interacting via command-line interface.
- Responses are displayed directly in the terminal
- Tool execution shows real-time progress
- User can interrupt with Ctrl+C at any time
""",
            "telegram": """
## Interaction Mode

You are interacting via Telegram.
- Keep responses concise for mobile reading
- Use markdown formatting (Telegram supports it)
- Long responses will be split into multiple messages
- Users can send images, documents, and voice messages
""",
            "discord": """
## Interaction Mode

You are interacting via Discord.
- Support threads and channels
- Can react with emojis
- Voice channel support available
- Rich embeds for structured information
""",
            "slack": """
## Interaction Mode

You are interacting via Slack.
- Support threads and channels
- Use Slack-style formatting
- Can upload files and images
- Integrations with other Slack apps
""",
        }
        
        return platform_instructions.get(platform, "")
    
    def inject_context(self, prompt: str, context: Dict) -> str:
        """
        Inject dynamic context into prompt.
        
        Used for variables like ${WORKING_DIR}, ${CURRENT_TIME}, etc.
        """
        result = prompt
        
        for key, value in context.items():
            placeholder = f"${{{key}}}"
            result = result.replace(placeholder, str(value))
        
        return result
