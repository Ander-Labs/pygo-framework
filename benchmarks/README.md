# PyGo Benchmarks

Performance benchmarks for the PyGo framework.

## Running Benchmarks

```bash
python benchmarks/run_benchmarks.py
```

## Benchmark Results

### Latest Results (as of 2024-07-31)

| Benchmark | Operations/sec | Mean Time |
|-----------|----------------|-----------|
| Static Route | ~10,000 RPS | 0.1ms |
| DB Query | ~1,000 RPS | 1ms |
| IPC Call | ~2,000 RPS | 0.5ms |
| HTMX Update | ~500 RPS | 2ms |

## Interpretation

- **Static Route**: Baseline performance for serving static content
- **DB Query**: ORM overhead with SQLite
- **IPC Call**: Go ↔ Python communication overhead
- **HTMX Update**: Full request lifecycle with partial update

## Contributing

New benchmarks should be added to `benchmarks/run_benchmarks.py` and follow the same pattern.

## Historical Results

Results are saved to `benchmarks/results/` after each CI run.