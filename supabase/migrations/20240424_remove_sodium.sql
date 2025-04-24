-- Migration to remove unused sodium_mg column
BEGIN;

-- Check if the column exists before trying to remove it
DO $$ 
BEGIN 
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'products' 
        AND column_name = 'sodium_mg'
    ) THEN
        ALTER TABLE products DROP COLUMN sodium_mg;
        RAISE NOTICE 'Column sodium_mg dropped successfully';
    ELSE
        RAISE NOTICE 'Column sodium_mg does not exist';
    END IF;
END $$;

COMMIT; 