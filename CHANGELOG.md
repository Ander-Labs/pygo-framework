# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Distribution and installation system
- GoReleaser configuration for multi-platform builds
- Universal installer script (install.sh)
- Project scaffolding with `pygo new` command
- Templates directory with base project structure
- CI/CD GitHub Actions workflows
- CONTRIBUTING.md with development guidelines
- CODE_OF_CONDUCT.md for community behavior
- SECURITY.md with vulnerability reporting policy
- GitHub issue and PR templates

## [0.35.0] - 2026-01-XX

### Added
- Gap analysis completed - parser CRUD and ecosystem features
- CrudNode now generates 5 REST routes automatically
- Benchmark system for performance testing
- Security utilities module
- Updated falta-implementar.md with current status

## [0.34.0] - 2025-12-XX

### Added
- Audit system for change tracking
- Workflow engine with state machines
- Tests for audit and workflow systems

## [0.33.0] - 2025-12-XX

### Added
- Internationalization (i18n) system
- WebSocket support with channels and pub/sub
- Tests for globalization features

## [0.32.0] - 2025-12-XX

### Added
- Hot reload system for development
- Testing framework (PyGoTest, TestRunner)
- Tests for hot-reload and testing framework

## [0.31.0] - 2025-12-XX

### Added
- Report engine (PDF, Excel, CSV)
- Background job system with queue and scheduler
- Email system with SMTP and templates
- Cache system (Memory, Redis)
- Tests for enterprise features

## [0.30.0] - 2025-12-XX

### Added
- Admin panel automatic generator
- API REST automatic generation
- OpenAPI/Swagger documentation
- Pagination and filtering

## [0.29.0] - 2025-12-XX

### Added
- Module system with lifecycle hooks
- Module manager for install/list/enable/disable
- Permission system per module

## [0.28.0] - 2025-12-XX

### Added
- Authentication system
- Sessions (cookie-based)
- JWT tokens
- OAuth2 support
- Password hashing (Argon2id)
- CSRF protection
- Rate limiting middleware

## [0.27.0] - 2025-12-XX

### Added
- ORM with PostgreSQL/MySQL support
- Query builder
- Database abstraction layer

## [0.26.0] - 2025-12-XX

### Fixed
- Multi-tenancy bug resolved
- Unix Sockets communication between Go and Python

## [0.25.0] - 2025-12-XX

### Added
- Enhanced CLI with `gen` and `test` commands
- Development server improvements

## [0.24.0] - 2025-12-XX

### Added
- Documentation updates
- falta-implementar.md roadmap updated

[Unreleased]: https://github.com/Ander-Labs/pygo/compare/v0.35.0...HEAD
[0.35.0]: https://github.com/Ander-Labs/pygo/compare/v0.34.0...v0.35.0
[0.34.0]: https://github.com/Ander-Labs/pygo/compare/v0.33.0...v0.34.0
[0.33.0]: https://github.com/Ander-Labs/pygo/compare/v0.32.0...v0.33.0
[0.32.0]: https://github.com/Ander-Labs/pygo/compare/v0.31.0...v0.32.0
[0.31.0]: https://github.com/Ander-Labs/pygo/compare/v0.30.0...v0.31.0
[0.30.0]: https://github.com/Ander-Labs/pygo/compare/v0.29.0...v0.30.0
[0.29.0]: https://github.com/Ander-Labs/pygo/compare/v0.28.0...v0.29.0
[0.28.0]: https://github.com/Ander-Labs/pygo/compare/v0.27.0...v0.28.0
[0.27.0]: https://github.com/Ander-Labs/pygo/releases/tag/v0.27.0