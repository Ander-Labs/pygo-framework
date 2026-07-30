"""PyGo Background Job System (v0.31.0).

Provides job queue, scheduler, and retry mechanisms.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRIED = "retried"


@dataclass
class Job:
    """Represents a background job."""
    id: str
    name: str
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    retries: int = 3
    retry_delay: float = 1.0
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tenant: Optional[str] = None


class JobQueue:
    """In-memory job queue."""
    
    def __init__(self, max_workers: int = 4):
        self.jobs: Dict[str, Job] = {}
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def enqueue(self, name: str, func: Callable, *args, retries: int = 3,
                retry_delay: float = 1.0, tenant: Optional[str] = None, **kwargs) -> str:
        """Enqueue a job for execution."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            retries=retries,
            retry_delay=retry_delay,
            tenant=tenant
        )
        
        with self._lock:
            self.jobs[job_id] = job
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        with self._lock:
            return self.jobs.get(job_id)
    
    def get_jobs(self, status: Optional[JobStatus] = None) -> List[Job]:
        """Get all jobs, optionally filtered by status."""
        with self._lock:
            if status is None:
                return list(self.jobs.values())
            return [j for j in self.jobs.values() if j.status == status]
    
    def start(self):
        """Start processing jobs."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop processing jobs."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _process_loop(self):
        """Main processing loop."""
        while self._running:
            with self._lock:
                pending = [j for j in self.jobs.values() if j.status == JobStatus.PENDING]
            
            for job in pending:
                self._process_job(job)
            
            time.sleep(0.1)  # Small delay to prevent busy loop
    
    def _process_job(self, job: Job):
        """Process a single job."""
        job.status = JobStatus.RUNNING
        job.started_at = time.time()
        
        def execute():
            try:
                result = job.func(*job.args, **job.kwargs)
                job.result = result
                job.status = JobStatus.COMPLETED
            except Exception as e:
                job.error = str(e)
                if job.retries > 0:
                    job.retries -= 1
                    job.status = JobStatus.RETRIED
                    time.sleep(job.retry_delay)
                else:
                    job.status = JobStatus.FAILED
            finally:
                job.completed_at = time.time()
        
        # Submit to thread pool
        future = self._executor.submit(execute)
    
    def submit(self, name: str, func: Callable, *args, **kwargs) -> str:
        """Submit a job for immediate execution (deprecated, use enqueue)."""
        return self.enqueue(name, func, *args, **kwargs)


# Global job queue
_default_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get the default job queue."""
    global _default_queue
    if _default_queue is None:
        _default_queue = JobQueue()
    return _default_queue


def schedule(name: str, func: Callable, *args, retries: int = 3, **kwargs) -> str:
    """Schedule a job for execution."""
    return get_job_queue().enqueue(name, func, *args, retries=retries, **kwargs)


def get_job(job_id: str) -> Optional[Job]:
    """Get a job by ID."""
    return get_job_queue().get_job(job_id)


def list_jobs(status: Optional[JobStatus] = None) -> List[Job]:
    """List jobs."""
    return get_job_queue().get_jobs(status)


# Decorator for defining jobs
def job(name: str, retries: int = 3, retry_delay: float = 1.0):
    """Decorator to define a background job."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            queue = get_job_queue()
            return queue.enqueue(name, func, *args, retries=retries,
                                 retry_delay=retry_delay, **kwargs)
        return wrapper
    return decorator