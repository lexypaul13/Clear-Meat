-- Migration: Remove backup and unused tables
-- Date: 2024-05-15

BEGIN;

-- Step 1: Check table existence before attempting operations
DO $$
DECLARE
    tables_to_check TEXT[] := ARRAY[
        'ingredients_backup_20240430',
        'price_history',
        'product_alternatives',
        'product_errors',
        'product_ingredients_backup_20240430',
        'product_nutrition',
        'supply_chain'
    ];
    table_exists BOOLEAN;
    current_table TEXT;
BEGIN
    RAISE NOTICE 'Starting table removal verification...';
    
    FOREACH current_table IN ARRAY tables_to_check
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = current_table
        ) INTO table_exists;
        
        IF table_exists THEN
            RAISE NOTICE 'Table % exists and will be removed', current_table;
        ELSE
            RAISE NOTICE 'Table % does not exist, skipping removal', current_table;
        END IF;
    END LOOP;
END $$;

-- Step 2: Drop foreign key constraints first
-- This ensures we can drop tables without constraint violations
DO $$
DECLARE
    constraint_record RECORD;
BEGIN
    -- Find and drop all foreign key constraints pointing to the tables we want to remove
    FOR constraint_record IN
        SELECT tc.table_schema, tc.constraint_name, tc.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
            ON tc.constraint_catalog = ccu.constraint_catalog 
            AND tc.constraint_schema = ccu.constraint_schema
            AND tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND (
            ccu.table_name IN (
                'ingredients_backup_20240430',
                'price_history',
                'product_alternatives',
                'product_errors',
                'product_ingredients_backup_20240430',
                'product_nutrition',
                'supply_chain'
            )
            OR tc.table_name IN (
                'ingredients_backup_20240430',
                'price_history',
                'product_alternatives',
                'product_errors',
                'product_ingredients_backup_20240430',
                'product_nutrition',
                'supply_chain'
            )
        )
    LOOP
        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT %I CASCADE',
            constraint_record.table_schema,
            constraint_record.table_name,
            constraint_record.constraint_name
        );
        RAISE NOTICE 'Dropped constraint % on table %', 
            constraint_record.constraint_name, 
            constraint_record.table_name;
    END LOOP;
END $$;

-- Step 3: Drop tables in dependency order (if they exist)
-- This ensures dependent tables are removed first

-- product_nutrition table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_nutrition') THEN
        DROP TABLE public.product_nutrition;
        RAISE NOTICE 'Dropped table product_nutrition';
    END IF;
END $$;

-- product_alternatives table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_alternatives') THEN
        DROP TABLE public.product_alternatives;
        RAISE NOTICE 'Dropped table product_alternatives';
    END IF;
END $$;

-- product_errors table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_errors') THEN
        DROP TABLE public.product_errors;
        RAISE NOTICE 'Dropped table product_errors';
    END IF;
END $$;

-- price_history table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'price_history') THEN
        DROP TABLE public.price_history;
        RAISE NOTICE 'Dropped table price_history';
    END IF;
END $$;

-- supply_chain table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'supply_chain') THEN
        DROP TABLE public.supply_chain;
        RAISE NOTICE 'Dropped table supply_chain';
    END IF;
END $$;

-- ingredients_backup_20240430 table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'ingredients_backup_20240430') THEN
        DROP TABLE public.ingredients_backup_20240430;
        RAISE NOTICE 'Dropped table ingredients_backup_20240430';
    END IF;
END $$;

-- product_ingredients_backup_20240430 table
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_ingredients_backup_20240430') THEN
        DROP TABLE public.product_ingredients_backup_20240430;
        RAISE NOTICE 'Dropped table product_ingredients_backup_20240430';
    END IF;
END $$;

-- Step 4: Verification checks
DO $$
DECLARE
    tables_to_check TEXT[] := ARRAY[
        'ingredients_backup_20240430',
        'price_history',
        'product_alternatives',
        'product_errors',
        'product_ingredients_backup_20240430',
        'product_nutrition',
        'supply_chain'
    ];
    table_exists BOOLEAN;
    current_table TEXT;
BEGIN
    RAISE NOTICE 'Performing verification checks...';
    
    FOREACH current_table IN ARRAY tables_to_check
    LOOP
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = current_table
        ) INTO table_exists;
        
        IF table_exists THEN
            RAISE WARNING 'Table % still exists after removal attempt!', current_table;
        ELSE
            RAISE NOTICE 'Verified: Table % successfully removed', current_table;
        END IF;
    END LOOP;
END $$;

-- Step 5: Document removed tables in schema comments
COMMENT ON SCHEMA public IS 'Tables removed on 2024-05-15: ingredients_backup_20240430, price_history, product_alternatives, product_errors, product_ingredients_backup_20240430, product_nutrition, supply_chain';

COMMIT; 