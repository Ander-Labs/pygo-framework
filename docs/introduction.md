# Introduction

PyGo is a lightweight Go + Python HTMX framework for building modern web applications.

## Philosophy

- **Lightweight**: Only Go standard library and Python stdlib
- **Full-stack**: One framework for frontend and backend
- **HTMX-first**: No SPA complexity, progressive enhancement
- **Type-safe DSL**: Strong typing with .pgo files
- **Production-ready**: Built-in security, testing, and deployment

## Features

- DSL for defining models, handlers, and routes
- Automatic CRUD generation
- HTMX-powered admin panel
- REST API with OpenAPI spec
- PostgreSQL/MySQL/SQLite support
- Background jobs with Redis
- Email system (SMTP, Mailgun, SendGrid, SES)
- WebSockets for real-time features
- Internationalization (i18n)
- Report generation (PDF, Excel, CSV)

## Quick Start

```bash
# Install PyGo
curl -fsSL https://pygo.dev/install.sh | bash

# Create new project
pygo new myapp

# Run development server
cd myapp
pygo dev
```

## Architecture

PyGo uses a unique architecture:

1. **DSL Layer** (.pgo files) - Define your application declaratively
2. **Transpiler** - Compiles .pgo to Python and Go
3. **Runtime** - Python runtime with Go helpers via Unix sockets
4. **Frontend** - HTMX templates with Tailwind CSS

## Language

PyGo is written primarily in Spanish and English, reflecting the developer's preference and the LATAM market focus.