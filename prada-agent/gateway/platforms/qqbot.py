"""
PRADA Agent - QQBot Platform Adapter (OneBot protocol)
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class QQBotAdapter(PlatformAdapter):
    """QQBot OneBot protocol adapter (WebSocket)"""
    
    def __init__(self, ws_url: str, access_token: Optional[str] = None):
        self.ws_url = ws_url
        self.access_token = access_token
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "qqbot"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start WebSocket connection to OneBot server"""
        self.callback = callback
        self.running = True
        
        import aiohttp
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.ws_connect(self.ws_url) as ws:
                while self.running:
                    try:
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get('post_type') == 'message':
                                await self._handle_message(data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                    except Exception as e:
                        print(f"QQBot WS error: {e}")
                        break
    
    async def stop(self) -> None:
        """Stop WebSocket connection"""
        self.running = False
    
    async def _handle_message(self, data: dict) -> None:
        """Process incoming QQ message"""
        if not self.callback:
            return
        
        message_type = data.get('message_type', 'private')
        user_id = str(data.get('user_id', ''))
        
        if message_type == 'private':
            chat_id = f"private_{user_id}"
        else:
            chat_id = str(data.get('group_id', ''))
        
        # Extract text from message
        raw_message = data.get('message', [])
        content = ''
        
        if isinstance(raw_message, str):
            content = raw_message
        elif isinstance(raw_message, list):
            for segment in raw_message:
                if segment.get('type') == 'text':
                    content += segment.get('data', {}).get('text', '')
        
        message = Message(
            id=str(data.get('message_id', '')),
            platform="qqbot",
            chat_id=chat_id,
            user_id=user_id,
            content=content.strip(),
            timestamp=data.get('time', int(datetime.now().timestamp())),
        )
        
        await self.callback(message)
    
    async def _send_ws_action(self, ws, action: str, params: dict) -> dict:
        """Send action via WebSocket"""
        payload = {
            "action": action,
            "params": params,
        }
        await ws.send_json(payload)
        # Note: Response handling would need proper request tracking
        return {}
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message via OneBot"""
        import aiohttp
        
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        # Determine if private or group message
        is_private = chat_id.startswith('private_')
        target_id = chat_id.replace('private_', '') if is_private else chat_id
        
        params = {
            "message": content,
        }
        
        if is_private:
            params["user_id"] = int(target_id)
        else:
            params["group_id"] = int(target_id)
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                # Use HTTP API for sending (more reliable than WS response tracking)
                http_url = self.ws_url.replace('ws', 'http').replace('/ws', '')
                async with session.post(f"{http_url}/send_msg", json=params) as response:
                    result = await response.json()
                    return result.get('status') == 'ok'
        except Exception as e:
            print(f"QQBot send error: {e}")
            return False
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """QQ doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """QQ doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Recall a message"""
        import aiohttp
        
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                http_url = self.ws_url.replace('ws', 'http').replace('/ws', '')
                async with session.post(f"{http_url}/delete_msg", json={"message_id": int(message_id)}) as response:
                    result = await response.json()
                    return result.get('status') == 'ok'
        except:
            return False
