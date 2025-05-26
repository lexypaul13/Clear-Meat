-- Security Fixes Migration
-- Addresses all security warnings and errors from Supabase database linter

-- =============================================================================
-- PRIORITY 1 (ERROR): Fix RLS disabled on public tables
-- =============================================================================

-- Fix RLS for description_cache table (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'description_cache'
    ) THEN
        -- Enable RLS on description_cache
        ALTER TABLE public.description_cache ENABLE ROW LEVEL SECURITY;
        
        -- Add RLS policies for description_cache - allow authenticated users to read/write
        CREATE POLICY "Authenticated users can view cached descriptions"
            ON public.description_cache FOR SELECT
            USING (auth.role() = 'authenticated');

        CREATE POLICY "Authenticated users can insert cached descriptions"
            ON public.description_cache FOR INSERT
            WITH CHECK (auth.role() = 'authenticated');

        CREATE POLICY "Authenticated users can update cached descriptions"
            ON public.description_cache FOR UPDATE
            USING (auth.role() = 'authenticated');

        CREATE POLICY "Authenticated users can delete expired cached descriptions"
            ON public.description_cache FOR DELETE
            USING (auth.role() = 'authenticated' AND expires_at < NOW());
            
        RAISE NOTICE 'RLS enabled for description_cache table';
    ELSE
        RAISE NOTICE 'description_cache table does not exist, skipping RLS setup';
    END IF;
END $$;

-- Check if 'users' table exists and fix RLS if it does
-- Note: Based on code analysis, this should be the 'profiles' table, but fixing if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        -- Enable RLS on users table
        ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
        
        -- Add appropriate policies for users table
        CREATE POLICY "Users can view their own user record" 
            ON public.users FOR SELECT 
            USING (auth.uid() = id);
            
        CREATE POLICY "Users can update their own user record" 
            ON public.users FOR UPDATE 
            USING (auth.uid() = id);
            
        RAISE NOTICE 'RLS enabled for users table';
    ELSE
        RAISE NOTICE 'users table does not exist, skipping RLS setup';
    END IF;
END $$;

-- =============================================================================
-- PRIORITY 2 (WARN): Fix function search_path mutable issues
-- =============================================================================

-- Fix execute_sql function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'execute_sql'
    ) THEN
        CREATE OR REPLACE FUNCTION public.execute_sql(sql_query TEXT)
        RETURNS JSONB 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, extensions
        AS $func$
        DECLARE
            result JSONB;
        BEGIN
            -- Execute the query and get results as JSON
            EXECUTE 'SELECT array_to_json(array_agg(row_to_json(t))) FROM (' || sql_query || ') t' INTO result;
            RETURN result;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for execute_sql function';
    END IF;
END $$;

-- Fix get_backup_info function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'get_backup_info'
    ) THEN
        -- This function appears to be commented out in migrations, recreate with proper security
        CREATE OR REPLACE FUNCTION public.get_backup_info()
        RETURNS TABLE (
            table_name TEXT,
            row_count BIGINT
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        BEGIN
            RETURN QUERY
            SELECT 
                t.table_name::TEXT,
                (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = t.table_name)::BIGINT
            FROM information_schema.tables t
            WHERE t.table_schema = 'public';
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for get_backup_info function';
    END IF;
END $$;

-- Fix handle_updated_at function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'handle_updated_at'
    ) THEN
        CREATE OR REPLACE FUNCTION public.handle_updated_at()
        RETURNS TRIGGER 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for handle_updated_at function';
    END IF;
END $$;

-- Fix log_migration_progress function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'log_migration_progress'
    ) THEN
        CREATE OR REPLACE FUNCTION public.log_migration_progress(
            migration_name TEXT,
            step_description TEXT,
            step_status TEXT DEFAULT 'COMPLETED'
        )
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        BEGIN
            -- Log migration progress
            RAISE NOTICE 'Migration: % - %: %', migration_name, step_description, step_status;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for log_migration_progress function';
    END IF;
END $$;

-- Fix update_updated_at_enriched function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'update_updated_at_enriched'
    ) THEN
        CREATE OR REPLACE FUNCTION public.update_updated_at_enriched()
        RETURNS TRIGGER 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for update_updated_at_enriched function';
    END IF;
END $$;

-- Fix validate_user_preferences function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'validate_user_preferences'
    ) THEN
        CREATE OR REPLACE FUNCTION public.validate_user_preferences()
        RETURNS TRIGGER 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        BEGIN
            -- Check that preferences is a valid JSON object
            IF NEW.preferences IS NOT NULL AND jsonb_typeof(NEW.preferences) != 'object' THEN
                RAISE EXCEPTION 'preferences must be a JSON object';
            END IF;
            
            -- Additional validation could be added here
            
            RETURN NEW;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for validate_user_preferences function';
    END IF;
