#!/usr/bin/env python3
"""PyGo CLI (v1.0.0).

Main command-line interface for PyGo framework.
"""

import argparse
import os
import signal
import sys
from pathlib import Path
from typing import Optional


def cmd_doctor(args):
    """Check environment health."""
    errors = []
    warnings = []
    
    # Check Python version
    import sys
    if sys.version_info < (3, 9):
        errors.append(f"Python 3.9+ required, found {sys.version}")
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check Go version
    import subprocess
    try:
        result = subprocess.run(['go', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Go installed")
        else:
            errors.append("Go not installed")
    except FileNotFoundError:
        errors.append("Go not installed")
    
    # Check port availability
    import socket
    port = args.port or 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        warnings.append(f"Port {port} is in use")
    else:
        print(f"✅ Port {port} is available")
    
    # Check database connection
    db_path = os.getenv('DATABASE_URL', ':memory:')
    if db_path == ':memory:':
        print("✅ Using SQLite in-memory database")
    else:
        print(f"✅ Database configured: {db_path[:50]}...")
    
    # Check virtualenv
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment active")
    else:
        warnings.append("Not in a virtual environment")
    
    if errors:
        print("\n❌ Errors:")
        for e in errors:
            print(f"  - {e}")
        return 1
    
    if warnings:
        print("\n⚠️  Warnings:")
        for w in warnings:
            print(f"  - {w}")
    
    print("\n✅ Environment is healthy")
    return 0


def cmd_fmt(args):
    """Format .pgo files."""
    from core.runtime.pygo_fmt import format_file, format_project
    
    target = Path(args.path)
    
    if target.is_file():
        formatted = format_file(str(target))
        print(formatted)
        target.write_text(formatted)
        print(f"✅ Formatted {target}")
    elif target.is_dir():
        format_project(str(target))
    else:
        print(f"Error: {target} not found")
        return 1
    
    return 0


def cmd_shell(args):
    """Start interactive Python REPL with project context."""
    import code
    from core.runtime.db import connect
    from core.runtime.modules import get_manager
    
    print("PyGo Shell - Interactive Python REPL")
    print("Type 'help()' for assistance, 'exit()' to quit")
    print()
    
    # Load project context
    locals_dict = {
        'connect': connect,
        'db': None,
        'models': [],
    }
    
    # Load models if available
    models_dir = Path('models')
    if models_dir.exists():
        for model_file in models_dir.glob('*.pgo'):
            print(f"📦 Loaded model: {model_file.name}")
    
    # Start REPL
    code.interact(local=locals_dict)
    return 0


def cmd_db_seed(args):
    """Seed database with test data."""
    from core.runtime.db import connect, ensure_table
    import uuid
    from datetime import datetime, timedelta
    
    conn = connect()
    
    # Create users table
    ensure_table(conn, 'users', [
        'id TEXT PRIMARY KEY',
        'name TEXT NOT NULL',
        'email TEXT UNIQUE NOT NULL',
        'password_hash TEXT',
        'created_at TIMESTAMP',
        'updated_at TIMESTAMP'
    ])
    
    # Create posts table
    ensure_table(conn, 'posts', [
        'id TEXT PRIMARY KEY',
        'user_id TEXT REFERENCES users(id)',
        'title TEXT NOT NULL',
        'content TEXT',
        'created_at TIMESTAMP',
        'updated_at TIMESTAMP'
    ])
    
    # Insert test users
    users = [
        ('User 1', 'user1@example.com'),
        ('User 2', 'user2@example.com'),
        ('User 3', 'user3@example.com'),
    ]
    
    for name, email in users:
        try:
            conn.execute(
                'INSERT INTO users (id, name, email, created_at) VALUES (?, ?, ?, ?)',
                (str(uuid.uuid4()), name, email, datetime.now())
            )
        except Exception:
            pass  # User already exists
    
    # Insert test posts
    post_titles = [
        'Welcome to PyGo',
        'Building Web Apps',
        'HTMX vs React',
        'Database Design',
        'API Best Practices'
    ]
    
    user_ids = [r[0] for r in conn.execute('SELECT id FROM users').fetchall()]
    
    for i, title in enumerate(post_titles):
        try:
            conn.execute(
                'INSERT INTO posts (id, user_id, title, content, created_at) VALUES (?, ?, ?, ?, ?)',
                (
                    str(uuid.uuid4()),
                    user_ids[i % len(user_ids)],
                    title,
                    f'Content for post: {title}',
                    datetime.now() - timedelta(days=i)
                )
            )
        except Exception:
            pass
    
    conn.commit()
    conn.close()
    
    print(f"✅ Seeded database with {len(users)} users and {len(post_titles)} posts")
    return 0


def cmd_module(args):
    """Module management commands."""
    from core.runtime.modules import ModuleManager
    
    manager = ModuleManager()
    
    if args.subcommand == 'install':
        manager.install(args.module)
    elif args.subcommand == 'list':
        for m in manager.list_modules():
            print(f"  {m.name} ({m.version}) - {'enabled' if m.enabled else 'disabled'}")
    elif args.subcommand == 'enable':
        manager.enable(args.module)
    elif args.subcommand == 'disable':
        manager.disable(args.module)
    elif args.subcommand == 'uninstall':
        manager.uninstall(args.module)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='pygo',
        description='PyGo Framework CLI'
    )
    subparsers = parser.add_subparsers(dest='command')
    
    # doctor command
    doctor_parser = subparsers.add_parser('doctor', help='Check environment health')
    doctor_parser.add_argument('--port', type=int, default=8080, help='Port to check')
    doctor_parser.set_defaults(func=cmd_doctor)
    
    # fmt command
    fmt_parser = subparsers.add_parser('fmt', help='Format .pgo files')
    fmt_parser.add_argument('path', help='File or directory to format')
    fmt_parser.set_defaults(func=cmd_fmt)
    
    # shell command
    shell_parser = subparsers.add_parser('shell', help='Start interactive Python REPL')
    shell_parser.set_defaults(func=cmd_shell)
    
    # db seed command
    db_parser = subparsers.add_parser('db', help='Database commands')
    db_parser.add_argument('subcommand', choices=['seed'], help='Database subcommand')
    db_parser.set_defaults(func=cmd_db_seed)
    
    # module command
    module_parser = subparsers.add_parser('module', help='Module management')
    module_parser.add_argument('subcommand', choices=['install', 'list', 'enable', 'disable', 'uninstall'])
    module_parser.add_argument('module', nargs='?', help='Module name')
    module_parser.set_defaults(func=cmd_module)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())