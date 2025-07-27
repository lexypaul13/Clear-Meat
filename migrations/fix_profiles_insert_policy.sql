-- Fix RLS policy for profiles table to allow INSERT operations during registration
-- This is needed for user registration to work properly

-- Check if the policy already exists to avoid errors
DO $$
BEGIN
    -- Drop existing policies if they exist (to recreate with correct permissions)
    IF EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'profiles' 
        AND policyname = 'Service role can insert profiles'
    ) THEN
        DROP POLICY "Service role can insert profiles" ON profiles;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE schemaname = 'public' 
        AND tablename = 'profiles' 
        AND policyname = 'Users can insert their own profile during signup'
    ) THEN
        DROP POLICY "Users can insert their own profile during signup" ON profiles;
    END IF;
END $$;

-- Create policy to allow service role to insert profiles
-- This is needed for admin registration operations
CREATE POLICY "Service role can insert profiles"
    ON profiles FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Create policy to allow users to insert their own profile during signup
-- This ensures users can create their profile after auth signup
CREATE POLICY "Users can insert their own profile during signup"
    ON profiles FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = id);

-- Grant INSERT permission to authenticated users on profiles table
GRANT INSERT ON profiles TO authenticated;
GRANT INSERT ON profiles TO service_role;

-- Log the fix
DO $$
BEGIN
    RAISE NOTICE 'Fixed profiles table RLS policies for INSERT operations';
    RAISE NOTICE 'Service role and authenticated users can now insert profiles during registration';
END $$; 