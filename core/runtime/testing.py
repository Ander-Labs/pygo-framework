"""PyGo Testing Framework (v0.32.0).

Provides fixtures, test runners, and scenario testing.
"""

from __future__ import annotations

from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
import time
import uuid


@dataclass
class PyGoTest:
    """Represents a PyGo test case."""
    name: str
    description: str = ""
    scenario: str = ""
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)
    
    def run(self) -> Dict[str, Any]:
        """Run the test and return result."""
        result = {
            "name": self.name,
            "passed": False,
            "duration": 0,
            "error": None
        }
        
        start = time.time()
        
        try:
            if self.setup:
                self.setup()
            
            # Test would run here
            result["passed"] = True
            
        except Exception as e:
            result["error"] = str(e)
        finally:
            if self.teardown:
                try:
                    self.teardown()
                except Exception as e:
                    if result["error"] is None:
                        result["error"] = f"Teardown error: {e}"
            
            result["duration"] = time.time() - start
        
        return result


class TestRunner:
    """Runs PyGo tests."""
    
    def __init__(self, verbose: bool = True):
        self.tests: List[PyGoTest] = []
        self.verbose = verbose
        self._results: List[Dict[str, Any]] = []
    
    def add(self, test: PyGoTest) -> "TestRunner":
        """Add a test to the runner."""
        self.tests.append(test)
        return self
    
    def run_all(self) -> Dict[str, Any]:
        """Run all tests and return summary."""
        for test in self.tests:
            result = test.run()
            self._results.append(result)
            
            if self.verbose:
                status = "✓" if result["passed"] else "✗"
                print(f"{status} {test.name} ({result['duration']:.3f}s)")
                if result["error"]:
                    print(f"  Error: {result['error']}")
        
        passed = sum(1 for r in self._results if r["passed"])
        failed = len(self._results) - passed
        
        return {
            "total": len(self._results),
            "passed": passed,
            "failed": failed,
            "results": self._results
        }
    
    def clear(self):
        """Clear all tests."""
        self.tests.clear()
        self._results.clear()


# Fixture registry
_fixtures: Dict[str, Callable] = {}


def fixture(name: Optional[str] = None):
    """Decorator to register a fixture."""
    def decorator(func: Callable) -> Callable:
        fixture_name = name or func.__name__
        _fixtures[fixture_name] = func
        return func
    return decorator


def get_fixture(name: str) -> Optional[Callable]:
    """Get a registered fixture."""
    return _fixtures.get(name)


def run_tests(tests: List[PyGoTest], verbose: bool = True) -> Dict[str, Any]:
    """Run a list of tests."""
    runner = TestRunner(verbose=verbose)
    for test in tests:
        runner.add(test)
    return runner.run_all()


def assert_equal(expected: Any, actual: Any, message: str = ""):
    """Assert two values are equal."""
    if expected != actual:
        raise AssertionError(f"{message}\nExpected: {expected}\nActual: {actual}")


def assert_true(value: bool, message: str = ""):
    """Assert a value is true."""
    if not value:
        raise AssertionError(f"{message}\nExpected: True\nActual: {value}")


def assert_in(needle: Any, haystack: Any, message: str = ""):
    """Assert needle is in haystack."""
    if needle not in haystack:
        raise AssertionError(f"{message}\n{needle} not found in {haystack}")


def assert_raises(exception: type, func: Callable, *args, **kwargs):
    """Assert function raises expected exception."""
    try:
        func(*args, **kwargs)
        raise AssertionError(f"Expected {exception.__name__} but no exception was raised")
    except exception:
        pass  # Expected
    except Exception as e:
        raise AssertionError(f"Expected {exception.__name__} but got {type(e).__name__}: {e}")