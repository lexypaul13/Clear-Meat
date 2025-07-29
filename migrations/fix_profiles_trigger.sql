-- Fix the profiles table trigger that references 'last_updated' instead of 'updated_at'
-- This is causing the "record 'new' has no field 'last_updated'" error

-- First, drop the existing trigger if it exists
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;

-- Create or replace the function to use the correct field name
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Use the correct field name 'updated_at' instead of 'last_updated'
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate the trigger
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Test that the trigger works
-- UPDATE profiles SET preferences = '{"test": true}'::jsonb WHERE id = (SELECT id FROM profiles LIMIT 1);