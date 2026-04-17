"""
PRADA Agent - Cron Scheduler System
Handles scheduled jobs and automated tasks
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from croniter import croniter


@dataclass
class CronJob:
    """Scheduled job definition"""
    id: str
    name: str
    schedule_type: str  # cron, interval, once
    expression: str  # cron expression or interval seconds
    timezone: str
    prompt: str
    toolsets: List[str]
    skills: List[str]
    delivery: dict
    timeout_minutes: int
    retry: dict
    enabled: bool
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    status: str = "pending"  # pending, running, success, failed, disabled


class JobScheduler:
    """Cron job scheduler"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.config_dir / "jobs.json"
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._execute_callback: Optional[Callable[[CronJob], None]] = None
        
        self._load_jobs()
    
    def _load_jobs(self):
        """Load jobs from disk"""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file) as f:
                    data = json.load(f)
                    for jid, jdata in data.get("jobs", {}).items():
                        self.jobs[jid] = CronJob(**jdata)
            except Exception as e:
                print(f"Error loading jobs: {e}")
        
        # Calculate next run times
        for job in self.jobs.values():
            if job.enabled and job.status != "disabled":
                job.next_run = self._calculate_next_run(job)
        
        self._save_jobs()
    
    def _save_jobs(self):
        """Save jobs to disk"""
        try:
            with open(self.jobs_file, 'w') as f:
                data = {
                    "jobs": {jid: asdict(job) for jid, job in self.jobs.items()}
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving jobs: {e}")
    
    def _calculate_next_run(self, job: CronJob) -> Optional[float]:
        """Calculate next run time for a job"""
        now = datetime.now()
        
        if job.schedule_type == "once":
            # One-time job
            try:
                run_time = datetime.fromisoformat(job.expression)
                if run_time > now:
                    return run_time.timestamp()
            except Exception:
                pass
            return None
        
        elif job.schedule_type == "interval":
            # Interval in seconds
            try:
                interval = int(job.expression)
                if job.last_run:
                    return job.last_run + interval
                else:
                    return now.timestamp()
            except Exception:
                pass
            return None
        
        elif job.schedule_type == "cron":
            # Cron expression
            try:
                tz = job.timezone or "UTC"
                cron = croniter(job.expression, now)
                return cron.get_next(float).timestamp()
            except Exception as e:
                print(f"Cron parse error: {e}")
                return None
        
        return None
    
    def add_job(self, job: CronJob) -> str:
        """Add a new job"""
        job.next_run = self._calculate_next_run(job)
        self.jobs[job.id] = job
        self._save_jobs()
        return job.id
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job"""
        if job_id in self.jobs:
            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False
    
    def enable_job(self, job_id: str) -> bool:
        """Enable a job"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            self.jobs[job_id].status = "pending"
            self.jobs[job_id].next_run = self._calculate_next_run(self.jobs[job_id])
            self._save_jobs()
            return True
        return False
    
    def disable_job(self, job_id: str) -> bool:
        """Disable a job"""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            self.jobs[job_id].status = "disabled"
            self._save_jobs()
            return True
        return False
    
    def list_jobs(self) -> List[CronJob]:
        """List all jobs"""
        return list(self.jobs.values())
    
    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get job by ID"""
        return self.jobs.get(job_id)
    
    async def start(self, execute_callback: Callable[[CronJob], None]):
        """Start the scheduler"""
        self.running = True
        self._execute_callback = execute_callback
        
        while self.running:
            try:
                await self._check_and_run_jobs()
            except Exception as e:
                print(f"Scheduler error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
    
    async def _check_and_run_jobs(self):
        """Check for due jobs and execute them"""
        now = datetime.now().timestamp()
        
        for job in self.jobs.values():
            if not job.enabled:
                continue
            
            if job.status == "running":
                continue
            
            if job.next_run and now >= job.next_run:
                await self._run_job(job)
    
    async def _run_job(self, job: CronJob):
        """Execute a job"""
        job.status = "running"
        job.last_run = datetime.now().timestamp()
        self._save_jobs()
        
        print(f"Running job: {job.name} ({job.id})")
        
        try:
            if self._execute_callback:
                await self._execute_callback(job)
            
            job.status = "success"
        except Exception as e:
            print(f"Job {job.id} failed: {e}")
            job.status = "failed"
            
            # Handle retries
            retry_config = job.retry or {}
            max_attempts = retry_config.get("max_attempts", 3)
            # In production, track attempt count and retry
            
        finally:
            # Calculate next run
            job.next_run = self._calculate_next_run(job)
            self._save_jobs()


class JobRunner:
    """Execute scheduled jobs"""
    
    def __init__(self, config: dict):
        self.config = config
        self.scheduler: Optional[JobScheduler] = None
    
    def initialize(self, prada_home: Path):
        """Initialize job runner"""
        cron_dir = prada_home / "cron"
        self.scheduler = JobScheduler(cron_dir)
    
    async def execute_job(self, job: CronJob):
        """Execute a single job"""
        # This would integrate with the main AIAgent
        # For now, just log the job execution
        print(f"Executing job '{job.name}': {job.prompt}")
        
        # In production:
        # 1. Create AIAgent instance with job prompt
        # 2. Load specified toolsets and skills
        # 3. Execute agent
        # 4. Capture output
        # 5. Deliver results via specified channel
        
        return {"status": "completed", "output": ""}
