-- Backup tables before removal
-- Created: 2025-04-30
-- Run this script BEFORE running the 20240430_remove_unused_tables.sql migration

BEGIN;

-- Create backup tables with timestamps to avoid conflicts
CREATE TABLE IF NOT EXISTS ingredients_backup_20240430 AS 
SELECT * FROM ingredients;

CREATE TABLE IF NOT EXISTS product_ingredients_backup_20240430 AS 
SELECT * FROM product_ingredients;

CREATE TABLE IF NOT EXISTS environmental_impact_backup_20240430 AS 
SELECT * FROM environmental_impact;

CREATE TABLE IF NOT EXISTS product_alternatives_backup_20240430 AS 
SELECT * FROM product_alternatives;

CREATE TABLE IF NOT EXISTS price_history_backup_20240430 AS 
SELECT * FROM price_history;

CREATE TABLE IF NOT EXISTS product_errors_backup_20240430 AS 
SELECT * FROM product_errors;

CREATE TABLE IF NOT EXISTS product_nutrition_backup_20240430 AS 
SELECT * FROM product_nutrition;

-- Count rows in backup tables to verify
DO $$
DECLARE
    ing_count INT;
    pi_count INT;
    env_count INT;
    alt_count INT;
    price_count INT;
    err_count INT;
    nutr_count INT;
BEGIN
    SELECT COUNT(*) INTO ing_count FROM ingredients_backup_20240430;
    SELECT COUNT(*) INTO pi_count FROM product_ingredients_backup_20240430;
    SELECT COUNT(*) INTO env_count FROM environmental_impact_backup_20240430;
    SELECT COUNT(*) INTO alt_count FROM product_alternatives_backup_20240430;
    SELECT COUNT(*) INTO price_count FROM price_history_backup_20240430;
    SELECT COUNT(*) INTO err_count FROM product_errors_backup_20240430;
    SELECT COUNT(*) INTO nutr_count FROM product_nutrition_backup_20240430;
    
    RAISE NOTICE 'Backup table row counts:';
    RAISE NOTICE 'ingredients: %', ing_count;
    RAISE NOTICE 'product_ingredients: %', pi_count;
    RAISE NOTICE 'environmental_impact: %', env_count;
    RAISE NOTICE 'product_alternatives: %', alt_count;
    RAISE NOTICE 'price_history: %', price_count;
    RAISE NOTICE 'product_errors: %', err_count;
    RAISE NOTICE 'product_nutrition: %', nutr_count;
END $$;

-- Add comment to schema documenting these backups
COMMENT ON SCHEMA public IS 'Backup tables created on 2025-04-30 before migration: 
ingredients_backup_20240430, product_ingredients_backup_20240430,
environmental_impact_backup_20240430, product_alternatives_backup_20240430,
price_history_backup_20240430, product_errors_backup_20240430,
product_nutrition_backup_20240430';

COMMIT; 