-- Seed data for PyGo application
-- Run with: pygo db seed

-- Create admin user
INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'admin@example.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA/7.J6LlZy', -- password: 'password'
  'admin',
  datetime('now'),
  datetime('now')
);

-- Create test user
INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  'user@example.com',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA/7.J6LlZy', -- password: 'password'
  'user',
  datetime('now'),
  datetime('now')
);