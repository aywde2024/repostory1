"""
PRADA Agent - Home Assistant Platform Adapter
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class HomeAssistantAdapter(PlatformAdapter):
    """Home Assistant MQTT/REST adapter"""
    
    def __init__(self, base_url: str, token: str, notify_service: str = "notify"):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.notify_service = notify_service
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "homeassistant"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for HA events via WebSocket"""
        self.callback = callback
        self.running = True
        
        import aiohttp
        ws_url = f"{self.base_url.replace('http', 'ws')}/api/websocket"
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                # Auth
                await ws.send_json({"type": "auth", "access_token": self.token})
                
                # Subscribe to events
                await ws.send_json({
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "prada_message"
                })
                
                while self.running:
                    try:
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get('type') == 'event':
                                await self._handle_message(data['event']['data'])
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                    except Exception as e:
                        print(f"HA WS error: {e}")
                        break
    
    async def stop(self) -> None:
        """Stop WebSocket connection"""
        self.running = False
    
    async def _handle_message(self, data: dict) -> None:
        """Process incoming HA event"""
        if not self.callback:
            return
        
        event_data = data.get('data', {})
        sender = event_data.get('sender', 'unknown')
        content = event_data.get('message', '')
        
        message = Message(
            id=f"ha_{int(datetime.now().timestamp())}",
            platform="homeassistant",
            chat_id="homeassistant",
            user_id=sender,
            content=content,
            timestamp=int(datetime.now().timestamp()),
        )
        
        await self.callback(message)
    
    async def _api_request(self, endpoint: str, method: str = 'GET', data: Optional[dict] = None) -> dict:
        """Make Home Assistant API request"""
        import aiohttp
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        
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
        """Send notification via Home Assistant"""
        data = {
            "message": content,
        }
        
        # Add title if provided
        if thread_id:
            data["title"] = thread_id
        
        result = await self._api_request(
            f"/api/services/{self.notify_service}/persistent_notification",
            method='POST',
            data=data
        )
        return True  # HA doesn't return meaningful response
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """HA doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """HA doesn't support editing notifications"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Dismiss a notification"""
        # Would need to track notification IDs
        return False
    
    # Home Assistant specific methods
    
    async def get_entities(self, domain: Optional[str] = None) -> List[dict]:
        """Get all entities or filter by domain"""
        states = await self._api_request("/api/states")
        if domain:
            return [e for e in states if e['entity_id'].startswith(domain + '.')]
        return states
    
    async def get_entity_state(self, entity_id: str) -> Optional[dict]:
        """Get state of a specific entity"""
        return await self._api_request(f"/api/states/{entity_id}")
    
    async def call_service(self, domain: str, service: str, 
                          target: Optional[dict] = None,
                          data: Optional[dict] = None) -> bool:
        """Call a Home Assistant service"""
        payload = data or {}
        if target:
            payload.update(target)
        
        result = await self._api_request(
            f"/api/services/{domain}/{service}",
            method='POST',
            data=payload
        )
        return True
