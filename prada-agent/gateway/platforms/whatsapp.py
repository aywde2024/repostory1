"""
WhatsApp Platform Adapter - Cloud API + Twilio fallback
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..run import PlatformAdapter, MessageContext

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessage(MessageContext):
    """WhatsApp-specific message context"""
    phone_number: str = ""
    message_type: str = "text"


class WhatsAppAdapter(PlatformAdapter):
    """WhatsApp platform adapter using Cloud API"""
    
    def __init__(self, access_token: str, phone_id: str, business_account_id: str):
        super().__init__("whatsapp")
        self.access_token = access_token
        self.phone_id = phone_id
        self.business_account_id = business_account_id
        self.base_url = "https://graph.facebook.com/v17.0"
        self._session = None
    
    async def connect(self) -> bool:
        """Initialize WhatsApp connection"""
        try:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            })
            
            # Verify phone number
            url = f"{self.base_url}/{self.phone_id}"
            response = self._session.get(url)
            if response.status_code == 200:
                logger.info("WhatsApp adapter connected")
                return True
            logger.error(f"WhatsApp connection failed: {response.text}")
            return False
        except Exception as e:
            logger.error(f"WhatsApp connection error: {e}")
            return False
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str, 
        **kwargs
    ) -> bool:
        """Send text message via WhatsApp Cloud API"""
        try:
            url = f"{self.base_url}/{self.phone_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "to": chat_id,
                "type": "text",
                "text": {"body": text}
            }
            
            response = self._session.post(url, json=payload)
            result = response.json()
            return "messages" in result
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
    
    async def send_file(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send media file via WhatsApp"""
        try:
            # First upload media
            url = f"{self.base_url}/{self.phone_id}/media"
            files = {"file": open(file_path, "rb")}
            data = {"messaging_product": "whatsapp", "type": self._get_media_type(file_path)}
            
            response = self._session.post(url, files=files, data=data)
            media_id = response.json().get("id")
            
            if not media_id:
                return False
            
            # Send message with media
            msg_url = f"{self.base_url}/{self.phone_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "to": chat_id,
                "type": self._get_media_type(file_path),
                self._get_media_type(file_path): {"id": media_id, "caption": caption or ""}
            }
            
            response = self._session.post(msg_url, json=payload)
            return "messages" in response.json()
        except Exception as e:
            logger.error(f"Failed to send WhatsApp file: {e}")
            return False
    
    def _get_media_type(self, file_path: str) -> str:
        """Determine media type from file extension"""
        ext = file_path.split(".")[-1].lower()
        media_types = {
            "jpg": "image", "jpeg": "image", "png": "image", "gif": "image",
            "mp4": "video", "avi": "video",
            "mp3": "audio", "ogg": "audio",
            "pdf": "document", "doc": "document", "docx": "document",
        }
        return media_types.get(ext, "document")
    
    def parse_message(self, raw_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """Parse incoming WhatsApp webhook to MessageContext"""
        try:
            entry = raw_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            msg = messages[0]
            return WhatsAppMessage(
                platform="whatsapp",
                user_id=msg.get("from", ""),
                chat_id=msg.get("from", ""),
                content=msg.get("text", {}).get("body", ""),
                phone_number=msg.get("from", ""),
                message_type=msg.get("type", "text"),
                timestamp=msg.get("timestamp", ""),
            )
        except Exception as e:
            logger.error(f"Failed to parse WhatsApp message: {e}")
            return None
    
    async def set_typing(self, chat_id: str) -> None:
        """WhatsApp doesn't support typing indicators via API"""
        pass
    
    async def disconnect(self) -> None:
        """Close WhatsApp session"""
        if self._session:
            self._session.close()
