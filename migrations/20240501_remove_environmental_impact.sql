-- Migration: Remove environmental_impact table
-- Date: 2024-05-01

BEGIN;

-- Step 1: Check table existence before attempting operations
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    RAISE NOTICE 'Starting environmental_impact table removal verification...';
    
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'environmental_impact'
    ) INTO table_exists;
    
    IF table_exists THEN
        RAISE NOTICE 'Table environmental_impact exists and will be removed';
    ELSE
        RAISE NOTICE 'Table environmental_impact does not exist, skipping removal';
    END IF;
END $$;

-- Step 2: Drop foreign key constraints first
DO $$
DECLARE
    constraint_record RECORD;
BEGIN
    -- Find and drop all foreign key constraints pointing to the environmental_impact table
    FOR constraint_record IN
        SELECT tc.table_schema, tc.constraint_name, tc.table_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
            ON tc.constraint_catalog = ccu.constraint_catalog 
            AND tc.constraint_schema = ccu.constraint_schema
            AND tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND (
            ccu.table_name = 'environmental_impact' 
            OR tc.table_name = 'environmental_impact'
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

-- Step 3: Drop environmental_impact table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'environmental_impact') THEN
        DROP TABLE public.environmental_impact;
        RAISE NOTICE 'Dropped table environmental_impact';
    END IF;
END $$;

-- Step 4: Verification check
DO $$
DECLARE
    table_exists BOOLEAN;
BEGIN
    RAISE NOTICE 'Performing verification check...';
    
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'environmental_impact'
    ) INTO table_exists;
    
    IF table_exists THEN
        RAISE WARNING 'Table environmental_impact still exists after removal attempt!';
    ELSE
        RAISE NOTICE 'Verified: Table environmental_impact successfully removed';
    END IF;
END $$;

COMMIT; 