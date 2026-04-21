"""
PRADA Agent - API Server Platform Adapter (OpenAI-compatible REST API)
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class APIServerAdapter(PlatformAdapter):
    """OpenAI-compatible REST API server adapter"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8000, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
        self._server = None
        self._sessions = {}  # Store active chat sessions
    
    @property
    def platform_name(self) -> str:
        return "api_server"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start OpenAI-compatible API server"""
        self.callback = callback
        self.running = True
        
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/v1/chat/completions', self._handle_chat)
        app.router.add_get('/health', self._handle_health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self._server = runner
        
        print(f"API Server started on {self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop API server"""
        self.running = False
        if self._server:
            await self._server.cleanup()
    
    def _verify_auth(self, request) -> bool:
        """Verify API key if configured"""
        if not self.api_key:
            return True
        
        auth_header = request.headers.get('Authorization', '')
        return auth_header == f"Bearer {self.api_key}"
    
    async def _handle_health(self, request) -> web.Response:
        """Health check endpoint"""
        from aiohttp import web
        return web.json_response({"status": "healthy"})
    
    async def _handle_chat(self, request) -> web.Response:
        """Handle chat completions request (OpenAI-compatible)"""
        from aiohttp import web
        
        if not self._verify_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            data = await request.json()
        except:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        
        # Extract conversation context
        messages = data.get('messages', [])
        model = data.get('model', 'prada-agent')
        stream = data.get('stream', False)
        
        # Get or create session ID
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Get last user message
        user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        if not user_message and self.callback:
            return web.json_response({
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "No user message provided"},
                    "finish_reason": "stop"
                }]
            })
        
        # Create message object for agent
        message = Message(
            id=f"api_{uuid.uuid4()}",
            platform="api_server",
            chat_id=session_id,
            user_id=session_id,
            content=user_message,
            timestamp=int(datetime.now().timestamp()),
            metadata={"messages": messages, "model": model}
        )
        
        # Process through agent
        if self.callback:
            await self.callback(message)
        
        # For now, return placeholder response
        # In production, this would wait for agent response
        response_content = "Message received and being processed..."
        
        return web.json_response({
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response_content},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 10,
                "total_tokens": 10
            }
        })
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send message via API (stored in session)"""
        # In streaming mode, responses are sent via SSE
        self._sessions[chat_id] = content
        return True
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """API doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """API doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """API doesn't support deletion"""
        return False
