"""
PRADA Agent - Gateway Message Distribution System
Handles multi-platform messaging with session routing
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod


@dataclass
class Message:
    """Unified message format across all platforms"""
    id: str
    platform: str
    chat_id: str
    user_id: str
    content: str
    timestamp: float
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    attachments: Optional[List[dict]] = None
    is_edit: bool = False
    is_delete: bool = False
    metadata: Optional[dict] = None


@dataclass
class SessionState:
    """Session state for a user"""
    session_id: str
    user_id: str
    platform: str
    created_at: float
    last_activity: float
    message_history: List[dict]
    context: dict


class PlatformAdapter(ABC):
    """Abstract base class for platform adapters"""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform name"""
        pass
    
    @abstractmethod
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for messages"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop listening"""
        pass
    
    @abstractmethod
    async def send_message(self, chat_id: str, content: str, 
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to the platform"""
        pass
    
    @abstractmethod
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        pass
    
    @abstractmethod
    async def edit_message(self, chat_id: str, message_id: str, 
                          new_content: str) -> bool:
        """Edit an existing message"""
        pass
    
    @abstractmethod
    async def delete_message(self, chat_id: str, message_id: str) -> bool:
        """Delete a message"""
        pass


class SessionStore:
    """Persistent session storage"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, SessionState] = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from disk"""
        session_file = self.data_dir / "sessions.json"
        if session_file.exists():
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    for sid, sdata in data.items():
                        self.sessions[sid] = SessionState(**sdata)
            except Exception as e:
                print(f"Error loading sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to disk"""
        session_file = self.data_dir / "sessions.json"
        try:
            with open(session_file, 'w') as f:
                data = {sid: asdict(s) for sid, s in self.sessions.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def get_or_create_session(self, user_id: str, platform: str) -> SessionState:
        """Get existing session or create new one"""
        # Find existing session for this user
        for session in self.sessions.values():
            if session.user_id == user_id and session.platform == platform:
                return session
        
        # Create new session
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        session = SessionState(
            session_id=session_id,
            user_id=user_id,
            platform=platform,
            created_at=datetime.now().timestamp(),
            last_activity=datetime.now().timestamp(),
            message_history=[],
            context={},
        )
        self.sessions[session_id] = session
        self._save_sessions()
        return session
    
    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Optional[dict] = None):
        """Add a message to session history"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        session.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().timestamp(),
            "metadata": metadata or {},
        })
        session.last_activity = datetime.now().timestamp()
        
        # Limit history size
        max_messages = 100
        if len(session.message_history) > max_messages:
            session.message_history = session.message_history[-max_messages:]
        
        self._save_sessions()
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[SessionState]:
        """List all sessions"""
        return list(self.sessions.values())
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return False


class GatewayRunner:
    """Main gateway message distributor"""
    
    def __init__(self, config: dict):
        self.config = config
        self.adapters: Dict[str, PlatformAdapter] = {}
        self.session_store: Optional[SessionStore] = None
        self.message_callback: Optional[Callable[[Message], None]] = None
        self.running = False
        self._tasks: List[asyncio.Task] = []
        
        # Initialize session store
        prada_home = Path(config.get("prada_home", "~/.prada")).expanduser()
        self.session_store = SessionStore(prada_home / "gateway")
    
    def register_adapter(self, adapter: PlatformAdapter):
        """Register a platform adapter"""
        self.adapters[adapter.platform_name] = adapter
        print(f"Registered adapter: {adapter.platform_name}")
    
    def set_message_callback(self, callback: Callable[[Message], None]):
        """Set callback for incoming messages"""
        self.message_callback = callback
    
    async def start(self):
        """Start all platform adapters"""
        self.running = True
        
        for name, adapter in self.adapters.items():
            try:
                task = asyncio.create_task(adapter.start(self._handle_message))
                self._tasks.append(task)
                print(f"Started adapter: {name}")
            except Exception as e:
                print(f"Failed to start adapter {name}: {e}")
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop all adapters"""
        self.running = False
        
        for adapter in self.adapters.values():
            try:
                await adapter.stop()
            except Exception as e:
                print(f"Error stopping adapter: {e}")
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        print("Gateway stopped")
    
    async def _handle_message(self, message: Message):
        """Handle incoming message"""
        if not self.message_callback:
            return
        
        # Get or create session
        session = self.session_store.get_or_create_session(
            message.user_id, message.platform
        )
        
        # Add user message to history
        self.session_store.add_message(
            session.session_id,
            "user",
            message.content,
            metadata={"platform": message.platform, "chat_id": message.chat_id},
        )
        
        # Call the agent callback
        await self.message_callback(message, session)
    
    async def send_response(self, platform: str, chat_id: str, content: str,
                           thread_id: Optional[str] = None,
                           reply_to: Optional[str] = None) -> bool:
        """Send a response message"""
        if platform not in self.adapters:
            print(f"Unknown platform: {platform}")
            return False
        
        adapter = self.adapters[platform]
        return await adapter.send_message(
            chat_id, content, thread_id, reply_to
        )
    
    async def broadcast(self, content: str, platforms: Optional[List[str]] = None) -> int:
        """Broadcast message to multiple platforms"""
        platforms = platforms or list(self.adapters.keys())
        sent_count = 0
        
        for platform in platforms:
            if platform in self.adapters:
                # Get all chat IDs for this platform
                for session in self.session_store.list_sessions():
                    if session.platform == platform:
                        # Extract chat_id from metadata
                        if session.message_history:
                            last_msg = session.message_history[-1]
                            chat_id = last_msg.get("metadata", {}).get("chat_id")
                            if chat_id:
                                success = await self.send_response(
                                    platform, chat_id, content
                                )
                                if success:
                                    sent_count += 1
        
        return sent_count


# Delivery tracking
@dataclass
class DeliveryStatus:
    message_id: str
    platform: str
    chat_id: str
    status: str  # pending, sent, delivered, failed
    timestamp: float
    error: Optional[str] = None


class DeliveryTracker:
    """Track message delivery status"""
    
    def __init__(self):
        self.deliveries: Dict[str, DeliveryStatus] = {}
    
    def track(self, message_id: str, platform: str, chat_id: str):
        """Start tracking a message"""
        self.deliveries[message_id] = DeliveryStatus(
            message_id=message_id,
            platform=platform,
            chat_id=chat_id,
            status="pending",
            timestamp=datetime.now().timestamp(),
        )
    
    def update(self, message_id: str, status: str, error: Optional[str] = None):
        """Update delivery status"""
        if message_id in self.deliveries:
            self.deliveries[message_id].status = status
            self.deliveries[message_id].error = error
            self.deliveries[message_id].timestamp = datetime.now().timestamp()
    
    def get_status(self, message_id: str) -> Optional[DeliveryStatus]:
        """Get delivery status"""
        return self.deliveries.get(message_id)
