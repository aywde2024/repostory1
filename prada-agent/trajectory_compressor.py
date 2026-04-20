"""
PRADA Agent - Trajectory Compressor

Compresses long trajectories to target token budget for training data preparation.
Supports lossy summary strategy while preserving key information.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class CompressionStrategy(Enum):
    LOSSY_SUMMARY = "lossy-summary"
    KEEP_KEY_TOOLS = "keep-key-tools"
    AGGRESSIVE = "aggressive"


@dataclass
class CompressedTrajectory:
    id: str
    model: str
    created_at: str
    prompt: str
    messages: List[Dict[str, Any]]
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy: str
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "created_at": self.created_at,
            "prompt": self.prompt,
            "messages": self.messages,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": self.compression_ratio,
            "strategy": self.strategy
        }


class TrajectoryCompressor:
    """Compress trajectories to target token budget."""
    
    def __init__(
        self,
        target_tokens: int = 4096,
        strategy: CompressionStrategy = CompressionStrategy.LOSSY_SUMMARY
    ):
        self.target_tokens = target_tokens
        self.strategy = strategy
        # Approximate tokens per character (1 token ≈ 4 chars for English)
        self.chars_per_token = 4
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return len(text) // self.chars_per_token
    
    def summarize_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        tool_calls: List[Dict] = None
    ) -> str:
        """Summarize a single turn (lossy compression)."""
        summary_parts = []
        
        # Keep user intent concise
        user_summary = user_msg[:200] + "..." if len(user_msg) > 200 else user_msg
        summary_parts.append(f"User: {user_summary}")
        
        # Summarize assistant response
        if tool_calls:
            tool_names = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls]
            summary_parts.append(f"Assistant used tools: {', '.join(tool_names)}")
        else:
            asst_summary = assistant_msg[:300] + "..." if len(assistant_msg) > 300 else assistant_msg
            summary_parts.append(f"Assistant: {asst_summary}")
        
        return "\n".join(summary_parts)
    
    def compress_message(
        self,
        message: Dict[str, Any],
        preserve_tool_calls: bool = True
    ) -> Dict[str, Any]:
        """Compress a single message."""
        role = message.get("role", "unknown")
        content = message.get("content", "")
        
        if role == "user":
            # Preserve user messages mostly intact (protected head)
            return message.copy()
        
        elif role == "assistant":
            tool_calls = message.get("tool_calls", [])
            
            if preserve_tool_calls and tool_calls:
                # Keep tool call structure but simplify content
                compressed = {
                    "role": "assistant",
                    "content": "[Tool execution]",
                    "tool_calls": tool_calls
                }
                return compressed
            else:
                # Summarize content
                if len(content) > 500:
                    compressed_content = content[:500] + "...[summarized]"
                else:
                    compressed_content = content
                
                return {
                    "role": "assistant",
                    "content": compressed_content
                }
        
        elif role == "tool":
            # Compress tool outputs aggressively
            tool_output = content or ""
            if len(tool_output) > 300:
                # Keep first and last part
                compressed = tool_output[:150] + "\n...[truncated]...\n" + tool_output[-150:]
            else:
                compressed = tool_output
            
            return {
                "role": "tool",
                "content": compressed,
                "tool_call_id": message.get("tool_call_id", "")
            }
        
        return message.copy()
    
    def compress_trajectory(
        self,
        trajectory: Dict[str, Any]
    ) -> CompressedTrajectory:
        """Compress a full trajectory to target tokens."""
        messages = trajectory.get("messages", [])
        original_tokens = sum(
            self.estimate_tokens(msg.get("content", ""))
            for msg in messages
        )
        
        # Strategy 1: Keep protected head (system + first user message)
        # Strategy 2: Summarize middle turns
        # Strategy 3: Keep final response intact
        
        compressed_messages = []
        
        if len(messages) <= 2:
            # Too short to compress meaningfully
            compressed_messages = messages.copy()
        else:
            # Keep first message (system/user)
            compressed_messages.append(messages[0].copy())
            
            # Keep second message (first assistant response) mostly intact
            if len(messages) > 1:
                compressed_messages.append(self.compress_message(messages[1]))
            
            # Summarize middle turns
            middle_start = 2
            middle_end = len(messages) - 2 if len(messages) > 4 else 2
            
            if middle_end > middle_start:
                middle_turns = []
                for i in range(middle_start, min(middle_end, len(messages))):
                    msg = messages[i]
                    if msg.get("role") == "user":
                        # Will be paired with next assistant message
                        continue
                    elif msg.get("role") == "assistant":
                        prev_user = messages[i-1] if i > 0 and messages[i-1].get("role") == "user" else ""
                        summary = self.summarize_turn(
                            prev_user.get("content", "") if isinstance(prev_user, dict) else "",
                            msg.get("content", ""),
                            msg.get("tool_calls", [])
                        )
                        middle_turns.append({
                            "role": "assistant",
                            "content": f"[Turn {i} summarized]\n{summary}"
                        })
                
                if middle_turns:
                    compressed_messages.append({
                        "role": "assistant",
                        "content": f"[{len(middle_turns)} middle turns summarized]"
                    })
            
            # Keep last 2 messages intact (final exchange)
            for i in range(max(middle_end, 2), len(messages)):
                compressed_messages.append(self.compress_message(messages[i]))
        
        # Calculate compressed tokens
        compressed_tokens = sum(
            self.estimate_tokens(msg.get("content", ""))
            for msg in compressed_messages
        )
        
        compression_ratio = original_tokens / max(compressed_tokens, 1)
        
        return CompressedTrajectory(
            id=trajectory.get("id", "unknown"),
            model=trajectory.get("model", "unknown"),
            created_at=trajectory.get("created_at", ""),
            prompt=trajectory.get("prompt", ""),
            messages=compressed_messages,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            strategy=self.strategy.value
        )
    
    def compress_batch(
        self,
        input_file: Path,
        output_file: Path
    ) -> tuple[int, float]:
        """Compress batch of trajectories from JSONL file."""
        trajectories = []
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    trajectories.append(json.loads(line))
        
        compressed_results = []
        total_original = 0
        total_compressed = 0
        
        for traj in trajectories:
            result = self.compress_trajectory(traj)
            compressed_results.append(result.to_dict())
            total_original += result.original_tokens
            total_compressed += result.compressed_tokens
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in compressed_results:
                f.write(json.dumps(result) + "\n")
        
        avg_ratio = total_original / max(total_compressed, 1)
        return len(compressed_results), avg_ratio


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Trajectory compressor")
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL file")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL file")
    parser.add_argument("--target-tokens", type=int, default=4096, help="Target token budget")
    parser.add_argument(
        "--strategy",
        type=str,
        default="lossy-summary",
        choices=["lossy-summary", "keep-key-tools", "aggressive"]
    )
    
    args = parser.parse_args()
    
    strategy_map = {
        "lossy-summary": CompressionStrategy.LOSSY_SUMMARY,
        "keep-key-tools": CompressionStrategy.KEEP_KEY_TOOLS,
        "aggressive": CompressionStrategy.AGGRESSIVE
    }
    
    compressor = TrajectoryCompressor(
        target_tokens=args.target_tokens,
        strategy=strategy_map[args.strategy]
    )
    
    count, ratio = compressor.compress_batch(args.input, args.output)
    print(f"Compressed {count} trajectories")
    print(f"Average compression ratio: {ratio:.2f}x")
    print(f"Output written to {args.output}")


if __name__ == "__main__":
    main()
