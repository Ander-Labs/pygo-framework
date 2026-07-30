# Contributing to PyGo Framework

Thank you for your interest in contributing to PyGo! 🎉

## Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/Ander-Labs/pygo.git
cd pygo

# Install Go 1.22+
go version # Should show 1.22 or later

# Install Python 3.10+
python3 --version # Should show 3.10 or later

# Install dependencies
go mod download
pip install -r requirements.txt

# Run tests
go test ./...
pytest tests/
```

## Running Tests

```bash
# Go tests
go test ./... -v

# Python tests
pytest tests/ -v

# Transpiler tests
go test ./core/transpiler/... -v
```

## Code Structure

```
pygo-framework/
├── cmd/              # CLI entry point
├── core/
│   ├── runtime/      # Python runtime
│   └── transpiler/   # DSL transpiler (Go)
├── templates/        # Project templates
└── docs/             # Documentation
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Run tests to ensure they pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### PR Checklist

- [ ] Tests added/updated
- [ ] Code follows Go formatting (`gofmt`)
- [ ] Python code follows ruff/black
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG updated (for features/fixes)

## Coding Standards

- **Go**: Use `gofmt`, follow standard Go conventions
- **Python**: Use `ruff` and `black` for formatting
- **DSL**: Follow the PyGo DSL specification

## Questions?

Open an issue or join our [Discussions](https://github.com/Ander-Labs/pygo/discussions).