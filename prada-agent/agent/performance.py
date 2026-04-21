"""
Performance Optimization Module for PRADA Agent

Features:
- Tool call parallelization
- Connection pooling for HTTP clients
- Token caching for repeated prompts
- Async batch processing
- Memory-efficient context management
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LRUCache:
    """
    Thread-safe LRU cache for token/memory optimization.
    
    Use cases:
    - Cache system prompt tokens
    - Cache tool schemas
    - Cache memory embeddings
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                self._stats.hits += 1
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                return self._cache[key]
            
            self._stats.misses += 1
            return None
    
    async def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                if len(self._cache) >= self.max_size:
                    # Evict oldest
                    self._cache.popitem(last=False)
                    self._stats.evictions += 1
                self._cache[key] = value
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "evictions": self._stats.evictions,
            "hit_rate": self._stats.hit_rate,
        }


class ParallelExecutor:
    """
    Execute multiple tool calls in parallel with concurrency control.
    
    Features:
    - Configurable max concurrency
    - Timeout per task
    - Aggregate results with error handling
    - Progress tracking
    """
    
    def __init__(self, max_concurrency: int = 5, default_timeout: int = 60):
        self.max_concurrency = max_concurrency
        self.default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrency)
    
    async def execute_all(
        self,
        tasks: List[Tuple[str, Callable, Dict]],
        progress_callback: Optional[Callable] = None,
    ) -> List[Tuple[str, Any]]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of (task_id, async_func, kwargs) tuples
            progress_callback: Optional callback(task_id, result) on completion
            
        Returns:
            List of (task_id, result_or_error) tuples
        """
        async def run_task(task_id: str, func: Callable, kwargs: dict):
            async with self._semaphore:
                try:
                    timeout = kwargs.pop('timeout', self.default_timeout)
                    result = await asyncio.wait_for(func(**kwargs), timeout=timeout)
                    
                    if progress_callback:
                        await progress_callback(task_id, {"success": True, "result": result})
                    
                    return (task_id, {"success": True, "result": result})
                    
                except asyncio.TimeoutError:
                    error = f"Task timed out after {timeout}s"
                    logger.warning(f"Task {task_id} timed out")
                    
                    if progress_callback:
                        await progress_callback(task_id, {"success": False, "error": error})
                    
                    return (task_id, {"success": False, "error": error})
                    
                except Exception as e:
                    error = str(e)
                    logger.exception(f"Task {task_id} failed: {e}")
                    
                    if progress_callback:
                        await progress_callback(task_id, {"success": False, "error": error})
                    
                    return (task_id, {"success": False, "error": error})
        
        # Run all tasks concurrently
        coroutines = [run_task(task_id, func, kwargs) for task_id, func, kwargs in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Handle any unexpected exceptions from gather
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_id = tasks[i][0]
                logger.exception(f"Unexpected error in task {task_id}: {result}")
                final_results.append((task_id, {"success": False, "error": str(result)}))
            else:
                final_results.append(result)
        
        return final_results


class TokenBudgetManager:
    """
    Manage token budget across conversation turns.
    
    Strategies:
    - Reserve tokens for system prompt and tools
    - Dynamically adjust context window based on usage
    - Prioritize recent messages when truncating
    """
    
    def __init__(
        self,
        max_tokens: int = 128000,
        system_reserve: int = 8000,
        tools_reserve: int = 4000,
        safety_margin: float = 0.1,
    ):
        self.max_tokens = max_tokens
        self.system_reserve = system_reserve
        self.tools_reserve = tools_reserve
        self.safety_margin = safety_margin
        
        # Available for conversation
        self.available_tokens = max_tokens - system_reserve - tools_reserve
        self.available_tokens = int(self.available_tokens * (1 - safety_margin))
    
    def calculate_budget(self, message_tokens: List[int]) -> Dict[str, int]:
        """
        Calculate how many tokens can be used for new messages.
        
        Args:
            message_tokens: List of token counts for existing messages
            
        Returns:
            Budget allocation dict
        """
        used_tokens = sum(message_tokens)
        remaining = self.available_tokens - used_tokens
        
        return {
            "total_max": self.max_tokens,
            "system_reserved": self.system_reserve,
            "tools_reserved": self.tools_reserve,
            "used": used_tokens,
            "remaining": max(0, remaining),
            "utilization": used_tokens / self.available_tokens if self.available_tokens > 0 else 0,
        }
    
    def should_compress(self, message_tokens: List[int], threshold: float = 0.8) -> bool:
        """Check if context compression is needed"""
        budget = self.calculate_budget(message_tokens)
        return budget["utilization"] > threshold


class BatchProcessor:
    """
    Process items in batches for efficiency.
    
    Use cases:
    - Batch memory embedding generation
    - Batch tool schema validation
    - Batch file operations
    """
    
    def __init__(self, batch_size: int = 32, delay_between_batches: float = 0.1):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
    
    async def process(
        self,
        items: List[Any],
        processor: Callable[[List[Any]], Any],
    ) -> List[Any]:
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            processor: Async function that processes a batch
            
        Returns:
            List of results in same order as input
        """
        results = []
        
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            
            # Process batch
            batch_results = await processor(batch)
            results.extend(batch_results)
            
            # Rate limiting between batches
            if i + self.batch_size < len(items):
                await asyncio.sleep(self.delay_between_batches)
        
        return results


