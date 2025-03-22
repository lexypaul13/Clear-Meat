-- First, drop the existing function
DROP FUNCTION IF EXISTS public.update_updated_at_column();

-- Create extensions schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS extensions;

-- Move vector extension to extensions schema
DROP EXTENSION IF EXISTS vector;
CREATE EXTENSION vector WITH SCHEMA extensions;

-- Recreate the function with a fixed search path
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Grant execute permission to public (since it's used by triggers)
GRANT EXECUTE ON FUNCTION public.update_updated_at_column() TO public;

-- Recreate triggers (in case they were dropped)
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_ingredients_updated_at ON ingredients;
CREATE TRIGGER update_ingredients_updated_at
    BEFORE UPDATE ON ingredients
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column(); 