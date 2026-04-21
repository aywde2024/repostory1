"""
PRADA Agent - Mattermost Platform Adapter
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class MattermostAdapter(PlatformAdapter):
    """Mattermost WebSocket API adapter"""
    
    def __init__(self, server_url: str, access_token: str):
        self.server_url = server_url.rstrip('/')
        self.access_token = access_token
        self.ws_url = server_url.replace('http', 'ws').rstrip('/') + '/api/v4/websocket'
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
        self._ws = None
    
    @property
    def platform_name(self) -> str:
        return "mattermost"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start WebSocket connection"""
        self.callback = callback
        self.running = True
        
        import aiohttp
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.ws_connect(self.ws_url) as ws:
                self._ws = ws
                while self.running:
                    try:
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message(json.loads(msg.data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                    except Exception as e:
                        print(f"Mattermost WS error: {e}")
                        break
    
    async def stop(self) -> None:
        """Stop WebSocket connection"""
        self.running = False
        if self._ws:
            await self._ws.close()
    
    async def _handle_message(self, data: dict) -> None:
        """Process incoming WebSocket message"""
        if not self.callback or 'event' not in data:
            return
        
        event = data.get('event', '')
        
        if event == 'posted':
            post_data = data.get('data', {})
            post = json.loads(post_data.get('post', '{}'))
            
            message = Message(
                id=post.get('id', ''),
                platform="mattermost",
                chat_id=post.get('channel_id', ''),
                user_id=post.get('user_id', ''),
                content=post.get('message', ''),
                timestamp=int(datetime.now().timestamp()),
                thread_id=post.get('parent_id'),
            )
            
            await self.callback(message)
    
    async def _api_request(self, endpoint: str, method: str = 'GET', data: Optional[dict] = None) -> dict:
        """Make Mattermost API request"""
        import aiohttp
        
        url = f"{self.server_url}/api/v4{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
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
        """Send a message to Mattermost"""
        post_data = {
            "channel_id": chat_id,
            "message": content,
        }
        
        if thread_id:
            post_data["root_id"] = thread_id
        
        result = await self._api_request("/posts", method='POST', data=post_data)
        return 'id' in result
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        # Mattermost doesn't have direct typing API, skip
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """Edit a message"""
        data = {"message": new_content}
        result = await self._api_request(f"/posts/{message_id}", method='PUT', data=data)
        return 'id' in result
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Delete a message"""
        try:
            await self._api_request(f"/posts/{message_id}", method='DELETE')
            return True
        except:
            return False
