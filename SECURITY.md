# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| 0.x     | :x:                |

## Reporting a Vulnerability

We take the security of PyGo seriously. If you discover a security vulnerability,
please report it responsibly.

### How to Report

**Email**: security@pygo.dev

Please include:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

### What to Expect

* We will acknowledge your report within 48 hours
* We will provide a more detailed response within 7 days
* We will keep you informed of the progress towards a fix

### Responsible Disclosure

We ask that you:

* Do not disclose the vulnerability publicly until we have had a chance to fix it
* Do not access or modify data that is not yours
* Act in good faith to avoid privacy violations, destruction of data, and interruption or degradation of our services

## Security Best Practices

When using PyGo:

1. Always use environment variables for secrets (never hardcode)
2. Generate strong, unique secrets for `JWT_SECRET` and `APP_KEY`
3. Keep PyGo updated to the latest version
4. Use HTTPS in production
5. Set appropriate file permissions on `.env` files
6. Regular database backups

## Security Features

PyGo includes built-in security features:

* **Password Hashing**: Bcrypt/Argon2id
* **CSRF Protection**: Automatic token validation
* **XSS Protection**: Automatic HTML escaping
* **Rate Limiting**: Configurable limits
* **Security Headers**: CSP, X-Frame-Options, etc.
* **Input Validation**: Type-safe DSL

Thank you for helping keep PyGo secure!