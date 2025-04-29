-- Migration script to remove unused columns from the products table

-- BEGIN TRANSACTION
BEGIN;

-- 1. Remove 'source' column which was marked as no longer needed
ALTER TABLE products DROP COLUMN IF EXISTS source;

-- 2. Remove 'ingredients_array' which doesn't appear to be in use in the codebase
ALTER TABLE products DROP COLUMN IF EXISTS ingredients_array;

-- 3. Remove 'risk_score' which appears to cause errors (not in SQLAlchemy model)
-- According to logs, it's causing the error: 'Product' object has no attribute 'risk_score'
ALTER TABLE products DROP COLUMN IF EXISTS risk_score;

-- Add a comment explaining the changes
COMMENT ON TABLE products IS 'Product information table. Unused fields removed in 20240429 migration.';

-- COMMIT TRANSACTION
COMMIT; 