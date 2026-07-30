"""PyGo Performance Benchmarks (v0.35.0).

Provides benchmark tests for performance optimization.
"""

from __future__ import annotations

import time
import timeit
from typing import Dict, Any, Callable
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Result of a benchmark."""
    name: str
    duration: float
    iterations: int
    ops_per_second: float


class BenchmarkRunner:
    """Runs performance benchmarks."""
    
    def __init__(self):
        self.results: list[BenchmarkResult] = []
    
    def run(self, name: str, func: Callable, iterations: int = 1000) -> BenchmarkResult:
        """Run a benchmark."""
        start = time.perf_counter()
        
        for _ in range(iterations):
            func()
        
        end = time.perf_counter()
        duration = end - start
        ops_per_second = iterations / duration if duration > 0 else 0
        
        result = BenchmarkResult(
            name=name,
            duration=duration,
            iterations=iterations,
            ops_per_second=ops_per_second
        )
        
        self.results.append(result)
        return result
    
    def report(self) -> str:
        """Generate a report of benchmark results."""
        lines = ["Benchmark Results:"]
        lines.append("-" * 50)
        
        for r in self.results:
            lines.append(f"{r.name}:")
            lines.append(f"  Duration: {r.duration:.4f}s")
            lines.append(f"  Iterations: {r.iterations}")
            lines.append(f"  Ops/sec: {r.ops_per_second:.2f}")
        
        return "\n".join(lines)


# Convenience function
def benchmark(name: str, func: Callable, iterations: int = 1000) -> BenchmarkResult:
    """Run a single benchmark."""
    runner = BenchmarkRunner()
    return runner.run(name, func, iterations)
