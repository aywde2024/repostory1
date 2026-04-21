"""
Context Engine - Manages conversation context and compression
Abstract base class for pluggable context engines
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Message:
    """Simple message container"""
    def __init__(self, role: str, content: str, **kwargs):
        self.role = role
        self.content = content
        self.extra = kwargs
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            **self.extra
        }


class ContextEngine(ABC):
    """
    Abstract base class for context management.
    
    Subclasses can implement different strategies:
    - DefaultCompressor: Lossy summarization
    - TokenCounter: Exact token counting
    - VectorStore: Semantic retrieval
    - Hybrid: Combination approaches
    """
    
    def __init__(self, prada_home: Path, config: Optional[Dict] = None):
        self.prada_home = prada_home
        self.config = config or {}
        self._stats = {
            "compressions": 0,
            "tokens_removed": 0,
            "original_tokens": 0,
        }
    
    @abstractmethod
    async def compress(
        self,
        messages: List[Message],
        target_tokens: int,
    ) -> List[Message]:
        """
        Compress message list to fit within target token count.
        
        Args:
            messages: List of conversation messages
            target_tokens: Maximum tokens to fit
            
        Returns:
            Compressed message list
        """
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        pass
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        return self._stats.copy()
    
    def _protect_header(self, messages: List[Message]) -> List[Message]:
        """
        Protect system prompt and first user message from compression.
        
        Returns messages that should never be compressed.
        """
        protected = []
        
        # Always protect system message
        for msg in messages:
            if msg.role == "system":
                protected.append(msg)
                break
        
        # Protect first user message
        user_msg_found = False
        for msg in messages:
            if msg.role == "user" and not user_msg_found:
                protected.append(msg)
                user_msg_found = True
                break
        
        return protected


class DefaultContextEngine(ContextEngine):
    """
    Default context engine with lossy summarization.
    
    Strategy:
    1. Keep system prompt intact
    2. Keep first and last N user/assistant turns
    3. Summarize middle conversations
    4. Preserve all tool calls and results
    """
    
    def __init__(self, prada_home: Path, config: Optional[Dict] = None):
        super().__init__(prada_home, config)
        self.keep_recent_turns = (config or {}).get('keep_recent_turns', 5)
        self.summary_model = (config or {}).get('summary_model', 'gemini-1.5-flash')
    
    async def compress(
        self,
        messages: List[Message],
        target_tokens: int,
    ) -> List[Message]:
        """Compress messages using sliding window + summarization"""
        self._stats["compressions"] += 1
        
        # Estimate current tokens
        current_tokens = sum(self.estimate_tokens(m.content or "") for m in messages)
        self._stats["original_tokens"] += current_tokens
        
        # If under limit, return as-is
        if current_tokens <= target_tokens:
            return messages
        
        # Separate messages by type
        system_msgs = [m for m in messages if m.role == "system"]
        tool_msgs = [m for m in messages if m.role == "tool"]
        
        # Get conversation turns (user+assistant pairs)
        conversation = [m for m in messages if m.role in ("user", "assistant")]
        
        # Keep recent turns
        recent_count = self.keep_recent_turns * 2  # user + assistant
        recent_turns = conversation[-recent_count:] if len(conversation) > recent_count else conversation
        
        # Middle section to summarize
        middle_start = len(conversation) - recent_count
        if middle_start > 0:
            middle_section = conversation[:middle_start]
            
            # Summarize middle section
            summary = await self._summarize_conversation(middle_section)
            
            # Create summary message
            summary_msg = Message(
                role="system",
                content=f"[Previous conversation summary]\n{summary}"
            )
        else:
            summary_msg = None
        
        # Reconstruct messages
        result = []
        result.extend(system_msgs)
        
        if summary_msg:
            result.append(summary_msg)
        
        result.extend(recent_turns)
        result.extend(tool_msgs)
        
        # Update stats
        final_tokens = sum(self.estimate_tokens(m.content or "") for m in result)
        self._stats["tokens_removed"] += current_tokens - final_tokens
        
        logger.info(f"Compressed context: {current_tokens} → {final_tokens} tokens")
        
        return result
    
    async def _summarize_conversation(self, messages: List[Message]) -> str:
        """Summarize a conversation section"""
        # In production, this would call an LLM
        # For now, use simple truncation
        
        text_parts = []
        for msg in messages:
            text_parts.append(f"{msg.role}: {msg.content[:200]}...")
        
        full_text = "\n".join(text_parts)
        
        # Simple truncation summary
        if len(full_text) > 1000:
            return f"[Conversation summary - truncated]\n{full_text[:1000]}..."
        
        return full_text
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token for English)"""
        if not text:
            return 0
        
        # Simple heuristic: ~4 characters per token
        char_count = len(text)
        
        # Adjust for common patterns
        word_count = len(text.split())
        
        # Average the two estimates
        return int((char_count / 4 + word_count) / 2)


# Global default engine instance
_default_engine: Optional[ContextEngine] = None


def get_context_engine(prada_home: Path, config: Optional[Dict] = None) -> ContextEngine:
    """Get or create default context engine"""
    global _default_engine
    
    if _default_engine is None:
        _default_engine = DefaultContextEngine(prada_home, config)
    
    return _default_engine


def set_context_engine(engine: ContextEngine) -> None:
    """Set custom context engine (for plugins)"""
    global _default_engine
    _default_engine = engine
