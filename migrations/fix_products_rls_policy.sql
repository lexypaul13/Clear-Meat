-- Fix RLS policy for products table to allow INSERT operations
-- This is needed for the OpenFoodFacts auto-add functionality

-- Check if the policy already exists to avoid errors
DO $$
BEGIN
    -- Drop existing policies if they exist (to recreate with correct permissions)
    IF EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'products' 
        AND policyname = 'Service role can insert products'
    ) THEN
        DROP POLICY "Service role can insert products" ON products;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'products' 
        AND policyname = 'Authenticated users can insert products'
    ) THEN
        DROP POLICY "Authenticated users can insert products" ON products;
    END IF;
END $$;

-- Create policy to allow service role to insert products
-- This is needed for auto-adding products from OpenFoodFacts
CREATE POLICY "Service role can insert products"
    ON products FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Create policy to allow authenticated users to insert products as fallback
-- This ensures the auto-add functionality works even if service role auth fails
CREATE POLICY "Authenticated users can insert products"
    ON products FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Grant INSERT permission to authenticated users on products table
GRANT INSERT ON products TO authenticated;
GRANT INSERT ON products TO service_role;

-- Log the fix
DO $$
BEGIN
    RAISE NOTICE 'Fixed products table RLS policies for INSERT operations';
    RAISE NOTICE 'Service role and authenticated users can now insert products';
    RAISE NOTICE 'This enables OpenFoodFacts auto-add functionality';
END $$;