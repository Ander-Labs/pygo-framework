-- Seed data for PyGo application
-- Run with: pygo db seed

-- Create admin user (password: admin123, hashed with bcrypt)
INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.Xqt8F.fOy',
    'admin',
    '2024-01-01T00:00:00Z',
    '2024-01-01T00:00:00Z'
);

-- Create demo user (password: demo123)
INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'demo@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.aOy6.Xqt8F.fOy',
    'user',
    '2024-01-01T00:00:00Z',
    '2024-01-01T00:00:00Z'
);