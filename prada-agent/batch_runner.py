"""
PRADA Agent - Batch Trajectory Generator

Generates training data by running multiple prompts through the agent.
Outputs ShareGPT-compatible trajectory format.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ToolUsageStats:
    total_calls: int = 0
    by_tool: Dict[str, int] = None
    success_rate: float = 1.0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.by_tool is None:
            self.by_tool = {}


@dataclass
class Trajectory:
    id: str
    model: str
    created_at: str
    prompt: str
    messages: List[Dict[str, Any]]
    tool_usage_stats: ToolUsageStats
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "created_at": self.created_at,
            "prompt": self.prompt,
            "messages": self.messages,
            "tool_usage_stats": asdict(self.tool_usage_stats),
            "metadata": self.metadata or {}
        }


class BatchRunner:
    """Batch trajectory generator for training data."""
    
    def __init__(
        self,
        model: str = "openrouter:nousresearch/hermes-3-llama-3.1-70b",
        toolsets: List[str] = None,
        max_turns: int = 20,
        timeout_seconds: int = 300,
        parallel: int = 4
    ):
        self.model = model
        self.toolsets = toolsets or ["core", "file", "terminal"]
        self.max_turns = max_turns
        self.timeout_seconds = timeout_seconds
        self.parallel = parallel
        self.semaphore = asyncio.Semaphore(parallel)
    
    async def run_prompt(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Trajectory:
        """Run a single prompt and generate trajectory."""
        async with self.semaphore:
            trajectory_id = f"traj_{int(time.time() * 1000)}"
            messages = [
                {"role": "user", "content": prompt}
            ]
            tool_calls_count = 0
            tool_by_tool = {}
            
            # Simulated agent loop (would integrate with AIAgent)
            for turn in range(self.max_turns):
                # In real implementation, this would call AIAgent
                # For now, create placeholder trajectory
                if turn == 0:
                    messages.append({
                        "role": "assistant",
                        "content": f"[Simulated response to: {prompt[:50]}...]",
                        "tool_calls": []
                    })
                    break
            
            stats = ToolUsageStats(
                total_calls=tool_calls_count,
                by_tool=tool_by_tool,
                total_tokens=len(prompt) // 4
            )
            
            return Trajectory(
                id=trajectory_id,
                model=self.model,
                created_at=datetime.utcnow().isoformat() + "Z",
                prompt=prompt,
                messages=messages,
                tool_usage_stats=stats,
                metadata={
                    "toolsets": self.toolsets,
                    "max_turns": self.max_turns,
                    "timeout_seconds": self.timeout_seconds
                }
            )
    
    async def run_batch(
        self,
        input_file: Path,
        output_file: Path
    ) -> int:
        """Run batch generation from JSONL input file."""
        prompts = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    prompts.append(data)
        
        trajectories = []
        tasks = []
        
        for item in prompts:
            prompt = item.get("prompt", "")
            context = item.get("context")
            task = self.run_prompt(prompt, context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error processing prompt {i}: {result}")
            else:
                trajectories.append(result)
        
        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            for traj in trajectories:
                f.write(json.dumps(traj.to_dict()) + "\n")
        
        return len(trajectories)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch trajectory generator")
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL file")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL file")
    parser.add_argument("--parallel", type=int, default=4, help="Parallel concurrency")
    parser.add_argument("--model", type=str, default="openrouter:nousresearch/hermes-3-llama-3.1-70b")
    parser.add_argument("--toolsets", type=str, default="core,file,terminal")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    
    args = parser.parse_args()
    
    runner = BatchRunner(
        model=args.model,
        toolsets=args.toolsets.split(","),
        max_turns=args.max_turns,
        timeout_seconds=args.timeout_seconds,
        parallel=args.parallel
    )
    
    count = asyncio.run(runner.run_batch(args.input, args.output))
    print(f"Generated {count} trajectories to {args.output}")


if __name__ == "__main__":
    main()
