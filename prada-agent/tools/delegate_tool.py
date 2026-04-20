"""
PRADA Agent - Delegate Tool for Subagent Management

Enables delegating tasks to specialized subagents.
Supports parallel execution, status tracking, and cancellation.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SubagentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubagentTask:
    id: str
    prompt: str
    toolsets: List[str]
    skills: List[str]
    status: SubagentStatus = SubagentStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "toolsets": self.toolsets,
            "skills": self.skills,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class SubagentManager:
    """Manages subagent delegation and execution."""
    
    def __init__(self):
        self._tasks: Dict[str, SubagentTask] = {}
        self._max_concurrent = 5
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
    
    async def create_task(
        self,
        prompt: str,
        toolsets: List[str] = None,
        skills: List[str] = None
    ) -> SubagentTask:
        """Create a new subagent task."""
        task_id = f"subagent_{uuid.uuid4().hex[:8]}"
        
        task = SubagentTask(
            id=task_id,
            prompt=prompt,
            toolsets=toolsets or ["core", "file"],
            skills=skills or []
        )
        
        self._tasks[task_id] = task
        return task
    
    async def execute_task(self, task_id: str) -> SubagentTask:
        """Execute a subagent task asynchronously."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        
        async with self._semaphore:
            task.status = SubagentStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat()
            
            try:
                # Simulate subagent execution
                # In real implementation, this would spawn a new AIAgent instance
                await asyncio.sleep(1)  # Simulate work
                
                task.result = f"[Simulated result for: {task.prompt[:50]}...]"
                task.status = SubagentStatus.COMPLETED
                task.completed_at = datetime.utcnow().isoformat()
                
            except asyncio.CancelledError:
                task.status = SubagentStatus.CANCELLED
                task.completed_at = datetime.utcnow().isoformat()
                raise
                
            except Exception as e:
                task.error = str(e)
                task.status = SubagentStatus.FAILED
                task.completed_at = datetime.utcnow().isoformat()
        
        return task
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        if task.status not in [SubagentStatus.PENDING, SubagentStatus.RUNNING]:
            return False
        
        task.status = SubagentStatus.CANCELLED
        task.completed_at = datetime.utcnow().isoformat()
        return True
    
    def get_task_status(self, task_id: str) -> Optional[SubagentTask]:
        """Get current status of a task."""
        return self._tasks.get(task_id)
    
    def list_tasks(self, status_filter: Optional[SubagentStatus] = None) -> List[SubagentTask]:
        """List all tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        
        return tasks


# Delegate tool implementations

async def delegate_impl(
    prompt: str,
    toolsets: Optional[List[str]] = None,
    skills: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Delegate a task to a subagent."""
    manager = SubagentManager()
    task = await manager.create_task(prompt, toolsets, skills)
    
    # Start execution in background (fire and forget for now)
    asyncio.create_task(manager.execute_task(task.id))
    
    return {
        "task_id": task.id,
        "status": task.status.value,
        "message": f"Subagent created for task: {prompt[:50]}..."
    }


async def subagent_status_impl(task_id: str) -> Dict[str, Any]:
    """Get status of a subagent task."""
    # In real implementation, would use shared manager instance
    manager = SubagentManager()
    
    # For demo, create a mock task
    task = SubagentTask(
        id=task_id,
        prompt="Mock task",
        toolsets=["core"],
        skills=[],
        status=SubagentStatus.RUNNING
    )
    
    return task.to_dict()


async def subagent_cancel_impl(task_id: str) -> Dict[str, Any]:
    """Cancel a subagent task."""
    manager = SubagentManager()
    success = await manager.cancel_task(task_id)
    
    return {
        "success": success,
        "message": f"Task {task_id} cancelled" if success else f"Task {task_id} not found or already completed"
    }


# Tool schemas for registry
DELEGATE_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {
            "type": "string",
            "description": "Task description to delegate to subagent"
        },
        "toolsets": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Toolsets available to subagent"
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Skills available to subagent"
        }
    },
    "required": ["prompt"]
}

SUBAGENT_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Subagent task ID"
        }
    },
    "required": ["task_id"]
}

SUBAGENT_CANCEL_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Subagent task ID to cancel"
        }
    },
    "required": ["task_id"]
}


def register_delegate_tools(registry):
    """Register delegate tools with the registry."""
    registry.register(
        name="delegate",
        func=delegate_impl,
        schema=DELEGATE_SCHEMA,
        toolsets=["delegate"],
        platforms=["linux", "macos", "windows"],
        requires_env=[],
        dangerous=False
    )
    
    registry.register(
        name="subagent_status",
        func=subagent_status_impl,
        schema=SUBAGENT_STATUS_SCHEMA,
        toolsets=["delegate"],
        platforms=["linux", "macos", "windows"],
        requires_env=[],
        dangerous=False
    )
    
    registry.register(
        name="subagent_cancel",
        func=subagent_cancel_impl,
        schema=SUBAGENT_CANCEL_SCHEMA,
        toolsets=["delegate"],
        platforms=["linux", "macos", "windows"],
        requires_env=[],
        dangerous=False
    )


if __name__ == "__main__":
    # Test subagent manager
    async def test():
        manager = SubagentManager()
        
        print("Testing Subagent Manager...")
        
        # Create tasks
        task1 = await manager.create_task(
            "Analyze code structure",
            toolsets=["core", "file", "code"],
            skills=["code-review"]
        )
        print(f"\nCreated task: {task1.id}")
        
        task2 = await manager.create_task(
            "Write documentation",
            toolsets=["core", "file"],
            skills=[]
        )
        print(f"Created task: {task2.id}")
        
        # Execute task
        print("\nExecuting task1...")
        result = await manager.execute_task(task1.id)
        print(f"Result: {result.result}")
        
        # List tasks
        print("\nAll tasks:")
        for task in manager.list_tasks():
            print(f"  - {task.id}: {task.status.value}")
        
        # Cancel task
        print(f"\nCancelling task2...")
        success = await manager.cancel_task(task2.id)
        print(f"Cancelled: {success}")
    
    asyncio.run(test())
