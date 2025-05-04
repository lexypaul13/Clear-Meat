-- Backup tables before removal
-- Created: 2025-04-30
-- Run this script BEFORE running the 20240430_remove_unused_tables.sql migration

BEGIN;

-- Create backup tables with timestamps to avoid conflicts
-- Removed backup for non-existent table ingredients
-- CREATE TABLE IF NOT EXISTS ingredients_backup_20240430 AS 
-- SELECT * FROM ingredients;

CREATE TABLE IF NOT EXISTS product_ingredients_backup_20240430 AS 
SELECT * FROM product_ingredients;

-- Removed backup for non-existent table environmental_impact
-- CREATE TABLE IF NOT EXISTS environmental_impact_backup_20240430 AS 
-- SELECT * FROM environmental_impact;

CREATE TABLE IF NOT EXISTS product_alternatives_backup_20240430 AS 
SELECT * FROM product_alternatives;

-- Removed backup for non-existent table price_history
-- CREATE TABLE IF NOT EXISTS price_history_backup_20240430 AS 
-- SELECT * FROM price_history;

-- Removed backup for non-existent table product_errors
-- CREATE TABLE IF NOT EXISTS product_errors_backup_20240430 AS 
-- SELECT * FROM product_errors;

-- Removed backup for non-existent table product_nutrition
-- CREATE TABLE IF NOT EXISTS product_nutrition_backup_20240430 AS 
-- SELECT * FROM product_nutrition;

-- Count rows in backup tables to verify
DO $$
DECLARE
    -- ing_count INT; -- Removed variable for ingredients
    pi_count INT;
    -- env_count INT; -- Removed variable for env impact
    alt_count INT;
    -- price_count INT; -- Removed variable for price history
    -- err_count INT; -- Removed variable for product errors
    -- nutr_count INT; -- Removed variable for product nutrition
BEGIN
    -- SELECT COUNT(*) INTO ing_count FROM ingredients_backup_20240430; -- Removed count for ingredients
    SELECT COUNT(*) INTO pi_count FROM product_ingredients_backup_20240430;
    -- SELECT COUNT(*) INTO env_count FROM environmental_impact_backup_20240430; -- Removed count for env impact
    SELECT COUNT(*) INTO alt_count FROM product_alternatives_backup_20240430;
    -- SELECT COUNT(*) INTO price_count FROM price_history_backup_20240430; -- Removed count for price history
    -- SELECT COUNT(*) INTO err_count FROM product_errors_backup_20240430; -- Removed count for product errors
    -- SELECT COUNT(*) INTO nutr_count FROM product_nutrition_backup_20240430; -- Removed count for product nutrition
    
    RAISE NOTICE 'Backup table row counts:';
    -- RAISE NOTICE 'ingredients: %', ing_count; -- Removed notice for ingredients
    RAISE NOTICE 'product_ingredients: %', pi_count;
    -- RAISE NOTICE 'environmental_impact: %', env_count; -- Removed notice for env impact
    RAISE NOTICE 'product_alternatives: %', alt_count;
    -- RAISE NOTICE 'price_history: %', price_count; -- Removed notice for price history
    -- RAISE NOTICE 'product_errors: %', err_count; -- Removed notice for product errors
    -- RAISE NOTICE 'product_nutrition: %', nutr_count; -- Removed notice for product nutrition
END $$;

-- Add comment to schema documenting these backups
COMMENT ON SCHEMA public IS 'Backup tables created on 2025-04-30 before migration: 
-- ingredients_backup_20240430, -- Removed ingredients from comment
product_ingredients_backup_20240430,
-- environmental_impact_backup_20240430, -- Removed env impact from comment
product_alternatives_backup_20240430
-- price_history_backup_20240430, -- Removed price history from comment
-- product_errors_backup_20240430, -- Removed product errors from comment
-- product_nutrition_backup_20240430 -- Removed product nutrition from comment
';

COMMIT; 