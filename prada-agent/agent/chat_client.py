"""
Chat Completions API Client
Standard OpenAI-compatible API client with streaming support
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ChatCompletionsClient:
    """
    Client for OpenAI Chat Completions API standard.
    
    Supports:
    - Streaming responses
    - Tool/function calling
    - Multiple providers (OpenAI, OpenRouter, Together, etc.)
    - Timeout and retry logic
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        timeout: int = 120,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP client with keepalive
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper configuration"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                # Keepalive settings to prevent connection leaks
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
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
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Send completion request to Chat Completions API.
        
        Args:
            messages: List of message dicts with role/content
            tools: Optional list of tool schemas (JSON Schema format)
            tool_choice: "auto", "none", or "required"
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream response
            
        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Sending chat completion request (attempt {attempt + 1})")
                
                response = await client.post(
                    "/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse response
                choice = data["choices"][0]
                message = choice["message"]
                
                result = {
                    "content": message.get("content"),
                    "finish_reason": choice.get("finish_reason"),
                    "usage": data.get("usage"),
                }
                
                # Extract tool calls if present
                if "tool_calls" in message and message["tool_calls"]:
                    result["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": tc["type"],
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        }
                        for tc in message["tool_calls"]
                    ]
                
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
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
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream completion response.
        
        Yields:
            Chunks of response data
        """
        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    if data_str.strip() == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        if data["choices"]:
                            choice = data["choices"][0]
                            delta = choice.get("delta", {})
                            
                            chunk = {
                                "content": delta.get("content"),
                                "finish_reason": choice.get("finish_reason"),
                            }
                            
                            if "tool_calls" in delta and delta["tool_calls"]:
                                chunk["tool_calls"] = delta["tool_calls"]
                            
                            yield chunk
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE data: {data_str}")
