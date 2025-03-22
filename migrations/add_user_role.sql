-- Add role column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'basic';

-- Make sure all existing users have a role
UPDATE users SET role = 'basic' WHERE role IS NULL;

-- Set superusers to admin role
UPDATE users SET role = 'admin' WHERE is_superuser = TRUE; 