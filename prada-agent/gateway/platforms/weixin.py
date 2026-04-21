"""
PRADA Agent - Weixin (微信) Platform Adapter
"""

import asyncio
import json
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class WeixinAdapter(PlatformAdapter):
    """Weixin (微信公众号/小程序) adapter"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token: Optional[str] = None
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "weixin"
    
    async def _get_access_token(self) -> str:
        """Get Weixin access token"""
        import aiohttp
        
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.access_token = data.get('access_token')
                return self.access_token
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for Weixin messages"""
        self.callback = callback
        self.running = True
        await self._get_access_token()
        print(f"Weixin adapter started")
    
    async def stop(self) -> None:
        """Stop listening"""
        self.running = False
    
    async def handle_incoming_message(self, data: dict) -> None:
        """Handle incoming message (called by webhook)"""
        if not self.callback:
            return
        
        msg_type = data.get('MsgType', 'text')
        from_user = data.get('FromUserName', 'unknown')
        
        content = ''
        if msg_type == 'text':
            content = data.get('Content', '')
        elif msg_type == 'image':
            content = f"[Image] {data.get('PicUrl', '')}"
        elif msg_type == 'voice':
            content = f"[Voice] {data.get('Recognition', '[Audio]')}"
        
        message = Message(
            id=f"weixin_{int(datetime.now().timestamp())}",
            platform="weixin",
            chat_id=from_user,
            user_id=from_user,
            content=content,
            timestamp=int(data.get('CreateTime', datetime.now().timestamp())),
        )
        
        await self.callback(message)
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to Weixin user"""
        import aiohttp
        
        if not self.access_token:
            await self._get_access_token()
        
        url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={self.access_token}"
        
        msg_data = {
            "touser": chat_id,
            "msgtype": "text",
            "text": {"content": content},
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=msg_data) as response:
                    result = await response.json()
                    return result.get('errcode', 0) == 0
        except Exception as e:
            print(f"Weixin send error: {e}")
            return False
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Weixin doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """Weixin doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Weixin doesn't support deletion"""
        return False