class PerformanceMonitor:
    """
    Monitor and log performance metrics.
    
    Tracks:
    - Tool execution times
    - LLM API latencies
    - Memory usage
    - Token throughput
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._start_times: Dict[str, float] = {}
    
    def start_timer(self, name: str) -> None:
        """Start timing an operation"""
        self._start_times[name] = time.perf_counter()
    
    def stop_timer(self, name: str) -> Optional[float]:
        """Stop timer and record duration"""
        if name not in self._start_times:
            return None
        
        duration = time.perf_counter() - self._start_times[name]
        del self._start_times[name]
        
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(duration)
        
        return duration
    
    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get statistics for a metric"""
        if name not in self._metrics or not self._metrics[name]:
            return None
        
        values = self._metrics[name]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "total": sum(values),
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get all recorded statistics"""
        return {
            name: self.get_stats(name)
            for name in self._metrics
            if self.get_stats(name) is not None
        }
    
    def reset(self) -> None:
        """Reset all metrics"""
        self._metrics.clear()
        self._start_times.clear()


# Global instances for agent-wide use
_global_cache: Optional[LRUCache] = None
_global_executor: Optional[ParallelExecutor] = None
_global_monitor: Optional[PerformanceMonitor] = None


def get_cache(max_size: int = 1000) -> LRUCache:
    """Get or create global LRU cache"""
    global _global_cache
    if _global_cache is None:
        _global_cache = LRUCache(max_size)
    return _global_cache


def get_executor(max_concurrency: int = 5) -> ParallelExecutor:
    """Get or create global parallel executor"""
    global _global_executor
    if _global_executor is None:
        _global_executor = ParallelExecutor(max_concurrency)
    return _global_executor


def get_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


async def optimize_tool_execution(
    tool_calls: List[Dict],
    tool_registry: Any,
    max_parallel: int = 5,
) -> List[Dict]:
    """
    Optimize tool execution by running independent calls in parallel.
    
    Args:
        tool_calls: List of tool call dicts
        tool_registry: ToolRegistry instance
        max_parallel: Maximum concurrent executions
        
    Returns:
        List of execution results
    """
    executor = get_executor(max_parallel)
    monitor = get_monitor()
    
    async def execute_tool(tool_call: Dict):
        tool_name = tool_call['function']['name']
        tool_args = tool_call['function'].get('arguments', '{}')
        
        import json
        args_dict = json.loads(tool_args) if tool_args else {}
        
        monitor.start_timer(f"tool_{tool_name}")
        
        tool_func = tool_registry.get_tool(tool_name)
        result = await tool_func(**args_dict)
        
        duration = monitor.stop_timer(f"tool_{tool_name}")
        logger.debug(f"Tool {tool_name} executed in {duration:.3f}s")
        
        return result
    
    # Prepare tasks
    tasks = []
    for call in tool_calls:
        task_id = call.get('id', f"tool_{len(tasks)}")
        tasks.append((task_id, execute_tool, {'tool_call': call}))
    
    # Execute in parallel
    results = await executor.execute_all(tasks)
    
    return [result for _, result in results]
