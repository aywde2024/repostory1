"""
Slack Platform Adapter - Bolt API + Events API support
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..run import PlatformAdapter, MessageContext

logger = logging.getLogger(__name__)


@dataclass
class SlackMessage(MessageContext):
    """Slack-specific message context"""
    channel: str
    thread_ts: Optional[str] = None
    team_id: str = ""


class SlackAdapter(PlatformAdapter):
    """Slack platform adapter using Bolt SDK"""
    
    def __init__(self, bot_token: str, signing_secret: str, app_token: Optional[str] = None):
        super().__init__("slack")
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.app_token = app_token
        self.client = None
        self.socket_mode_client = None
    
    async def connect(self) -> bool:
        """Initialize Slack connection"""
        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            
            self.app = App(token=self.bot_token, signing_secret=self.signing_secret)
            
            # Register message handler
            @self.app.event("message")
            def handle_message(event, say):
                pass  # Handled by gateway
            
            if self.app_token:
                from slack_sdk.socket_mode.aiohttp import SocketModeClient
                self.socket_mode_client = SocketModeClient(
                    app_token=self.app_token,
                    app=self.app
                )
                await self.socket_mode_client.connect()
            else:
                # Use HTTP mode
                pass
            
            logger.info("Slack adapter connected")
            return True
        except Exception as e:
            logger.error(f"Slack connection failed: {e}")
            return False
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str, 
        thread_ts: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send message to Slack channel/thread"""
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            client = AsyncWebClient(token=self.bot_token)
            
            result = await client.chat_postMessage(
                channel=chat_id,
                text=text,
                thread_ts=thread_ts,
                **kwargs
            )
            return result["ok"]
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    async def send_file(
        self,
        chat_id: str,
        file_path: str,
        title: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send file to Slack"""
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            client = AsyncWebClient(token=self.bot_token)
            
            with open(file_path, 'rb') as f:
                result = await client.files_upload_v2(
                    channel=chat_id,
                    file=f,
                    title=title or file_path.split('/')[-1],
                    **kwargs
                )
            return result["ok"]
        except Exception as e:
            logger.error(f"Failed to send Slack file: {e}")
            return False
    
    def parse_message(self, raw_data: Dict[str, Any]) -> Optional[SlackMessage]:
        """Parse incoming Slack event to MessageContext"""
        try:
            event = raw_data.get("event", {})
            
            # Skip bot messages
            if event.get("bot_id") or event.get("subtype") == "bot_message":
                return None
            
            return SlackMessage(
                platform="slack",
                user_id=event.get("user", ""),
                chat_id=event.get("channel", ""),
                content=event.get("text", ""),
                thread_ts=event.get("thread_ts"),
                team_id=raw_data.get("team_id", ""),
                timestamp=event.get("ts", ""),
            )
        except Exception as e:
            logger.error(f"Failed to parse Slack message: {e}")
            return None
    
    async def set_typing(self, chat_id: str) -> None:
        """Show typing indicator (Slack doesn't support this natively)"""
        pass
    
    async def disconnect(self) -> None:
        """Close Slack connection"""
        if self.socket_mode_client:
            await self.socket_mode_client.disconnect()
