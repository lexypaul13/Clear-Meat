-- Direct SQL to fix function search paths
-- Run this in Supabase SQL Editor

-- First, let's check current function definitions
SELECT proname, prosrc, proconfig 
FROM pg_proc 
WHERE proname IN ('get_product_max_values', 'safe_truncate', 'update_updated_at_column')
AND pronamespace = 'public'::regnamespace;

-- Now let's ALTER the functions to add search_path
ALTER FUNCTION public.get_product_max_values() SET search_path = public, pg_catalog;
ALTER FUNCTION public.safe_truncate(text, integer) SET search_path = public, pg_catalog;
ALTER FUNCTION public.update_updated_at_column() SET search_path = public, pg_catalog;

-- Verify the changes
SELECT 
    routine_name,
    routine_definition,
    external_language,
    routine_body,
    parameter_default
FROM information_schema.routines
WHERE routine_schema = 'public' 
AND routine_name IN ('get_product_max_values', 'safe_truncate', 'update_updated_at_column');

-- Also check using pg_proc
SELECT proname, proconfig 
FROM pg_proc 
WHERE proname IN ('get_product_max_values', 'safe_truncate', 'update_updated_at_column')
AND pronamespace = 'public'::regnamespace;