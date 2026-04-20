"""
PRADA Agent - Discord Platform Adapter
"""

import asyncio
from typing import Optional, Callable, List

from gateway.run import PlatformAdapter, Message


class DiscordAdapter(PlatformAdapter):
    """Discord.py adapter with voice support"""
    
    def __init__(self, bot_token: str, intents: Optional[List[str]] = None):
        self.bot_token = bot_token
        self.intents = intents or ["messages", "message_content", "guilds"]
        self.client = None
        self.callback: Optional[Callable[[Message], None]] = None
        self.running = False
    
    @property
    def platform_name(self) -> str:
        return "discord"
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start Discord bot"""
        try:
            import discord
            from discord.ext import commands
        except ImportError:
            print("Discord not installed. Install with: pip install discord.py")
            return
        
        self.callback = callback
        self.running = True
        
        # Set up intents
        intents_obj = discord.Intents.default()
        if "messages" in self.intents:
            intents_obj.message_content = True
            intents_obj.messages = True
        if "guilds" in self.intents:
            intents_obj.guilds = True
        
        # Create bot
        self.client = commands.Bot(command_prefix='!', intents=intents_obj)
        
        @self.client.event
        async def on_ready():
            print(f"Discord bot logged in as {self.client.user}")
        
        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return
            
            await self._handle_message(message)
        
        # Start bot
        await self.client.start(self.bot_token)
    
    async def stop(self) -> None:
        """Stop Discord bot"""
        self.running = False
        if self.client:
            await self.client.close()
    
    async def _handle_message(self, message) -> None:
        """Process incoming Discord message"""
        if not self.callback:
            return
        
        msg = Message(
            id=str(message.id),
            platform="discord",
            chat_id=str(message.channel.id),
            user_id=str(message.author.id),
            content=message.content,
            timestamp=message.created_at.timestamp(),
            thread_id=str(message.thread.id) if hasattr(message, 'thread') and message.thread else None,
            reply_to=str(message.reference.message_id) if message.reference else None,
            attachments=[{
                "type": "image" if att.filename.lower().endswith(('.png', '.jpg', '.gif')) else "file",
                "url": att.url,
                "filename": att.filename,
            } for att in message.attachments] if message.attachments else None,
        )
        
        await self.callback(msg)
    
    async def send_message(self, chat_id: str, content: str,
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to Discord"""
        if not self.client:
            return False
        
        try:
            channel = self.client.get_channel(int(chat_id))
            if not channel:
                channel = await self.client.fetch_channel(int(chat_id))
            
            # Handle reply
            reference = None
            if reply_to:
                reference = discord.MessageReference(message_id=int(reply_to))
            
            # Send message
            await channel.send(
                content=content,
                reference=reference,
            )
            return True
        except Exception as e:
            print(f"Discord send error: {e}")
            return False
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        if not self.client:
            return
        
        try:
            channel = self.client.get_channel(int(chat_id))
            if channel:
                await channel.typing()
        except Exception:
            pass
    
    async def edit_message(self, chat_id: str, message_id: str,
                          new_content: str) -> bool:
        """Edit a message"""
        if not self.client:
            return False
        
        try:
            channel = self.client.get_channel(int(chat_id))
            if not channel:
                channel = await self.client.fetch_channel(int(chat_id))
            
            message = await channel.fetch_message(int(message_id))
            await message.edit(content=new_content)
            return True
        except Exception as e:
            print(f"Discord edit error: {e}")
            return False
    
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Delete a message"""
        if not self.client:
            return False
        
        try:
            channel = self.client.get_channel(int(chat_id))
            if not channel:
                channel = await self.client.fetch_channel(int(chat_id))
            
            message = await channel.fetch_message(int(message_id))
            await message.delete()
            return True
        except Exception as e:
            print(f"Discord delete error: {e}")
            return False
