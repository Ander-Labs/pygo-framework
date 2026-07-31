"""PyGo Background Jobs System (v0.42.0).

Provides Redis-backed background job processing with:
- Retries with exponential backoff
- Dead letter queue
- Job status tracking
- Scheduler
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field, asdict


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DEAD = "dead"


@dataclass
class Job:
    id: str
    name: str
    queue: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: int = 1
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        d['scheduled_at'] = self.scheduled_at.isoformat() if self.scheduled_at else None
        d['started_at'] = self.started_at.isoformat() if self.started_at else None
        d['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        d['created_at'] = self.created_at.isoformat()
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(
            id=data['id'], name=data['name'], queue=data['queue'],
            payload=data['payload'], status=JobStatus(data['status']),
            result=data.get('result'), error=data.get('error'),
            retry_count=data.get('retry_count', 0), max_retries=data.get('max_retries', 3),
            retry_delay=data.get('retry_delay', 1),
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            created_at=datetime.fromisoformat(data['created_at']),
            metadata=data.get('metadata', {})
        )


class JobQueue:
    def __init__(self, redis_client=None, default_queue: str = "default"):
        self.redis = redis_client
        self.default_queue = default_queue
        self._jobs: Dict[str, Job] = {}
        self._queue: Dict[str, List[str]] = {}
    
    def enqueue(self, name: str, payload: Dict[str, Any], queue: Optional[str] = None,
                max_retries: int = 3, retry_delay: int = 1,
                scheduled_at: Optional[datetime] = None) -> str:
        job = Job(
            id=str(uuid.uuid4()), name=name,
            queue=queue or self.default_queue, payload=payload,
            max_retries=max_retries, retry_delay=retry_delay,
            scheduled_at=scheduled_at
        )
        if self.redis:
            queue_key = f"jobs:queue:{job.queue}"
            job_key = f"jobs:job:{job.id}"
            self.redis.set(job_key, json.dumps(job.to_dict()), ex=86400)
            if job.scheduled_at and job.scheduled_at > datetime.utcnow():
                score = job.scheduled_at.timestamp()
                self.redis.zadd("jobs:delayed", {job.id: score})
            else:
                self.redis.lpush(queue_key, job.id)
        else:
            self._jobs[job.id] = job
            if job.queue not in self._queue:
                self._queue[job.queue] = []
            self._queue[job.queue].append(job.id)
        return job.id
    
    def dequeue(self, queue: Optional[str] = None) -> Optional[Job]:
        queue_name = queue or self.default_queue
        if self.redis:
            queue_key = f"jobs:queue:{queue_name}"
            job_id = self.redis.rpop(queue_key)
            if job_id:
                job_data = self.redis.get(f"jobs:job:{job_id}")
                if job_data:
                    return Job.from_dict(json.loads(job_data))
        else:
            if queue_name in self._queue and self._queue[queue_name]:
                job_id = self._queue[queue_name].pop(0)
                return self._jobs.pop(job_id, None)
        return None
    
    def requeue(self, job: Job, delay: Optional[int] = None) -> None:
        if delay:
            job.scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
        if self.redis:
            queue_key = f"jobs:queue:{job.queue}"
            job_key = f"jobs:job:{job.id}"
            self.redis.set(job_key, json.dumps(job.to_dict()), ex=86400)
            self.redis.lpush(queue_key, job.id)
        else:
            self._jobs[job.id] = job
            if job.queue not in self._queue:
                self._queue[job.queue] = []
            self._queue[job.queue].append(job.id)
    
    def fail(self, job: Job, error: str) -> None:
        job.retry_count += 1
        if job.retry_count <= job.max_retries:
            job.status = JobStatus.RETRY
            job.error = error
            delay = job.retry_delay * (2 ** (job.retry_count - 1))
            self.requeue(job, delay=delay)
        else:
            job.status = JobStatus.DEAD
            job.error = error
            if self.redis:
                self.redis.lpush("jobs:dlq", json.dumps(job.to_dict()))
    
    def complete(self, job: Job, result: Optional[Dict[str, Any]] = None) -> None:
        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = datetime.utcnow()
        if self.redis:
            job_key = f"jobs:job:{job.id}"
            self.redis.set(job_key, json.dumps(job.to_dict()), ex=86400)
        else:
            self._jobs[job.id] = job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        if self.redis:
            job_data = self.redis.get(f"jobs:job:{job_id}")
            if job_data:
                return Job.from_dict(json.loads(job_data))
        return self._jobs.get(job_id)
    
    def get_queue_size(self, queue: Optional[str] = None) -> int:
        queue_name = queue or self.default_queue
        if self.redis:
            return self.redis.llen(f"jobs:queue:{queue_name}")
        return len(self._queue.get(queue_name, []))
    
    def process_next(self, queue: Optional[str] = None, worker: Optional[Callable] = None) -> bool:
        job = self.dequeue(queue)
        if not job:
            return False
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        if self.redis:
            self._update_job_redis(job)
        else:
            self._jobs[job.id] = job
        try:
            if worker:
                result = worker(job)
                self.complete(job, result)
            else:
                raise NotImplementedError("No worker function provided")
        except Exception as e:
            self.fail(job, str(e))
            return False
        return True
    
    def _update_job_redis(self, job: Job) -> None:
        job_key = f"jobs:job:{job.id}"
        self.redis.set(job_key, json.dumps(job.to_dict()), ex=86400)


class JobScheduler:
    def __init__(self, queue: JobQueue):
        self.queue = queue
        self._jobs: Dict[str, Job] = {}
    
    def schedule(self, name: str, payload: Dict[str, Any], cron_expr: str,
                 queue: Optional[str] = None) -> str:
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression")
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id, name=name, queue=queue or self.queue.default_queue,
            payload=payload, scheduled_at=self._next_run(cron_expr)
        )
        self._jobs[job_id] = job
        return job_id
    
    def _next_run(self, cron_expr: str) -> datetime:
        return datetime.utcnow() + timedelta(minutes=1)
    
    def run_ready_jobs(self) -> int:
        now = datetime.utcnow()
        ready_jobs = [
            job for job in self._jobs.values()
            if job.scheduled_at and job.scheduled_at <= now and job.status == JobStatus.PENDING
        ]
        for job in ready_jobs:
            self.queue.enqueue(
                name=job.name, payload=job.payload, queue=job.queue,
                max_retries=job.max_retries, retry_delay=job.retry_delay
            )
            job.status = JobStatus.PENDING
        return len(ready_jobs)


def enqueue_job(name: str, payload: Dict[str, Any], queue: str = "default") -> str:
    return JobQueue().enqueue(name, payload, queue)

def run_worker(queue: str = "default", worker_fn: Optional[Callable] = None) -> None:
    jq = JobQueue()
    while True:
        if jq.process_next(queue, worker_fn):
            time.sleep(0.1)
        else:
            time.sleep(1)

def get_job(job_id: str) -> Optional[Job]:
    return JobQueue().get_job(job_id)