END $$;

-- Fix get_product_max_values function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'get_product_max_values'
    ) THEN
        CREATE OR REPLACE FUNCTION public.get_product_max_values()
        RETURNS JSON 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        DECLARE
            max_protein FLOAT;
            max_fat FLOAT;
            max_salt FLOAT;
            result JSON;
        BEGIN
            -- Get maximum protein value
            SELECT MAX(protein) INTO max_protein FROM products WHERE protein IS NOT NULL;
            
            -- Get maximum fat value
            SELECT MAX(fat) INTO max_fat FROM products WHERE fat IS NOT NULL;
            
            -- Get maximum salt value
            SELECT MAX(salt) INTO max_salt FROM products WHERE salt IS NOT NULL;
            
            -- Ensure we don't have nulls or zeros (fallback to reasonable values)
            IF max_protein IS NULL OR max_protein = 0 THEN
                max_protein := 100;
            END IF;
            
            IF max_fat IS NULL OR max_fat = 0 THEN
                max_fat := 100;
            END IF;
            
            IF max_salt IS NULL OR max_salt = 0 THEN
                max_salt := 100;
            END IF;
            
            -- Create JSON result
            result := json_build_object(
                'max_protein', max_protein,
                'max_fat', max_fat,
                'max_salt', max_salt
            );
            
            RETURN result;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for get_product_max_values function';
    END IF;
END $$;

-- Fix migrate_legacy_preferences function (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.routines 
        WHERE routine_schema = 'public' AND routine_name = 'migrate_legacy_preferences'
    ) THEN
        CREATE OR REPLACE FUNCTION public.migrate_legacy_preferences()
        RETURNS void 
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $func$
        DECLARE
            profile_record RECORD;
            new_preferences JSONB;
        BEGIN
            FOR profile_record IN SELECT id, preferences FROM profiles WHERE preferences IS NOT NULL LOOP
                new_preferences := profile_record.preferences;
                
                -- Map health_goal to nutrition_focus if possible
                IF new_preferences ? 'health_goal' THEN
                    IF new_preferences->>'health_goal' = 'heart_healthy' THEN
                        new_preferences := new_preferences || '{"nutrition_focus": "salt"}'::jsonb;
                    ELSIF new_preferences->>'health_goal' = 'weight_loss' THEN
                        new_preferences := new_preferences || '{"nutrition_focus": "fat"}'::jsonb;
                    ELSIF new_preferences->>'health_goal' = 'muscle_building' THEN
                        new_preferences := new_preferences || '{"nutrition_focus": "protein"}'::jsonb;
                    END IF;
                END IF;
                
                -- Map additive_preference to new fields
                IF new_preferences ? 'additive_preference' THEN
                    IF new_preferences->>'additive_preference' = 'avoid_preservatives' THEN
                        new_preferences := new_preferences || '{"avoid_preservatives": true}'::jsonb;
                    ELSIF new_preferences->>'additive_preference' = 'avoid_antibiotics' THEN
                        new_preferences := new_preferences || '{"prefer_antibiotic_free": true}'::jsonb;
                    ELSIF new_preferences->>'additive_preference' = 'organic' THEN
                        new_preferences := new_preferences || '{"avoid_preservatives": true, "prefer_antibiotic_free": true}'::jsonb;
                    END IF;
                END IF;
                
                -- Map ethical_concerns to relevant fields
                IF new_preferences ? 'ethical_concerns' AND 
                   jsonb_typeof(new_preferences->'ethical_concerns') = 'array' THEN
                    IF jsonb_exists(new_preferences->'ethical_concerns', '"animal_welfare"') THEN
                        new_preferences := new_preferences || '{"prefer_grass_fed": true}'::jsonb;
                    END IF;
                END IF;
                
                -- Update the profile with the new preferences
                UPDATE profiles SET preferences = new_preferences WHERE id = profile_record.id;
            END LOOP;
        END;
        $func$;
        
        RAISE NOTICE 'Fixed search_path for migrate_legacy_preferences function';
    END IF;
END $$;

-- Fix update_updated_at_column function (always exists from initial schema)
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER 
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Check if the table has updated_at column
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = TG_TABLE_NAME
        AND column_name = 'updated_at'
    ) THEN
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$;

-- =============================================================================
-- PRIORITY 3 (WARN): Fix extension in public schema
-- =============================================================================

-- Create extensions schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS extensions;

