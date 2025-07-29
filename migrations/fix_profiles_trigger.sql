-- Fix the profiles table trigger that references 'last_updated' instead of 'updated_at'
-- Based on the actual table structure: id, email, full_name, created_at, updated_at, preferences

-- Drop any existing problematic triggers
DROP TRIGGER IF EXISTS update_profiles_updated_at ON profiles;
DROP TRIGGER IF EXISTS update_profiles_last_updated ON profiles;

-- Check what triggers currently exist on the profiles table
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE event_object_table = 'profiles';

-- Create the correct trigger function that references the actual field 'updated_at'
CREATE OR REPLACE FUNCTION update_profiles_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    -- The actual field is 'updated_at' not 'last_updated'
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger with the correct function
CREATE TRIGGER profiles_update_timestamp
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_profiles_timestamp();