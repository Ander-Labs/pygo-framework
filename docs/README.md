# PyGo Documentation

This directory contains the documentation for PyGo Framework.

## Building the Documentation

```bash
npm install -g vitepress
cd docs
vitepress dev .
```

## Deploying

```bash
vitepress build .
```

The output will be in `docs/.vitepress/dist/`.

## Structure

- `introduction.md` - Introduction to PyGo
- `installation.md` - Installation guide
- `quickstart.md` - Quick start tutorial
- `dsl.md` - DSL specification
- `architecture.md` - Architecture overview
- `models.md` - Model definitions
- `auth.md` - Authentication
- `admin.md` - Admin panel
- `api.md` - API documentation
- `database.md` - Database guide
- `modules.md` - Module system
- `jobs.md` - Background jobs
- `email.md` - Email system
- `reports.md` - Reports

## Local Development

```bash
# Start dev server
vitepress dev docs

# Build for production
vitepress build docs

# Preview build
vitepress preview docs
```

## GitHub Pages Deployment

The documentation is automatically deployed to GitHub Pages via:
- `.github/workflows/docs.yml` - Deploy workflow