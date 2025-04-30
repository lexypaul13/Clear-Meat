-- Migration script to remove ingredients and product_ingredients tables
-- Date: 2024-04-30
-- Description: Removes the ingredients and product_ingredients tables that are no longer used in the application

-- Create a function to log progress
CREATE OR REPLACE FUNCTION log_migration_progress(message TEXT) RETURNS VOID AS $$
BEGIN
    RAISE NOTICE '%', message;
END;
$$ LANGUAGE plpgsql;

-- Begin a transaction for the entire operation
BEGIN;

-- Create backup tables before dropping the originals
SELECT log_migration_progress('Creating backup tables...');

-- Backup ingredients table
CREATE TABLE IF NOT EXISTS ingredients_backup_20240430 AS
SELECT * FROM ingredients;

-- Backup product_ingredients table
CREATE TABLE IF NOT EXISTS product_ingredients_backup_20240430 AS
SELECT * FROM product_ingredients;

-- Count the number of rows in the backup tables to verify
DO $$
DECLARE
    ingredients_count INTEGER;
    product_ingredients_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO ingredients_count FROM ingredients_backup_20240430;
    SELECT COUNT(*) INTO product_ingredients_count FROM product_ingredients_backup_20240430;
    
    PERFORM log_migration_progress('Backup row counts:');
    PERFORM log_migration_progress('ingredients: ' || ingredients_count::TEXT);
    PERFORM log_migration_progress('product_ingredients: ' || product_ingredients_count::TEXT);
END $$;

-- Now drop constraints and tables
SELECT log_migration_progress('Dropping constraints and tables...');

-- First remove constraints in product_ingredients junction table
ALTER TABLE IF EXISTS product_ingredients
DROP CONSTRAINT IF EXISTS product_ingredients_ingredient_id_fkey,
DROP CONSTRAINT IF EXISTS product_ingredients_product_code_fkey;

-- Now drop the tables
SELECT log_migration_progress('Dropping tables...');
DROP TABLE IF EXISTS product_ingredients;
DROP TABLE IF EXISTS ingredients;

-- Verify that tables are gone
DO $$
BEGIN
    PERFORM log_migration_progress('Verifying tables are removed...');
    
    -- This will throw an error if the tables don't exist, which is good
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'ingredients') THEN
        RAISE EXCEPTION 'Table ingredients still exists!';
    END IF;
    
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'product_ingredients') THEN
        RAISE EXCEPTION 'Table product_ingredients still exists!';
    END IF;
    
    PERFORM log_migration_progress('Tables successfully removed. Backups available as ingredients_backup_20240430 and product_ingredients_backup_20240430');
END $$;

-- Commit the transaction
COMMIT;

-- Function to get backup information - can be used later to check backup status
CREATE OR REPLACE FUNCTION get_backup_info() RETURNS TABLE (
    table_name TEXT,
    row_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'ingredients_backup_20240430'::TEXT, COUNT(*)::BIGINT FROM ingredients_backup_20240430
    UNION ALL
    SELECT 'product_ingredients_backup_20240430'::TEXT, COUNT(*)::BIGINT FROM product_ingredients_backup_20240430;
END;
$$ LANGUAGE plpgsql; 