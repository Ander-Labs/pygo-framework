# Contributing to PyGo Framework

Thank you for your interest in contributing to PyGo! This document provides guidelines for contributing.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Ander-Labs/PYGO-generalidades.git
   cd PYGO-generalidades
   ```

2. Install dependencies:
   ```bash
   # Python
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   
   # Go (for CLI)
   go install
   ```

## Project Structure

```
pygo-framework/
├── cli/              # Command-line interface
├── core/
│   ├── runtime/    # Python runtime
│   ├── transpiler/ # Go transpiler
│   └── ...
├── examples/       # Example applications
├── docs/           # Documentation
└── tests/          # Test suites
```

## Development Phases

The framework is developed in phases:

- **v0.11.0-v0.25.0**: Foundation (DSL, Transpiler, CLI)
- **v0.26.0-v0.30.0**: Core features (ORM, Auth, Admin)
- **v0.31.0-v0.34.0**: Enterprise features (Reports, Jobs, Cache)
- **v0.35.0**: v1.0.0 preparation (Security, Stability)

## Coding Standards

### Python
- Use type hints
- Follow PEP 8
- Write docstrings for public functions
- Use dataclasses for data structures

### Go
- Follow Go conventions
- Use standard library only (no heavy frameworks)
- Write clear error messages

## Testing

Run tests before submitting:

```bash
# Python tests
python -m pytest core/runtime/ -v

# Go tests
go test ./... -v

# All tests
make test
```

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Add/update tests
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request

## Commit Messages

Use conventional commit format:
```
feat(v0.35.0): Add security headers

- Added SecurityHeaders class
- Added X-Content-Type-Options header
- Added Content-Security-Policy header
```

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.
