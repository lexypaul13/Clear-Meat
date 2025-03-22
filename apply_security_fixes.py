import psycopg2
import os

# SQL statements for security fixes
sql_statements = """
-- First, drop the existing triggers
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
DROP TRIGGER IF EXISTS update_ingredients_updated_at ON ingredients;
DROP TRIGGER IF EXISTS update_products_updated_at ON products;

-- Then drop the function
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

-- Recreate triggers
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_ingredients_updated_at
    BEFORE UPDATE ON ingredients
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();
"""

# Connect to the database
conn = psycopg2.connect("postgresql://postgres.szswmlkhirkmozwvhpnc:qvCRDhRRfcaNWnVh@aws-0-us-east-1.pooler.supabase.com:5432/postgres")
conn.autocommit = True

try:
    with conn.cursor() as cur:
        cur.execute(sql_statements)
        print("Successfully applied security fixes!")
except Exception as e:
    print(f"Error applying security fixes: {str(e)}")
finally:
    conn.close() 