"""
PRADA Agent - Telegram Platform Adapter
"""

import asyncio
import json
from typing import Optional, Callable, List
from pathlib import Path

from gateway.run import PlatformAdapter, Message


class TelegramAdapter(PlatformAdapter):
    """Telegram Bot API adapter"""
    
    def __init__(self, bot_token: str, webhook_url: Optional[str] = None):
        self.bot_token = bot_token
        self.webhook_url = webhook_url
        self.api_base = f"https://api.telegram.org/bot{bot_token}"
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
        self._last_update_id = 0
    
    @property
    def platform_name(self) -> str:
        return "telegram"
    
    async def _api_request(self, method: str, data: Optional[dict] = None) -> dict:
        """Make Telegram API request"""
        import aiohttp
        
        url = f"{self.api_base}/{method}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data or {}) as response:
                return await response.json()
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start polling for messages"""
        self.callback = callback
        self.running = True
        
        # Set webhook if provided, otherwise use polling
        if self.webhook_url:
            await self._api_request("setWebhook", {"url": self.webhook_url})
        else:
            # Delete webhook for polling mode
            await self._api_request("deleteWebhook")
        
        # Start polling
        while self.running:
            try:
                await self._poll_messages()
            except Exception as e:
                print(f"Telegram polling error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self) -> None:
        """Stop polling"""
        self.running = False
    
    async def _poll_messages(self) -> None:
        """Poll for new messages"""
        result = await self._api_request("getUpdates", {
            "offset": self._last_update_id + 1,
            "timeout": 30,
        })
        
        if not result.get("ok"):
            return
        
        updates = result.get("result", [])
        
        for update in updates:
            self._last_update_id = update["update_id"]
            
            # Handle message
            if "message" in update:
                msg = update["message"]
                await self._handle_message(msg)
            elif "callback_query" in update:
                # Handle callback query (inline buttons)
                query = update["callback_query"]
                await self._handle_callback_query(query)
    
    async def _handle_message(self, msg: dict) -> None:
        """Process incoming message"""
        if not self.callback:
            return
        
        chat_id = str(msg["chat"]["id"])
        user_id = str(msg["from"]["id"])
        content = msg.get("text", "")
        message_id = str(msg["message_id"])
        timestamp = msg.get("date", 0)
        
        # Handle thread (supergroup topics)
        thread_id = None
        if "is_topic_message" in msg and msg["is_topic_message"]:
            thread_id = str(msg["message_thread_id"])
        
        # Handle reply
        reply_to = None
        if "reply_to_message" in msg:
            reply_to = str(msg["reply_to_message"]["message_id"])
        
        # Handle attachments
        attachments = []
        if "photo" in msg:
            attachments.append({
                "type": "photo",
                "file_id": msg["photo"][-1]["file_id"],
            })
        if "document" in msg:
            attachments.append({
                "type": "document",
                "file_id": msg["document"]["file_id"],
            })
        if "voice" in msg:
            attachments.append({
                "type": "voice",
                "file_id": msg["voice"]["file_id"],
            })
        
        message = Message(
            id=message_id,
            platform="telegram",
            chat_id=chat_id,
            user_id=user_id,
            content=content,
            timestamp=timestamp,
            thread_id=thread_id,
            reply_to=reply_to,
            attachments=attachments if attachments else None,
        )
        
        await self.callback(message)
    
    async def _handle_callback_query(self, query: dict) -> None:
        """Handle inline button callback"""
        # Similar to message handling but for button clicks
        pass
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to Telegram"""
        data = {
            "chat_id": chat_id,
            "text": content,
            "parse_mode": "Markdown",
        }
        
        if thread_id:
            data["message_thread_id"] = thread_id
        
        if reply_to:
            data["reply_to_message_id"] = reply_to
        
        result = await self._api_request("sendMessage", data)
        return result.get("ok", False)
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        data = {"chat_id": chat_id, "action": "typing"}
        await self._api_request("sendChatAction", data)
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """Edit a message"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_content,
            "parse_mode": "Markdown",
        }
        result = await self._api_request("editMessageText", data)
        return result.get("ok", False)
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Delete a message"""
        data = {"chat_id": chat_id, "message_id": message_id}
        result = await self._api_request("deleteMessage", data)
        return result.get("ok", False)
