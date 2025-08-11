-- Fix function search path security warnings
-- This migration sets explicit search_path for functions to prevent potential security issues

-- 1. Fix get_product_max_values function
CREATE OR REPLACE FUNCTION public.get_product_max_values()
RETURNS TABLE(
    max_calories numeric,
    max_protein numeric, 
    max_fat numeric,
    max_carbohydrates numeric,
    max_salt numeric
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(MAX(calories), 0) as max_calories,
        COALESCE(MAX(protein), 0) as max_protein,
        COALESCE(MAX(fat), 0) as max_fat,
        COALESCE(MAX(carbohydrates), 0) as max_carbohydrates,
        COALESCE(MAX(salt), 0) as max_salt
    FROM public.products
    WHERE calories IS NOT NULL 
       OR protein IS NOT NULL 
       OR fat IS NOT NULL 
       OR carbohydrates IS NOT NULL 
       OR salt IS NOT NULL;
END;
$$;

-- 2. Fix safe_truncate function
CREATE OR REPLACE FUNCTION public.safe_truncate(
    input_text text,
    max_length integer DEFAULT 255
)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
PARALLEL SAFE
SET search_path = public, pg_catalog
AS $$
BEGIN
    IF input_text IS NULL THEN
        RETURN NULL;
    END IF;
    
    IF length(input_text) <= max_length THEN
        RETURN input_text;
    END IF;
    
    -- Truncate and add ellipsis
    RETURN left(input_text, max_length - 3) || '...';
END;
$$;

-- 3. Fix update_updated_at_column function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- Maintain existing permissions
GRANT EXECUTE ON FUNCTION public.get_product_max_values() TO authenticated;
GRANT EXECUTE ON FUNCTION public.safe_truncate(text, integer) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO authenticated;

-- Add comments to document the security fix
COMMENT ON FUNCTION public.get_product_max_values() IS 'Returns maximum values for product attributes. Used for normalization. Fixed search_path for security.';
COMMENT ON FUNCTION public.safe_truncate(text, integer) IS 'Safely truncates text to specified length, adding ellipsis if needed. Fixed search_path for security.';
COMMENT ON FUNCTION public.update_updated_at_column() IS 'Trigger function to automatically update updated_at timestamp. Fixed search_path for security.';