"""
PRADA Agent - BlueBubbles Platform Adapter (iMessage bridge)
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class BlueBubblesAdapter(PlatformAdapter):
    """BlueBubbles iMessage bridge adapter"""
    
    def __init__(self, server_url: str, password: str):
        self.server_url = server_url.rstrip('/')
        self.password = password
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "bluebubbles"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for iMessage via BlueBubbles WebSocket"""
        self.callback = callback
        self.running = True
        
        import aiohttp
        ws_url = self.server_url.replace('http', 'ws') + '/api/v1/ws/messages'
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, headers={"Authorization": f"Bearer {self.password}"}) as ws:
                while self.running:
                    try:
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message(json.loads(msg.data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                    except Exception as e:
                        print(f"BlueBubbles WS error: {e}")
                        break
    
    async def stop(self) -> None:
        """Stop WebSocket connection"""
        self.running = False
    
    async def _handle_message(self, data: dict) -> None:
        """Process incoming iMessage"""
        if not self.callback:
            return
        
        # BlueBubbles message format
        guid = data.get('guid', '')
        text = data.get('text', '')
        sender = data.get('handle', {}).get('id', 'unknown')
        chat_id = data.get('chat', {}).get('guid', '')
        date_sent = data.get('date_sent', int(datetime.now().timestamp()))
        
        message = Message(
            id=guid,
            platform="bluebubbles",
            chat_id=chat_id,
            user_id=sender,
            content=text,
            timestamp=date_sent,
        )
        
        await self.callback(message)
    
    async def _api_request(self, endpoint: str, method: str = 'GET', data: Optional[dict] = None) -> dict:
        """Make BlueBubbles API request"""
        import aiohttp
        
        url = f"{self.server_url}/api/v1{endpoint}"
        headers = {"Authorization": f"Bearer {self.password}"}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            if method == 'GET':
                async with session.get(url) as response:
                    return await response.json()
            else:
                async with session.post(url, json=data or {}) as response:
                    return await response.json()
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send an iMessage via BlueBubbles"""
        msg_data = {
            "chatId": chat_id,
            "message": content,
        }
        
        result = await self._api_request("/message/send/text", method='POST', data=msg_data)
        return result.get('success', False)
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        await self._api_request(f"/typing/start/{chat_id}", method='POST')
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """iMessage doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """iMessage doesn't support deletion"""
        return False
