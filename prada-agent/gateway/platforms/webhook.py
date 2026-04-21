"""
PRADA Agent - Webhook Platform Adapter (Generic JSON)
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class WebhookAdapter(PlatformAdapter):
    """Generic JSON Webhook adapter for receiving messages"""
    
    def __init__(self, port: int = 8080, secret: Optional[str] = None):
        self.port = port
        self.secret = secret
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
        self._server = None
    
    @property
    def platform_name(self) -> str:
        return "webhook"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start HTTP server to receive webhooks"""
        self.callback = callback
        self.running = True
        
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/webhook', self._handle_webhook)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        self._server = runner
        
        print(f"Webhook adapter started on port {self.port}")
    
    async def stop(self) -> None:
        """Stop HTTP server"""
        self.running = False
        if self._server:
            await self._server.cleanup()
    
    async def cleanup(self) -> None:
        """Alias for stop() - cleanup resources"""
        await self.stop()
    
    async def _handle_webhook(self, request) -> web.Response:
        """Handle incoming webhook POST"""
        from aiohttp import web
        
        # Verify secret if configured
        if self.secret:
            auth_header = request.headers.get('Authorization', '')
            if auth_header != f"Bearer {self.secret}":
                return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            data = await request.json()
        except:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        
        # Extract message fields (flexible format)
        user_id = data.get('user_id', data.get('sender', 'unknown'))
        chat_id = data.get('chat_id', data.get('room', user_id))
        content = data.get('content', data.get('text', data.get('message', '')))
        message_id = data.get('id', data.get('message_id', f"wh_{int(datetime.now().timestamp())}"))
        timestamp = data.get('timestamp', int(datetime.now().timestamp()))
        
        if self.callback and content:
            message = Message(
                id=str(message_id),
                platform="webhook",
                chat_id=str(chat_id),
                user_id=str(user_id),
                content=content,
                timestamp=timestamp,
            )
            await self.callback(message)
        
        return web.json_response({"status": "ok"})
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Webhook is receive-only by default, return False"""
        # For bidirectional use, implement custom delivery logic
        print(f"Webhook received message for {chat_id}: {content[:50]}...")
        return True
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Webhook doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """Webhook doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Webhook doesn't support deletion"""
        return False
