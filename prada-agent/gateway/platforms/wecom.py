"""
PRADA Agent - WeCom (企业微信) Platform Adapter
"""

import asyncio
import json
import hmac
import hashlib
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class WeComAdapter(PlatformAdapter):
    """WeCom (企业微信) Robot adapter"""
    
    def __init__(self, corp_id: str, agent_id: str, secret: str):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.access_token: Optional[str] = None
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "wecom"
    
    async def _get_access_token(self) -> str:
        """Get WeCom access token"""
        import aiohttp
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.secret}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                self.access_token = data.get('access_token')
                return self.access_token
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for WeCom messages"""
        self.callback = callback
        self.running = True
        await self._get_access_token()
        print(f"WeCom adapter started")
    
    async def stop(self) -> None:
        """Stop listening"""
        self.running = False
    
    async def handle_incoming_message(self, data: dict) -> None:
        """Handle incoming message (called by webhook/callback)"""
        if not self.callback:
            return
        
        msg_type = data.get('MsgType', 'text')
        from_user = data.get('FromUserName', 'unknown')
        to_agent = data.get('ToUserName', '')
        
        content = ''
        if msg_type == 'text':
            content = data.get('Content', '')
        
        message = Message(
            id=f"wecom_{int(datetime.now().timestamp())}",
            platform="wecom",
            chat_id=from_user,
            user_id=from_user,
            content=content,
            timestamp=int(datetime.now().timestamp()),
        )
        
        await self.callback(message)
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to WeCom"""
        import aiohttp
        
        if not self.access_token:
            await self._get_access_token()
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.access_token}"
        
        msg_data = {
            "touser": chat_id,
            "msgtype": "text",
            "agentid": int(self.agent_id),
            "text": {"content": content},
            "safe": 0,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=msg_data) as response:
                    result = await response.json()
                    return result.get('errcode', 0) == 0
        except Exception as e:
            print(f"WeCom send error: {e}")
            return False
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """WeCom doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """WeCom doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """WeCom doesn't support deletion"""
        return False
