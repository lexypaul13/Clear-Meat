-- Performance Optimizations Migration
-- Addresses slow queries identified in pg_stat_statements analysis

-- =====================================================
-- 1. TIMEZONE QUERIES OPTIMIZATION
-- =====================================================
-- Create a materialized view for timezone names to avoid repeated expensive queries
-- This addresses the 1649ms+ queries: SELECT name FROM pg_timezone_names

CREATE MATERIALIZED VIEW IF NOT EXISTS public.cached_timezone_names AS
SELECT name FROM pg_timezone_names
ORDER BY name;

-- Create index on the materialized view
CREATE INDEX IF NOT EXISTS idx_cached_timezone_names_name ON public.cached_timezone_names(name);

-- Create a function to refresh the timezone cache (run periodically)
CREATE OR REPLACE FUNCTION public.refresh_timezone_cache()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW public.cached_timezone_names;
END;
$$;

-- =====================================================
-- 2. PRODUCTS TABLE PERFORMANCE OPTIMIZATIONS
-- =====================================================
-- Add comprehensive indexes for the products table to speed up common queries

-- Index for meat_type filtering (used in recommendations)
CREATE INDEX IF NOT EXISTS idx_products_meat_type ON public.products(meat_type) WHERE meat_type IS NOT NULL;

-- Index for risk_rating filtering 
CREATE INDEX IF NOT EXISTS idx_products_risk_rating ON public.products(risk_rating) WHERE risk_rating IS NOT NULL;

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_products_meat_risk ON public.products(meat_type, risk_rating) 
WHERE meat_type IS NOT NULL AND risk_rating IS NOT NULL;

-- Index for ingredients_text filtering (used in recommendations)
CREATE INDEX IF NOT EXISTS idx_products_has_ingredients ON public.products(code) 
WHERE ingredients_text IS NOT NULL;

-- Index for pagination and ordering
CREATE INDEX IF NOT EXISTS idx_products_code_pagination ON public.products(code ASC NULLS LAST);

-- Partial index for products with complete data (optimization for health assessments)
CREATE INDEX IF NOT EXISTS idx_products_complete_data ON public.products(code, meat_type, risk_rating)
WHERE ingredients_text IS NOT NULL AND meat_type IS NOT NULL;

-- =====================================================
-- 3. STRING LENGTH OPTIMIZATION
-- =====================================================
-- Create a function to efficiently truncate text fields to avoid the expensive 
-- octet_length + case when operations seen in slow queries

CREATE OR REPLACE FUNCTION public.safe_truncate(
    input_text TEXT,
    max_length INTEGER DEFAULT 100,
    suffix TEXT DEFAULT '...'
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF input_text IS NULL THEN
        RETURN NULL;
    END IF;
    
    IF length(input_text) <= max_length THEN
        RETURN input_text;
    ELSE
        RETURN left(input_text, max_length - length(suffix)) || suffix;
    END IF;
END;
$$;

-- =====================================================
-- 4. QUERY PERFORMANCE MONITORING
-- =====================================================
-- Create a view to monitor query performance (requires pg_stat_statements)

CREATE OR REPLACE VIEW public.query_performance_monitor AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    (total_exec_time / sum(total_exec_time) OVER()) * 100 AS percent_total_time
FROM pg_stat_statements 
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;

-- =====================================================
-- 5. PRODUCTS TABLE STATISTICS UPDATE
-- =====================================================
-- Ensure PostgreSQL has up-to-date statistics for query planning

ANALYZE public.products;

-- =====================================================
-- 6. CONNECTION POOLING OPTIMIZATION
-- =====================================================
-- Set recommended PostgreSQL settings for better performance with PostgREST

-- Note: These would typically be set in postgresql.conf, but we can set them per session
-- Users should consider adding these to their Supabase project settings:

-- shared_preload_libraries = 'pg_stat_statements'
-- pg_stat_statements.track = all
-- pg_stat_statements.max = 10000

-- =====================================================
-- 7. API RESPONSE OPTIMIZATION
-- =====================================================
-- Create a optimized view for product listings to avoid complex case statements

CREATE OR REPLACE VIEW public.products_optimized AS
SELECT 
    code,
    safe_truncate(name, 100) as name,
    safe_truncate(brand, 50) as brand,
    safe_truncate(description, 200) as description,
    safe_truncate(ingredients_text, 500) as ingredients_text,
    calories,
    protein,
    fat,
    carbohydrates,
    salt,
    meat_type,
    risk_rating,
    safe_truncate(image_url, 255) as image_url,
    last_updated,
    created_at,
    CASE 
        WHEN image_data IS NOT NULL THEN '[Binary Data]'
        ELSE NULL 
    END as image_data_summary
FROM public.products;

-- Create index on the view's underlying table for common access patterns
CREATE INDEX IF NOT EXISTS idx_products_optimized_filters ON public.products(meat_type, risk_rating, last_updated DESC);

-- =====================================================
-- 8. COMMENTS AND DOCUMENTATION
-- =====================================================

COMMENT ON MATERIALIZED VIEW public.cached_timezone_names IS 
'Cached timezone names to avoid expensive pg_timezone_names queries. Refresh periodically.';

COMMENT ON FUNCTION public.safe_truncate IS 
'Efficiently truncates text fields to avoid octet_length case when operations in API responses.';

COMMENT ON VIEW public.products_optimized IS 
'Optimized view for product listings with pre-truncated text fields to improve API response times.';

COMMENT ON FUNCTION public.refresh_timezone_cache IS 
'Refreshes the cached timezone names materialized view. Should be called periodically (e.g., daily).';

-- =====================================================
-- 9. GRANT PERMISSIONS
-- =====================================================

-- Grant appropriate permissions for the API user
GRANT SELECT ON public.cached_timezone_names TO anon, authenticated;
GRANT SELECT ON public.products_optimized TO anon, authenticated;
GRANT SELECT ON public.query_performance_monitor TO authenticated; -- Only for authenticated users

-- Grant execute permission on the safe_truncate function
GRANT EXECUTE ON FUNCTION public.safe_truncate TO anon, authenticated;