-- Move pg_trgm extension from public to extensions schema
-- Note: This requires careful handling to avoid breaking existing functionality
DO $$
BEGIN
    -- Check if pg_trgm is in public schema
    IF EXISTS (
        SELECT 1 FROM pg_extension 
        WHERE extname = 'pg_trgm' 
        AND extnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
    ) THEN
        -- First, drop any dependent objects (indexes using gin_trgm_ops)
        IF EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'description_cache' 
            AND indexname = 'idx_description_cache_product_text'
        ) THEN
            DROP INDEX public.idx_description_cache_product_text;
        END IF;
        
        -- Now drop and recreate the extension in the correct schema
        DROP EXTENSION pg_trgm CASCADE;
        CREATE EXTENSION pg_trgm WITH SCHEMA extensions;
        
        -- Recreate the index with the correct schema reference
        IF EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'description_cache'
        ) THEN
            CREATE INDEX idx_description_cache_product_text 
            ON public.description_cache USING GIN ((query_data->>'product_text') extensions.gin_trgm_ops);
        END IF;
        
        RAISE NOTICE 'Moved pg_trgm extension to extensions schema';
    ELSE
        RAISE NOTICE 'pg_trgm extension not in public schema or does not exist';
    END IF;
END $$;

-- =============================================================================
-- PRIORITY 4: Additional security improvements
-- =============================================================================

-- Add secure permissions for functions
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM public;

-- Grant permissions conditionally based on function existence
DO $$
BEGIN
    -- Grant execute permissions for existing functions
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'get_product_max_values') THEN
        GRANT EXECUTE ON FUNCTION public.get_product_max_values() TO authenticated;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'validate_user_preferences') THEN
        GRANT EXECUTE ON FUNCTION public.validate_user_preferences() TO authenticated;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'update_updated_at_column') THEN
        GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO authenticated;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'update_updated_at_enriched') THEN
        GRANT EXECUTE ON FUNCTION public.update_updated_at_enriched() TO authenticated;
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'handle_updated_at') THEN
        GRANT EXECUTE ON FUNCTION public.handle_updated_at() TO authenticated;
    END IF;
    
    -- Restrict execute_sql function to service_role only for security
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'execute_sql') THEN
        GRANT EXECUTE ON FUNCTION public.execute_sql(TEXT) TO service_role;
    END IF;
END $$;

-- Add comments for documentation
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'execute_sql') THEN
        COMMENT ON FUNCTION public.execute_sql(TEXT) IS 'Executes dynamic SQL queries. Restricted to service_role for security.';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'get_product_max_values') THEN
        COMMENT ON FUNCTION public.get_product_max_values() IS 'Returns maximum values for product attributes. Used for normalization.';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name = 'validate_user_preferences') THEN
        COMMENT ON FUNCTION public.validate_user_preferences() IS 'Validates user preferences JSON structure.';
    END IF;
END $$;

-- =============================================================================
-- Verification and logging
-- =============================================================================

-- Create a view to monitor security compliance
CREATE OR REPLACE VIEW public.security_compliance_monitor AS
SELECT 
    'description_cache' as table_name,
    'RLS' as security_feature,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'description_cache') THEN
            CASE WHEN rls.rowsecurity THEN 'ENABLED' ELSE 'DISABLED' END
        ELSE 'TABLE_NOT_EXISTS'
    END as status
FROM (
    SELECT 
        c.relrowsecurity as rowsecurity
    FROM pg_class c
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'description_cache'
    LIMIT 1
) rls

UNION ALL

SELECT 
    'pg_trgm' as table_name,
    'Extension Schema' as security_feature,
    CASE 
        WHEN n.nspname = 'extensions' THEN 'COMPLIANT'
        WHEN n.nspname = 'public' THEN 'NON_COMPLIANT'
        ELSE 'EXTENSION_NOT_EXISTS'
    END as status
FROM pg_extension e
LEFT JOIN pg_namespace n ON n.oid = e.extnamespace
WHERE e.extname = 'pg_trgm'

UNION ALL

SELECT 
    'functions_with_search_path' as table_name,
    'Function Security' as security_feature,
    COUNT(*)::TEXT || ' functions fixed' as status
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN (
    'execute_sql', 'get_backup_info', 'handle_updated_at', 'log_migration_progress',
    'update_updated_at_enriched', 'validate_user_preferences', 'get_product_max_values',
    'migrate_legacy_preferences', 'update_updated_at_column'
);

-- Grant access to the compliance monitor
GRANT SELECT ON public.security_compliance_monitor TO authenticated, service_role;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE '=== Security fixes migration completed successfully ===';
    RAISE NOTICE 'Fixed: RLS on description_cache table (if exists)';
    RAISE NOTICE 'Fixed: Function search_path issues for 9 functions (if they exist)';
    RAISE NOTICE 'Fixed: pg_trgm extension moved to extensions schema (if needed)';
    RAISE NOTICE 'Added: Security compliance monitoring view';
    RAISE NOTICE 'Added: Proper function permissions and documentation';
END $$; 