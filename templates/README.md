# {{.ProjectName}}

A PyGo application - modern web framework with Go backend and Python flexibility.

## Quick Start

```bash
# Install PyGo (if not already installed)
curl -fsSL https://pygo.dev/install.sh | bash

# Install dependencies
pygo dev

# Development server running at http://localhost:8080
```

## Project Structure

```
.
├── pygo.toml              # Project configuration
├── .env.example           # Environment variables template
├── app/
│   ├── models/            # Data models (.pgo files)
│   │   └── user.pgo
│   ├── handlers/          # Request handlers
│   │   └── dashboard.pgo
│   └── views/             # HTML templates
│       ├── base.html
│       └── dashboard.html
├── modules/               # Custom modules
└── README.md
```

## Commands

```bash
pygo dev      # Start development server with hot-reload
pygo build    # Build production binary
pygo db migrate  # Run database migrations
pygo db seed     # Seed test data
```

## Authentication

The template includes a User model with authentication:

- **Email**: User's email address
- **Password**: Bcrypt-hashed password
- **Role**: User role (admin, user, etc.)

## Learn More

- [Documentation](https://pygo.dev/docs)
- [API Reference](https://pygo.dev/docs/api)
- [Community](https://github.com/Ander-Labs/pygo/discussions)

## License

AGPL-3.0 - See LICENSE file for details.