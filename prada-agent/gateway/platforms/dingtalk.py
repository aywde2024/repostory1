"""
PRADA Agent - DingTalk Platform Adapter
"""

import asyncio
import json
import hmac
import hashlib
import base64
from typing import Optional, Callable, List
from datetime import datetime
from urllib.parse import quote_plus

from gateway.run import PlatformAdapter, Message


class DingTalkAdapter(PlatformAdapter):
    """DingTalk (钉钉) Robot Webhook adapter"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "dingtalk"
    
    def _sign_webhook(self) -> str:
        """Generate signed webhook URL"""
        if not self.secret:
            return self.webhook_url
        
        timestamp = str(round(datetime.now().timestamp() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = quote_plus(base64.b64encode(hmac_code))
        
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for DingTalk messages via webhook"""
        self.callback = callback
        self.running = True
        print(f"DingTalk adapter started")
    
    async def stop(self) -> None:
        """Stop listening"""
        self.running = False
    
    async def handle_incoming_message(self, data: dict) -> None:
        """Handle incoming webhook message"""
        if not self.callback:
            return
        
        msg_type = data.get('msgtype', 'text')
        sender_id = data.get('senderId', 'unknown')
        conversation_id = data.get('conversationId', 'default')
        
        content = ''
        if msg_type == 'text':
            content = data.get('text', {}).get('content', '')
        
        message = Message(
            id=f"dingtalk_{int(datetime.now().timestamp())}",
            platform="dingtalk",
            chat_id=conversation_id,
            user_id=sender_id,
            content=content,
            timestamp=int(datetime.now().timestamp()),
        )
        
        await self.callback(message)
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to DingTalk"""
        import aiohttp
        
        url = self._sign_webhook()
        
        msg_data = {
            "msgtype": "text",
            "text": {"content": content},
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=msg_data) as response:
                    result = await response.json()
                    return result.get('errcode', 0) == 0
        except Exception as e:
            print(f"DingTalk send error: {e}")
            return False
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """DingTalk doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """DingTalk doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """DingTalk doesn't support deletion"""
        return False
