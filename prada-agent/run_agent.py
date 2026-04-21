"""
PRADA Agent - Core Entry Point
Main agent loop with multi-turn conversation support
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Represents a conversation message"""
    role: str  # "user", "assistant", "tool", "system"
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ToolCall(BaseModel):
    """Represents a tool call from the model"""
    id: str
    type: str = "function"
    function: Dict[str, Any]


class ExecutionResult(BaseModel):
    """Result of tool execution"""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None


class AIAgent:
    """
    Core AI Agent with closed-loop learning capabilities.
    
    Features:
    - Multi-platform support (CLI + 18+ message gateways)
    - Procedural memory (skill creation/improvement)
    - Persistent cross-session memory (MEMORY.md + USER.md)
    - 3 API mode support (chat_completions, codex_responses, anthropic_messages)
    - Tool execution with approval system
    - Context compression and caching
    """
    
    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "nousresearch/hermes-3-llama-3.1-70b",
        toolsets: Optional[List[str]] = None,
        config_path: Optional[Path] = None,
        profile: str = "default",
    ):
        self.provider = provider
        self.model = model
        self.toolsets = toolsets or ["core", "file", "terminal", "web", "skills"]
        self.profile = profile
        self.config_path = config_path
        
        # State
        self.messages: List[Message] = []
        self.session_id: Optional[str] = None
        self.running = False
        self.current_tool_calls: Dict[str, bool] = {}  # track in-flight calls
        
        # Lazy-loaded components
        self._client = None
        self._tool_registry = None
        self._memory_manager = None
        self._context_engine = None
        self._prompt_builder = None
        
    @property
    def prada_home(self) -> Path:
        """Get PRADA home directory (~/.prada)"""
        env_home = os.environ.get("PRADA_HOME")
        if env_home:
            return Path(env_home).expanduser()
        return Path.home() / ".prada"
    
    @property
    def config_file(self) -> Path:
        """Get config file path"""
        return self.prada_home / "config.yaml"
    
    async def initialize(self) -> None:
        """Initialize agent components"""
        logger.info(f"Initializing PRADA Agent with provider={self.provider}, model={self.model}")
        
        # Ensure PRADA home exists
        self.prada_home.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        await self._load_config()
        
        # Initialize components
        from tools.registry import ToolRegistry
        self._tool_registry = ToolRegistry()
        await self._tool_registry.initialize(self.toolsets)
        
        from agent.memory_manager import MemoryManager
        self._memory_manager = MemoryManager(self.prada_home)
        await self._memory_manager.initialize()
        
        from agent.context_engine import get_context_engine
        self._context_engine = get_context_engine(self.prada_home)
        
        from agent.prompt_builder import PromptBuilder
        self._prompt_builder = PromptBuilder(
            prada_home=self.prada_home,
            tool_registry=self._tool_registry,
            memory_manager=self._memory_manager,
        )
        
        # Initialize LLM client
        await self._init_client()
        
        # Validate API key is present
        if not self._client.api_key:
            raise RuntimeError(
                f"API key not found for provider '{self.provider}'. "
                f"Please set the required environment variable (e.g., OPENROUTER_API_KEY) "
                f"or create a .env file in ~/.prada/ or project root."
            )
        
        logger.info("PRADA Agent initialized successfully")
    
    async def _load_config(self) -> None:
        """Load configuration from YAML file"""
        import yaml
        
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            profiles = config.get('profiles', {})
            profile_config = profiles.get(self.profile, {})
            
            # Override defaults with profile config
            if 'provider' in profile_config:
                self.provider = profile_config['provider']
            if 'model' in profile_config:
                self.model = profile_config['model']
            if 'toolsets' in profile_config:
                self.toolsets = profile_config['toolsets']
    
    async def _init_client(self) -> None:
        """Initialize LLM API client based on provider"""
        from prada_cli.runtime_provider import resolve_runtime_provider
        
        runtime = resolve_runtime_provider(self.provider, self.model)
        
        api_mode = runtime['api_mode']
        credentials = runtime['credentials']
        base_url = runtime.get('base_url')
        
        if api_mode == "anthropic_messages":
            from agent.anthropic_adapter import AnthropicClient
            self._client = AnthropicClient(
                api_key=credentials.get('api_key'),
                base_url=base_url,
            )
        elif api_mode == "codex_responses":
            from agent.responses_adapter import ResponsesClient
            self._client = ResponsesClient(
                api_key=credentials.get('api_key'),
                base_url=base_url,
            )
        else:  # chat_completions (default OpenAI standard)
            from agent.chat_client import ChatCompletionsClient
            self._client = ChatCompletionsClient(
                api_key=credentials.get('api_key'),
                base_url=base_url,
                model=self.model,
            )
    
    async def chat(
        self,
        user_message: str,
        image_urls: Optional[List[str]] = None,
        file_paths: Optional[List[str]] = None,
    ) -> str:
        """
        Process a user message and return agent response.
        
        Args:
            user_message: The user's input text
            image_urls: Optional list of image URLs to analyze
            file_paths: Optional list of file paths to attach
            
        Returns:
            Agent's text response
        """
        if not self.running:
            await self.initialize()
            self.running = True
        
        # Add user message to history
        user_msg = Message(role="user", content=user_message)
        self.messages.append(user_msg)
        
        # Build system prompt with context
        system_prompt = await self._prompt_builder.build_system_prompt(
            toolsets=self.toolsets,
            session_id=self.session_id,
        )
        
        # Main conversation loop
        max_turns = 50  # prevent infinite loops
        turn_count = 0
        
        while turn_count < max_turns:
            turn_count += 1
            
            # Prepare messages for API
            api_messages = [
                {"role": "system", "content": system_prompt}
            ] + [
                msg.dict(exclude_none=True) for msg in self.messages
            ]
            
            # Get available tools
            available_tools = self._tool_registry.get_tools_for_toolsets(self.toolsets)
            
            # Call LLM
            response = await self._client.complete(
                messages=api_messages,
                tools=available_tools,
            )
            
            # Parse response
            assistant_message = Message(
                role="assistant",
                content=response.get('content'),
                tool_calls=response.get('tool_calls'),
            )
            self.messages.append(assistant_message)
            
            # Check if there are tool calls
            if not assistant_message.tool_calls:
                # No tool calls, return final response
                return assistant_message.content or ""
            
            # Execute tool calls
            for tool_call in assistant_message.tool_calls:
                result = await self._execute_tool(tool_call)
                
                # Add tool result to messages
                tool_msg = Message(
                    role="tool",
                    content=result.output or result.error,
                    tool_call_id=tool_call['id'],
                    name=tool_call['function']['name'],
                )
                self.messages.append(tool_msg)
            
            # Continue loop for next turn
        
        raise RuntimeError(f"Maximum turns ({max_turns}) exceeded")
    
    async def _execute_tool(self, tool_call: Dict) -> ExecutionResult:
        """Execute a single tool call with approval check"""
        from tools.approval import ApprovalChecker
        
        tool_name = tool_call['function']['name']
        tool_args = json.loads(tool_call['function'].get('arguments', '{}'))
        
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        
        # Check if tool requires approval
        checker = ApprovalChecker()
        if checker.requires_approval(tool_name, tool_args):
            # Request user approval (callback-based)
            approved = await self._request_approval(tool_name, tool_args)
            if not approved:
                return ExecutionResult(
                    success=False,
                    error="Tool execution denied by user"
                )
        
        # Execute the tool
        try:
            tool_func = self._tool_registry.get_tool(tool_name)
            result = await tool_func(**tool_args)
            
            if isinstance(result, str):
                return ExecutionResult(success=True, output=result)
            elif isinstance(result, dict):
                return ExecutionResult(
                    success=result.get('success', True),
                    output=result.get('output'),
                    error=result.get('error'),
                    exit_code=result.get('exit_code'),
                )
            else:
                return ExecutionResult(success=True, output=str(result))
                
        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            return ExecutionResult(success=False, error=str(e))
    
    async def _request_approval(self, tool_name: str, tool_args: Dict) -> bool:
        """Request user approval for dangerous operation"""
        # This should be implemented via callback mechanism
        # For now, default to auto-approve in CLI mode
        logger.warning(f"Approval requested for {tool_name} - auto-approving")
        return True
    
    async def close(self) -> None:
        """Cleanup resources"""
        self.running = False
        
        if self._memory_manager:
            await self._memory_manager.save()
        
        if self._client:
            await self._client.close()
        
        logger.info("PRADA Agent closed")
    
    async def cleanup(self) -> None:
        """Alias for close() - cleanup resources"""
        await self.close()


async def main():
    """Main entry point for CLI usage"""
    agent = AIAgent()
    
    try:
        await agent.initialize()
        
        print("PRADA Agent initialized. Type your message (or 'quit' to exit):")
        
        while True:
            user_input = input("> ").strip()
            
            if user_input.lower() in ('quit', 'exit', '/quit'):
                break
            
            if not user_input:
                continue
            
            response = await agent.chat(user_input)
            print(f"\n{response}\n")
    
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
