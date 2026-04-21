"""
PRADA Agent - SMS Platform Adapter (Twilio)
"""

import asyncio
from typing import Optional, Callable, List
from datetime import datetime

from gateway.run import PlatformAdapter, Message


class SMSAdapter(PlatformAdapter):
    """Twilio SMS adapter"""
    
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "sms"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for SMS messages via webhook"""
        self.callback = callback
        self.running = True
        # Twilio uses webhooks - this adapter expects webhook callbacks
        # via the gateway's webhook endpoint
        print(f"SMS adapter started for {self.phone_number}")
    
    async def stop(self) -> None:
        """Stop listening"""
        self.running = False
    
    async def handle_incoming_sms(self, from_number: str, body: str) -> None:
        """Handle incoming SMS (called by webhook)"""
        if not self.callback:
            return
        
        message = Message(
            id=f"sms_{int(datetime.now().timestamp())}",
            platform="sms",
            chat_id=from_number,
            user_id=from_number,
            content=body,
            timestamp=int(datetime.now().timestamp()),
        )
        
        await self.callback(message)
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send SMS via Twilio API"""
        import aiohttp
        from aiohttp import BasicAuth
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        data = {
            "From": self.phone_number,
            "To": chat_id,
            "Body": content,
        }
        
        auth = BasicAuth(self.account_sid, self.auth_token)
        
        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.post(url, data=data) as response:
                    result = await response.json()
                    return response.status == 201
        except Exception as e:
            print(f"SMS send error: {e}")
            return False
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """SMS doesn't support typing indicators"""
        pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """SMS doesn't support editing"""
        return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """SMS doesn't support deletion"""
        return False
