-- FINAL RLS POLICY FIX for profiles table
-- This addresses the authentication issue preventing user profile creation

-- First, disable RLS temporarily to clean up
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;

-- Drop ALL existing policies to start completely clean
DROP POLICY IF EXISTS "profiles_select_own" ON profiles;
DROP POLICY IF EXISTS "profiles_insert_own" ON profiles; 
DROP POLICY IF EXISTS "profiles_update_own" ON profiles;
DROP POLICY IF EXISTS "profiles_service_role_all" ON profiles;
DROP POLICY IF EXISTS "Users can view their own profile" ON profiles;
DROP POLICY IF EXISTS "Users can update their own profile" ON profiles;
DROP POLICY IF EXISTS "Service role can insert profiles" ON profiles;
DROP POLICY IF EXISTS "Users can insert their own profile during signup" ON profiles;
DROP POLICY IF EXISTS "Enable insert for authenticated users based on user_id" ON profiles;
DROP POLICY IF EXISTS "Enable read access for users based on user_id" ON profiles;
DROP POLICY IF EXISTS "Enable update for users based on user_id" ON profiles;

-- Re-enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Create comprehensive policies with clear names

-- 1. Allow authenticated users to read their own profile
CREATE POLICY "authenticated_users_select_own_profile" ON profiles
    FOR SELECT 
    TO authenticated
    USING (auth.uid() = id);

-- 2. Allow authenticated users to insert their own profile (CRITICAL for signup)
CREATE POLICY "authenticated_users_insert_own_profile" ON profiles
    FOR INSERT 
    TO authenticated
    WITH CHECK (auth.uid() = id);

-- 3. Allow authenticated users to update their own profile
CREATE POLICY "authenticated_users_update_own_profile" ON profiles
    FOR UPDATE 
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- 4. Allow service role full access for admin operations
CREATE POLICY "service_role_full_access_profiles" ON profiles
    FOR ALL 
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Grant necessary table permissions
GRANT SELECT ON profiles TO authenticated;
GRANT INSERT ON profiles TO authenticated;
GRANT UPDATE ON profiles TO authenticated;
GRANT DELETE ON profiles TO authenticated;

-- Grant full access to service role
GRANT ALL ON profiles TO service_role;

-- Verify policies were created correctly
SELECT 
    schemaname, 
    tablename, 
    policyname, 
    roles, 
    cmd,
    permissive
FROM pg_policies 
WHERE tablename = 'profiles'
ORDER BY policyname; 