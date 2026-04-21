"""
Responses API Client (OpenAI CodeAssist/Responses format)
Supports xAI/Grok and OpenAI Codex Responses API
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ResponsesClient:
    """
    Client for OpenAI Responses API / xAI Grok API.
    
    This API format is used by:
    - xAI (Grok models)
    - OpenAI CodeAssist
    - Some specialized endpoints
    
    Format differs from Chat Completions:
    - Uses "input" instead of "messages"
    - Enhanced tool schema support
    - Special headers for conversation tracking
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.x.ai/v1",
        model: str = "grok-beta",
        timeout: int = 120,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            # xAI specific: add conversation ID header if needed
            if "x.ai" in self.base_url:
                headers["x-grok-conv-id"] = f"conv_{asyncio.get_event_loop().time()}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                headers=headers,
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
        Send completion request to Responses API.
        
        Args:
            messages: List of message dicts (will be converted to "input" format)
            tools: Optional list of tool schemas
            tool_choice: "auto", "none", or "required"
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stream: Whether to stream
            
        Returns:
            Response dict with 'content' and optional 'tool_calls'
        """
        client = await self._get_client()
        
        # Convert messages to Responses API format
        input_format = []
        for msg in messages:
            item = {
                "role": msg["role"],
                "content": msg["content"],
            }
            if msg.get("tool_call_id"):
                item["tool_call_id"] = msg["tool_call_id"]
            if msg.get("name"):
                item["name"] = msg["name"]
            input_format.append(item)
        
        payload = {
            "model": self.model,
            "input": input_format,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        # xAI specific: request encrypted content for reasoning
        if "x.ai" in self.base_url:
            payload["include"] = ["reasoning.encrypted_content"]
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Sending responses API request (attempt {attempt + 1})")
                
                response = await client.post(
                    "/responses",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse response format
                choice = data.get("choices", [{}])[0] if data.get("choices") else {}
                message = choice.get("message", {})
                
                result = {
                    "content": message.get("content"),
                    "finish_reason": choice.get("finish_reason"),
                    "usage": data.get("usage"),
                }
                
                # Extract tool calls
                if "tool_calls" in message and message["tool_calls"]:
                    result["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": tc.get("type", "function"),
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
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream completion response"""
        client = await self._get_client()
        
        # Convert to input format
        input_format = []
        for msg in messages:
            item = {"role": msg["role"], "content": msg["content"]}
            if msg.get("tool_call_id"):
                item["tool_call_id"] = msg["tool_call_id"]
            input_format.append(item)
        
        payload = {
            "model": self.model,
            "input": input_format,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        async with client.stream("POST", "/responses", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    
                    if data_str.strip() == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        if data.get("choices"):
                            choice = data["choices"][0]
                            delta = choice.get("delta", {})
                            
                            chunk = {
                                "content": delta.get("content"),
                                "finish_reason": choice.get("finish_reason"),
                            }
                            
                            if "tool_calls" in delta:
                                chunk["tool_calls"] = delta["tool_calls"]
                            
                            yield chunk
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE data: {data_str}")
