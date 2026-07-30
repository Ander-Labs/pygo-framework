"""Test suite for v0.31.0 - Background Jobs."""
import pytest
import time
import threading

from core.runtime.jobs import (
    Job, JobStatus, JobQueue, get_job_queue, schedule, get_job, list_jobs, job
)


def test_v0310_job_status():
    """Test JobStatus enum."""
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"


def test_v0310_job_dataclass():
    """Test Job dataclass."""
    job = Job(
        id="test-123",
        name="test_job",
        func=lambda: None
    )
    
    assert job.id == "test-123"
    assert job.name == "test_job"
    assert job.status == JobStatus.PENDING


def test_v0310_job_queue_enqueue():
    """Test enqueuing jobs."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test", lambda: "result")
    
    assert job_id is not None
    assert len(jq.get_jobs()) == 1
    
    job = jq.get_job(job_id)
    assert job.status == JobStatus.PENDING


def test_v0310_job_queue_get_jobs():
    """Test getting jobs."""
    jq = JobQueue()
    
    jq.enqueue("job1", lambda: None)
    jq.enqueue("job2", lambda: None)
    
    all_jobs = jq.get_jobs()
    assert len(all_jobs) == 2
    
    pending_jobs = jq.get_jobs(JobStatus.PENDING)
    assert len(pending_jobs) == 2


def test_v0310_job_execution():
    """Test job execution."""
    jq = JobQueue(max_workers=2)
    
    # Job that returns a result
    def test_func():
        return "success"
    
    job_id = jq.enqueue("test", test_func)
    
    # Manually process (since start() runs in background)
    job = jq.get_job(job_id)
    jq._process_job(job)
    
    # Check result
    assert job.status == JobStatus.COMPLETED
    assert job.result == "success"


def test_v0310_job_failure():
    """Test job failure handling."""
    jq = JobQueue(max_workers=2)
    
    def failing_func():
        raise ValueError("Test error")
    
    job_id = jq.enqueue("test", failing_func, retries=2)
    job = jq.get_job(job_id)
    jq._process_job(job)
    
    assert job.status == JobStatus.FAILED
    assert job.error is not None
    assert "Test error" in job.error


def test_v0310_job_retry():
    """Test job retry mechanism."""
    jq = JobQueue(max_workers=2)
    
    attempt = [0]
    
    def flaky_func():
        attempt[0] += 1
        if attempt[0] < 3:
            raise ValueError("Not yet")
        return "success"
    
    job_id = jq.enqueue("test", flaky_func, retries=5, retry_delay=0.1)
    job = jq.get_job(job_id)
    jq._process_job(job)
    
    # Should have retried
    assert job.retries < 5  # Retries were consumed


def test_v0310_global_functions():
    """Test global convenience functions."""
    jq = get_job_queue()
    
    job_id = schedule("test", lambda: "result")
    job = get_job(job_id)
    
    assert job is not None
    assert job.name == "test"


def test_v0310_job_decorator():
    """Test job decorator."""
    @job("decorated_job", retries=2)
    def my_job():
        return "done"
    
    # The decorated function should return a job ID
    job_id = my_job()
    assert job_id is not None


def test_v0310_job_tenant():
    """Test tenant propagation in jobs."""
    jq = JobQueue()
    
    job_id = jq.enqueue("test", lambda: None, tenant="tenant-123")
    job = jq.get_job(job_id)
    
    assert job.tenant == "tenant-123"


def test_v0310_queue_start_stop():
    """Test queue start/stop."""
    jq = JobQueue(max_workers=2)
    
    assert not jq._running
    jq.start()
    assert jq._running
    jq.stop()
    assert not jq._running