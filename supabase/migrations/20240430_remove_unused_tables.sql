-- Migration to remove unused tables 
-- Created: 2025-04-30

BEGIN;

-- 1. First check if tables exist before dropping constraints
-- This provides better error reporting

DO $$
DECLARE
  table_count INT;
BEGIN
  SELECT COUNT(*) INTO table_count FROM information_schema.tables 
  WHERE table_schema = 'public' AND 
  table_name IN ('environmental_impact', 'ingredients', 'price_history', 
                'product_alternatives', 'product_errors', 'product_nutrition',
                'product_ingredients');
                
  RAISE NOTICE 'Found % tables to remove', table_count;
END $$;

-- 2. Drop foreign key constraints first to avoid dependency errors

-- Handle product_alternatives constraints
ALTER TABLE IF EXISTS product_alternatives 
  DROP CONSTRAINT IF EXISTS product_alternatives_product_code_fkey,
  DROP CONSTRAINT IF EXISTS product_alternatives_alternative_code_fkey;

-- Handle environmental_impact constraints
ALTER TABLE IF EXISTS environmental_impact
  DROP CONSTRAINT IF EXISTS environmental_impact_product_code_fkey;

-- Handle price_history constraints
ALTER TABLE IF EXISTS price_history
  DROP CONSTRAINT IF EXISTS price_history_product_code_fkey;

-- Handle product_errors constraints
ALTER TABLE IF EXISTS product_errors
  DROP CONSTRAINT IF EXISTS product_errors_product_code_fkey;

-- Handle product_nutrition constraints
ALTER TABLE IF EXISTS product_nutrition
  DROP CONSTRAINT IF EXISTS product_nutrition_product_code_fkey;

-- Special handling for ingredients table
-- First remove constraints in product_ingredients junction table
ALTER TABLE IF EXISTS product_ingredients
  DROP CONSTRAINT IF EXISTS product_ingredients_ingredient_id_fkey,
  DROP CONSTRAINT IF EXISTS product_ingredients_product_code_fkey;

-- 3. Now drop the tables in a safe order (dependencies first)

-- First drop tables that reference other tables
DROP TABLE IF EXISTS product_alternatives;
DROP TABLE IF EXISTS environmental_impact;
DROP TABLE IF EXISTS price_history;
DROP TABLE IF EXISTS product_errors;
DROP TABLE IF EXISTS product_nutrition;
DROP TABLE IF EXISTS product_ingredients;

-- Now drop the main tables
DROP TABLE IF EXISTS ingredients;

-- 4. Add a comment documenting the changes
COMMENT ON SCHEMA public IS 'Tables removed in migration on 2025-04-30: 
environmental_impact, ingredients, price_history, product_alternatives, 
product_errors, product_nutrition, product_ingredients';

-- 5. Verify tables were dropped
DO $$
DECLARE
  remaining_count INT;
BEGIN
  SELECT COUNT(*) INTO remaining_count FROM information_schema.tables 
  WHERE table_schema = 'public' AND 
  table_name IN ('environmental_impact', 'ingredients', 'price_history', 
                'product_alternatives', 'product_errors', 'product_nutrition',
                'product_ingredients');
                
  IF remaining_count > 0 THEN
    RAISE WARNING 'Some tables were not successfully dropped. Remaining: %', remaining_count;
  ELSE
    RAISE NOTICE 'All specified tables successfully dropped';
  END IF;
END $$;

COMMIT; 