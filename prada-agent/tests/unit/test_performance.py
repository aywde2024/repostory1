"""
Unit tests for performance optimization module
"""

import asyncio
import pytest
from agent.performance import (
    LRUCache, ParallelExecutor, TokenBudgetManager, 
    BatchProcessor, PerformanceMonitor, get_cache, get_executor, get_monitor
)


class TestLRUCache:
    """Test LRU cache functionality"""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic set and get operations"""
        cache = LRUCache(max_size=10)
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = LRUCache(max_size=10)
        
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_eviction(self):
        """Test LRU eviction when max size reached"""
        cache = LRUCache(max_size=3)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")  # Should evict key1
        
        result1 = await cache.get("key1")
        result4 = await cache.get("key4")
        
        assert result1 is None  # Evicted
        assert result4 == "value4"
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics tracking"""
        cache = LRUCache(max_size=5)
        
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2/3
    
    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache deletion"""
        cache = LRUCache(max_size=10)
        
        await cache.set("key1", "value1")
        deleted = await cache.delete("key1")
        result = await cache.get("key1")
        
        assert deleted is True
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clear"""
        cache = LRUCache(max_size=10)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        
        stats = cache.get_stats()
        assert stats["size"] == 0


class TestParallelExecutor:
    """Test parallel execution functionality"""
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test executing multiple tasks in parallel"""
        executor = ParallelExecutor(max_concurrency=3)
        
        async def dummy_task(value: int):
            await asyncio.sleep(0.1)
            return value * 2
        
        tasks = [
            ("task1", dummy_task, {"value": 1}),
            ("task2", dummy_task, {"value": 2}),
            ("task3", dummy_task, {"value": 3}),
        ]
        
        results = await executor.execute_all(tasks)
        
        assert len(results) == 3
        assert results[0][1]["result"] == 2
        assert results[1][1]["result"] == 4
        assert results[2][1]["result"] == 6
    
    @pytest.mark.asyncio
    async def test_parallel_timeout(self):
        """Test task timeout handling"""
        executor = ParallelExecutor(max_concurrency=2, default_timeout=1)
        
        async def slow_task(delay: float):
            await asyncio.sleep(delay)
            return "done"
        
        tasks = [
            ("fast", slow_task, {"delay": 0.1}),
            ("slow", slow_task, {"delay": 2.0}),  # Will timeout
        ]
        
        results = await executor.execute_all(tasks)
        
        assert results[0][1]["success"] is True
        assert results[1][1]["success"] is False
        assert "timed out" in results[1][1]["error"]
    
    @pytest.mark.asyncio
    async def test_parallel_error_handling(self):
        """Test error handling in parallel execution"""
        executor = ParallelExecutor(max_concurrency=2)
        
        async def failing_task(should_fail: bool):
            if should_fail:
                raise ValueError("Intentional failure")
            return "success"
        
        tasks = [
            ("success", failing_task, {"should_fail": False}),
            ("failure", failing_task, {"should_fail": True}),
        ]
        
        results = await executor.execute_all(tasks)
        
        assert results[0][1]["success"] is True
        assert results[1][1]["success"] is False
        assert "Intentional failure" in results[1][1]["error"]


class TestTokenBudgetManager:
    """Test token budget management"""
    
    def test_budget_calculation(self):
        """Test token budget calculation"""
        manager = TokenBudgetManager(
            max_tokens=100000,
            system_reserve=10000,
            tools_reserve=5000,
            safety_margin=0.1,
        )
        
        # With 50000 tokens used
        budget = manager.calculate_budget([50000])
        
        assert budget["total_max"] == 100000
        assert budget["system_reserved"] == 10000
        assert budget["tools_reserved"] == 5000
        assert budget["used"] == 50000
        assert budget["remaining"] > 0
    
    def test_should_compress(self):
        """Test compression threshold detection"""
        manager = TokenBudgetManager(
            max_tokens=100000,
            system_reserve=10000,
            tools_reserve=5000,
            safety_margin=0.0,  # No safety margin for predictable test
        )
        
        # Available = 100000 - 10000 - 5000 = 85000
        # At 80% threshold = 68000 tokens
        
        # Under threshold
        assert manager.should_compress([50000], threshold=0.8) is False
        
        # Over threshold
        assert manager.should_compress([70000], threshold=0.8) is True


class TestBatchProcessor:
    """Test batch processing functionality"""
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test processing items in batches"""
        processor = BatchProcessor(batch_size=3, delay_between_batches=0.01)
        
        async def process_batch(items):
            return [item * 2 for item in items]
        
        items = [1, 2, 3, 4, 5, 6, 7]
        results = await processor.process(items, process_batch)
        
        assert results == [2, 4, 6, 8, 10, 12, 14]
    
    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        """Test processing empty list"""
        processor = BatchProcessor(batch_size=5)
        
        async def process_batch(items):
            return [item * 2 for item in items]
        
        results = await processor.process([], process_batch)
        assert results == []


class TestPerformanceMonitor:
    """Test performance monitoring"""
    
    def test_timer_start_stop(self):
        """Test starting and stopping timers"""
        monitor = PerformanceMonitor()
        
        monitor.start_timer("test_op")
        asyncio.run(asyncio.sleep(0.1))
        duration = monitor.stop_timer("test_op")
        
        assert duration is not None
        assert duration >= 0.1
    
    def test_stats_collection(self):
        """Test statistics collection"""
        monitor = PerformanceMonitor()
        
        # Record multiple measurements
        for i in range(3):
            monitor.start_timer("op1")
            asyncio.run(asyncio.sleep(0.05))
            monitor.stop_timer("op1")
        
        stats = monitor.get_stats("op1")
        
        assert stats["count"] == 3
        assert stats["min"] >= 0.05
        assert stats["avg"] >= 0.05
    
    def test_reset(self):
        """Test resetting metrics"""
        monitor = PerformanceMonitor()
        
        monitor.start_timer("test")
        monitor.stop_timer("test")
        monitor.reset()
        
        stats = monitor.get_all_stats()
        assert len(stats) == 0


class TestGlobalInstances:
    """Test global singleton instances"""
    
    def test_get_cache_singleton(self):
        """Test cache singleton behavior"""
        cache1 = get_cache(max_size=100)
        cache2 = get_cache(max_size=200)  # Should return same instance
        
        assert cache1 is cache2
    
    def test_get_executor_singleton(self):
        """Test executor singleton behavior"""
        executor1 = get_executor(max_concurrency=5)
        executor2 = get_executor(max_concurrency=10)  # Should return same instance
        
        assert executor1 is executor2
    
    def test_get_monitor_singleton(self):
        """Test monitor singleton behavior"""
        monitor1 = get_monitor()
        monitor2 = get_monitor()
        
        assert monitor1 is monitor2
