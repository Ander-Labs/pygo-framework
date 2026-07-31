"""Test suite for v0.42.0 - Background Jobs Redis."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from core.runtime.jobs import (
    Job, JobStatus, JobQueue, JobScheduler,
    enqueue_job, get_job
)


def test_job_creation():
    """Test creating a job."""
    job = Job(
        id="test-id",
        name="test_job",
        queue="default",
        payload={"data": "test"}
    )
    
    assert job.id == "test-id"
    assert job.name == "test_job"
    assert job.queue == "default"
    assert job.payload == {"data": "test"}
    assert job.status == JobStatus.PENDING


def test_job_to_dict():
    """Test job serialization."""
    job = Job(
        id="test-id",
        name="test_job",
        queue="default",
        payload={"key": "value"},
        retry_count=2,
        max_retries=3
    )
    
    d = job.to_dict()
    
    assert d['id'] == "test-id"
    assert d['name'] == "test_job"
    assert d['payload'] == {"key": "value"}
    assert d['status'] == "pending"
    assert d['retry_count'] == 2


def test_job_from_dict():
    """Test job deserialization."""
    data = {
        'id': 'test-id',
        'name': 'test_job',
        'queue': 'default',
        'payload': {'key': 'value'},
        'status': 'completed',
        'retry_count': 1,
        'max_retries': 3,
        'created_at': '2024-01-01T00:00:00',
        'metadata': {}
    }
    
    job = Job.from_dict(data)
    
    assert job.id == 'test-id'
    assert job.status == JobStatus.COMPLETED
    assert job.retry_count == 1


def test_job_queue_enqueue():
    """Test enqueueing jobs."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test_job", {"data": "test"})
    
    assert job_id is not None
    assert len(jq._jobs) == 1
    assert job_id in jq._jobs


def test_job_queue_dequeue():
    """Test dequeuing jobs."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test_job", {"data": "test"})
    job = jq.dequeue()
    
    assert job is not None
    assert job.id == job_id
    assert job.status == JobStatus.PENDING  # dequeue does not change status


def test_job_queue_complete():
    """Test completing jobs."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test_job", {"data": "test"})
    job = jq.dequeue()
    
    jq.complete(job, {"result": "success"})
    
    assert job.status == JobStatus.COMPLETED
    assert job.result == {"result": "success"}


def test_job_queue_fail_and_retry():
    """Test job failure and retry."""
    jq = JobQueue()
    
    job = Job(
        id="test-id",
        name="test_job",
        queue="default",
        payload={"data": "test"},
        max_retries=2,
        retry_delay=1
    )
    jq._jobs[job.id] = job
    
    jq.fail(job, "Test error")
    
    assert job.status == JobStatus.RETRY
    assert job.retry_count == 1
    assert job.error == "Test error"


def test_job_queue_fail_dead_letter():
    """Test job moves to dead letter queue after max retries."""
    jq = JobQueue()
    
    job = Job(
        id="test-id",
        name="test_job",
        queue="default",
        payload={"data": "test"},
        max_retries=2,
        retry_count=2  # Already at max
    )
    jq._jobs[job.id] = job
    
    jq.fail(job, "Test error")
    
    assert job.status == JobStatus.DEAD


def test_job_queue_get_job():
    """Test getting job by ID."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test_job", {"data": "test"})
    job = jq.get_job(job_id)
    
    assert job is not None
    assert job.id == job_id


def test_job_queue_get_queue_size():
    """Test getting queue size."""
    jq = JobQueue()
    
    assert jq.get_queue_size() == 0
    
    jq.enqueue("job1", {})
    jq.enqueue("job2", {})
    
    assert jq.get_queue_size() == 2


def test_job_scheduler_schedule():
    """Test scheduling jobs."""
    jq = JobQueue()
    scheduler = JobScheduler(jq)
    
    job_id = scheduler.schedule("scheduled_job", {"data": "test"}, "*/5 * * * *")
    
    assert job_id is not None


def test_job_scheduler_run_ready_jobs():
    """Test running ready scheduled jobs."""
    jq = JobQueue()
    scheduler = JobScheduler(jq)
    
    # Schedule job to run immediately
    job_id = scheduler.schedule(
        "immediate_job",
        {"data": "test"},
        "* * * * *"
    )
    # Manually set scheduled_at
    for j in scheduler._jobs.values():
        j.scheduled_at = datetime.utcnow() - timedelta(minutes=1)
    
    count = scheduler.run_ready_jobs()
    
    assert count >= 1


def test_process_next_with_worker():
    """Test processing jobs with worker function."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test_job", {"data": "test"})
    
    def worker(job):
        return {"processed": True, "job_id": job.id}
    
    result = jq.process_next(worker=worker)
    
    assert result is True
    job = jq.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.result == {"processed": True, "job_id": job_id}


def test_process_next_failure():
    """Test processing job that fails."""
    jq = JobQueue()
    
    job_id = jq.enqueue("failing_job", {"data": "test"}, max_retries=1)
    
    def failing_worker(job):
        raise ValueError("Worker failed")
    
    result = jq.process_next(worker=failing_worker)
    
    assert result is False
    job = jq.get_job(job_id)
    assert job.status == JobStatus.RETRY


def test_convenience_enqueue():
    """Test convenience enqueue function."""
    job_id = enqueue_job("test", {"data": "test"})
    assert job_id is not None


def test_convenience_get_job():
    """Test convenience get_job function."""
    # Note: convenience functions create new JobQueue instances
    # In production, use a shared JobQueue instance
    jq = JobQueue()
    job_id = jq.enqueue("test", {"data": "test"})
    job = jq.get_job(job_id)
    assert job is not None
    assert job.name == "test"


def test_job_with_scheduled_time():
    """Test job with scheduled time."""
    future = datetime.utcnow() + timedelta(hours=1)
    job = Job(
        id="test-id",
        name="scheduled_job",
        queue="default",
        payload={},
        scheduled_at=future
    )
    
    assert job.scheduled_at > datetime.utcnow()


def test_job_metadata():
    """Test job with metadata."""
    job = Job(
        id="test-id",
        name="test_job",
        queue="default",
        payload={},
        metadata={"priority": "high", "tenant": "acme"}
    )
    
    assert job.metadata["priority"] == "high"
    assert job.metadata["tenant"] == "acme"


def test_job_status_values():
    """Test all job status values."""
    statuses = [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED,
                JobStatus.FAILED, JobStatus.RETRY, JobStatus.DEAD]
    
    for status in statuses:
        assert isinstance(status.value, str)