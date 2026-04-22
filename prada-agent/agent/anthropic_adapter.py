"""
Anthropic Messages API Client
Supports Claude models with prompt caching and beta features
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AnthropicClient:
    """
    Client for Anthropic Messages API.
    
    Supports:
    - Claude 3.x models (Opus, Sonnet, Haiku)
    - Prompt caching (beta)
    - Tool use with enhanced schemas
    - Streaming responses
    - Multi-modal input (text + images)
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        model: str = "claude-3-5-sonnet-20241022",
        timeout: int = 120,
        max_retries: int = 3,
        enable_prompt_caching: bool = False,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_prompt_caching = enable_prompt_caching
        
        # API version header
        self.api_version = "2023-06-01"
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with Anthropic-specific headers"""
        if self._client is None or self._client.is_closed:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": self.api_version,
                # Add User-Agent for better API compatibility
                "User-Agent": "PRADA-Agent/1.0",
            }
            
            # Add beta features header if caching enabled
            if self.enable_prompt_caching:
                headers["anthropic-beta"] = "prompt-caching-2024-07-31"
            
            # Create transport with explicit SSL and no proxy interference
            transport = httpx.AsyncHTTPTransport(
                retries=self.max_retries,
                verify=True,
            )
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=30.0, read=60.0, write=30.0),
                headers=headers,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
                transport=transport,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def cleanup(self) -> None:
        """Alias for close() - cleanup resources"""
        await self.close()
    
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Send completion request to Anthropic Messages API.
        
        Args:
            messages: List of message dicts (system separate in Anthropic format)
            tools: Optional list of tool schemas (Anthropic format)
            tool_choice: "auto", "any", "none", or dict with type
            temperature: Sampling temperature
            max_tokens: Maximum tokens (required for Anthropic)
            stream: Whether to stream
            
        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        client = await self._get_client()
        
        # Separate system message (Anthropic uses separate field)
        system_content = ""
        conversation_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                # Convert to Anthropic format
                anthropic_msg = {
                    "role": msg["role"],
                    "content": self._convert_content(msg),
                }
                conversation_messages.append(anthropic_msg)
        
        payload = {
            "model": self.model,
            "messages": conversation_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if system_content:
            payload["system"] = self._convert_content({"content": system_content})
        
        if tools:
            payload["tools"] = self._convert_tools(tools)
            
            # Convert tool_choice to Anthropic format
            if isinstance(tool_choice, str):
                if tool_choice == "auto":
                    payload["tool_choice"] = {"type": "auto"}
                elif tool_choice == "required":
                    payload["tool_choice"] = {"type": "any"}
                elif tool_choice == "none":
                    payload["tool_choice"] = {"type": "none"}
            else:
                payload["tool_choice"] = tool_choice
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Sending Anthropic request (attempt {attempt + 1})")
                
                response = await client.post(
                    "/messages",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse response
                result = {
                    "content": None,
                    "tool_calls": [],
                    "finish_reason": data.get("stop_reason"),
                    "usage": data.get("usage"),
                }
                
                # Extract content blocks
                for block in data.get("content", []):
                    if block["type"] == "text":
                        result["content"] = block["text"]
                    elif block["type"] == "tool_use":
                        result["tool_calls"].append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            },
                        })
                
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
                
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError("All retry attempts failed")
    
    async def complete_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream completion response using SSE"""
        client = await self._get_client()
        
        # Prepare payload (same as complete)
        system_content = ""
        conversation_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                conversation_messages.append({
                    "role": msg["role"],
                    "content": self._convert_content(msg),
                })
        
        payload = {
            "model": self.model,
            "messages": conversation_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        
        if system_content:
            payload["system"] = self._convert_content({"content": system_content})
        
        if tools:
            payload["tools"] = self._convert_tools(tools)
            if isinstance(tool_choice, str):
                if tool_choice == "auto":
                    payload["tool_choice"] = {"type": "auto"}
                elif tool_choice == "required":
                    payload["tool_choice"] = {"type": "any"}
        
        async with client.stream("POST", "/messages", json=payload) as response:
            response.raise_for_status()
            
            current_content = ""
            current_tool_call = None
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    
                    if data_str.strip() == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type")
                        
                        if event_type == "content_block_start":
                            block = data.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_call = {
                                    "id": block.get("id"),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name"),
                                        "arguments": "",
                                    },
                                }
                        
                        elif event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            
                            if delta.get("type") == "text_delta":
                                chunk = {
                                    "content": delta.get("text"),
                                    "finish_reason": None,
                                }
                                yield chunk
                            
                            elif delta.get("type") == "input_json_delta" and current_tool_call:
                                current_tool_call["function"]["arguments"] += delta.get("partial_json", "")
                        
                        elif event_type == "content_block_stop":
                            if current_tool_call:
                                yield {
                                    "content": None,
                                    "tool_calls": [current_tool_call],
                                    "finish_reason": None,
                                }
                                current_tool_call = None
                        
                        elif event_type == "message_stop":
                            yield {
                                "content": None,
                                "finish_reason": "stop",
                            }
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE data: {data_str}")
    
    def _convert_content(self, msg: Dict) -> Any:
        """Convert message content to Anthropic format"""
        content = msg.get("content")
        
        if content is None:
            return ""
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            # Handle multi-modal content
            converted = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        converted.append({"type": "text", "text": item.get("text", "")})
                    elif item.get("type") == "image_url":
                        # Convert image URL to base64 if needed
                        converted.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": item.get("image_url", ""),
                            },
                        })
                else:
                    converted.append({"type": "text", "text": str(item)})
            return converted
        
        return str(content)
    
    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert tool schemas to Anthropic format"""
        converted = []
        
        for tool in tools:
            if "function" in tool:
                # OpenAI format → Anthropic format
                func = tool["function"]
                converted.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {
                        "type": "object",
                        "properties": {},
                    }),
                })
            else:
                # Already in Anthropic format
                converted.append(tool)
        
        return converted
