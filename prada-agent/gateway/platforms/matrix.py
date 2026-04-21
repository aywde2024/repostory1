"""
PRADA Agent - Matrix Platform Adapter
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class MatrixAdapter(PlatformAdapter):
    """Matrix Client-Server API adapter"""
    
    def __init__(self, homeserver: str, access_token: str, user_id: str):
        self.homeserver = homeserver.rstrip('/')
        self.access_token = access_token
        self.user_id = user_id
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
        self._next_batch = None
    
    @property
    def platform_name(self) -> str:
        return "matrix"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start syncing with Matrix server"""
        self.callback = callback
        self.running = True
        
        while self.running:
            try:
                await self._sync()
            except Exception as e:
                print(f"Matrix sync error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self) -> None:
        """Stop syncing"""
        self.running = False
    
    async def _sync(self) -> None:
        """Sync with Matrix server"""
        import aiohttp
        
        url = f"{self.homeserver}/_matrix/client/v3/sync"
        params = {"access_token": self.access_token, "timeout": 30000}
        
        if self._next_batch:
            params["since"] = self._next_batch
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if 'next_batch' in data:
                    self._next_batch = data['next_batch']
                
                # Process rooms
                rooms = data.get('rooms', {})
                for room_id, room_data in rooms.get('join', {}).items():
                    for event in room_data.get('timeline', {}).get('events', []):
                        if event.get('type') == 'm.room.message':
                            await self._handle_message(room_id, event)
    
    async def _handle_message(self, room_id: str, event: dict) -> None:
        """Process incoming Matrix message"""
        if not self.callback:
            return
        
        sender = event.get('sender', '')
        content = event.get('content', {})
        msg_type = content.get('msgtype', 'm.text')
        body = content.get('body', '')
        
        # Skip own messages
        if sender == self.user_id:
            return
        
        message = Message(
            id=event.get('event_id', ''),
            platform="matrix",
            chat_id=room_id,
            user_id=sender,
            content=body,
            timestamp=int(datetime.now().timestamp()),
            thread_id=None,  # Matrix threads handled differently
        )
        
        await self.callback(message)
    
    async def _api_request(self, endpoint: str, method: str = 'GET', data: Optional[dict] = None) -> dict:
        """Make Matrix API request"""
        import aiohttp
        
        url = f"{self.homeserver}{endpoint}"
        params = {"access_token": self.access_token}
        
        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(url, params=params) as response:
                    return await response.json()
            else:
                async with session.post(url, params=params, json=data or {}) as response:
                    return await response.json()
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to Matrix room"""
        event_data = {
            "msgtype": "m.text",
            "body": content,
        }
        
        # Handle replies
        if reply_to:
            event_data["m.relates_to"] = {
                "m.in_reply_to": {"event_id": reply_to}
            }
        
        result = await self._api_request(
            f"/_matrix/client/v3/rooms/{chat_id}/send/m.room.message",
            method='POST',
            data=event_data
        )
        return 'event_id' in result
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        await self._api_request(
            f"/_matrix/client/v3/rooms/{chat_id}/typing/{self.user_id}",
            method='PUT',
            data={"typing": True, "timeout": 30000}
        )
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """Edit a message (Matrix uses relations)"""
        event_data = {
            "msgtype": "m.text",
            "body": f"* {new_content}",
            "m.new_content": {
                "msgtype": "m.text",
                "body": new_content
            },
            "m.relates_to": {
                "rel_type": "m.replace",
                "event_id": message_id
            }
        }
        
        result = await self._api_request(
            f"/_matrix/client/v3/rooms/{chat_id}/send/m.room.message",
            method='POST',
            data=event_data
        )
        return 'event_id' in result
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Redact (delete) a message"""
        result = await self._api_request(
            f"/_matrix/client/v3/rooms/{chat_id}/redact/{message_id}",
            method='POST',
            data={"reason": "Deleted by bot"}
        )
        return 'event_id' in result
