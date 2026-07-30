"""Test suite for v0.32.0 - Hot Reload and Testing Framework."""
import pytest
import tempfile
import os
import time
from pathlib import Path

from core.runtime.hot_reload import PGoFileHandler, HotReloader, DevServer


class MockEvent:
    """Mock file system event."""
    def __init__(self, path, is_dir=False):
        self.src_path = path
        self.is_directory = is_dir


class TestFileHandler:
    """Test PGoFileHandler."""
    
    def test_v0320_file_handler_ignore_dirs(self):
        """Test that handler ignores directories."""
        changes = []
        def callback(path):
            changes.append(path)
        
        handler = PGoFileHandler(callback)
        
        # Directory event should be ignored
        handler.on_modified(MockEvent("/test/dir", is_dir=True))
        assert len(changes) == 0


def test_v0320_hot_reloader_start_stop():
    """Test HotReloader start and stop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        changes = []
        
        def callback(path):
            changes.append(path)
        
        reloader = HotReloader([tmpdir], callback)
        
        assert not reloader._running
        reloader.start()
        assert reloader._running
        
        reloader.stop()
        assert not reloader._running


def test_v0320_dev_server_init():
    """Test DevServer initialization."""
    server = DevServer(port=3000, watch_dirs=["web"])
    
    assert server.port == 3000
    assert server.watch_dirs == ["web"]
    assert server.reloader is None


def test_v0320_dev_server_file_change():
    """Test DevServer file change handler."""
    server = DevServer()
    
    # Should not raise
    server._on_file_change("/test/app.pgo")


# ============== Testing Framework ==============

from core.runtime.testing import PyGoTest, TestRunner


def test_v0320_pygo_test():
    """Test PyGoTest class."""
    test = PyGoTest(
        name="test_user_can_login",
        description="User can login with valid credentials"
    )
    
    assert test.name == "test_user_can_login"
    assert test.description == "User can login with valid credentials"


def test_v0320_test_runner():
    """Test TestRunner."""
    runner = TestRunner()
    
    assert len(runner.tests) == 0


def test_v0320_test_scenario():
    """Test PyGoTest with scenario."""
    test = PyGoTest(
        name="test_user_login",
        description="Login test",
        scenario="Given a user with valid credentials"
    )
    
    assert test.scenario == "Given a user with valid credentials"


def test_v0320_test_run():
    """Test running a test."""
    test = PyGoTest(
        name="test_pass",
        description="Passing test"
    )
    
    result = test.run()
    assert result["passed"] is True
    assert result["error"] is None


def test_v0320_test_runner_run_all():
    """Test running all tests."""
    runner = TestRunner(verbose=False)
    
    test1 = PyGoTest(name="test1")
    test2 = PyGoTest(name="test2")
    
    runner.add(test1).add(test2)
    summary = runner.run_all()
    
    assert summary["total"] == 2
    assert summary["passed"] == 2
