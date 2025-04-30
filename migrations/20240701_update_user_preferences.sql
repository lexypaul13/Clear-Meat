-- Migration to update user preferences structure
-- This migration ensures the database tables can handle the new user preferences
-- from the redesigned onboarding process

-- Note: Since we're using JSONB for preferences, we don't need to alter table structure
-- This migration is for documentation purposes and to add any necessary indexes

-- Add comment to profiles.preferences column to document the new structure
COMMENT ON COLUMN profiles.preferences IS 'User preferences including: 
- nutrition_focus (string: protein, fat, salt)
- avoid_preservatives (boolean)
- prefer_antibiotic_free (boolean)
- prefer_grass_fed (boolean)
- cooking_style (string: grilling, pan_frying, oven_slow_cooker)
- open_to_alternatives (boolean)';

-- Create GIN index for faster JSON queries on the preferences column
-- This helps when filtering users by specific preference values
CREATE INDEX IF NOT EXISTS idx_profiles_preferences_gin ON profiles USING GIN (preferences);

-- Create function to validate preferences structure (optional)
CREATE OR REPLACE FUNCTION validate_user_preferences()
RETURNS TRIGGER AS $$
BEGIN
  -- Check that preferences is a valid JSON object
  IF NEW.preferences IS NOT NULL AND jsonb_typeof(NEW.preferences) != 'object' THEN
    RAISE EXCEPTION 'preferences must be a JSON object';
  END IF;
  
  -- Additional validation could be added here
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to validate preferences on insert/update (optional)
DROP TRIGGER IF EXISTS validate_preferences_trigger ON profiles;
CREATE TRIGGER validate_preferences_trigger
  BEFORE INSERT OR UPDATE ON profiles
  FOR EACH ROW
  EXECUTE FUNCTION validate_user_preferences();

-- Add function to help migrate old preference format to new
CREATE OR REPLACE FUNCTION migrate_legacy_preferences()
RETURNS void AS $$
DECLARE
  profile_record RECORD;
  new_preferences JSONB;
BEGIN
  FOR profile_record IN SELECT id, preferences FROM profiles WHERE preferences IS NOT NULL LOOP
    new_preferences := profile_record.preferences;
    
    -- Map health_goal to nutrition_focus if possible
    IF new_preferences ? 'health_goal' THEN
      IF new_preferences->>'health_goal' = 'heart_healthy' THEN
        new_preferences := new_preferences || '{"nutrition_focus": "salt"}'::jsonb;
      ELSIF new_preferences->>'health_goal' = 'weight_loss' THEN
        new_preferences := new_preferences || '{"nutrition_focus": "fat"}'::jsonb;
      ELSIF new_preferences->>'health_goal' = 'muscle_building' THEN
        new_preferences := new_preferences || '{"nutrition_focus": "protein"}'::jsonb;
      END IF;
    END IF;
    
    -- Map additive_preference to new fields
    IF new_preferences ? 'additive_preference' THEN
      IF new_preferences->>'additive_preference' = 'avoid_preservatives' THEN
        new_preferences := new_preferences || '{"avoid_preservatives": true}'::jsonb;
      ELSIF new_preferences->>'additive_preference' = 'avoid_antibiotics' THEN
        new_preferences := new_preferences || '{"prefer_antibiotic_free": true}'::jsonb;
      ELSIF new_preferences->>'additive_preference' = 'organic' THEN
        new_preferences := new_preferences || '{"avoid_preservatives": true, "prefer_antibiotic_free": true}'::jsonb;
      END IF;
    END IF;
    
    -- Map ethical_concerns to relevant fields
    IF new_preferences ? 'ethical_concerns' AND 
       jsonb_typeof(new_preferences->'ethical_concerns') = 'array' THEN
      IF jsonb_exists(new_preferences->'ethical_concerns', '"animal_welfare"') THEN
        new_preferences := new_preferences || '{"prefer_grass_fed": true}'::jsonb;
      END IF;
    END IF;
    
    -- Update the profile with the new preferences
    UPDATE profiles SET preferences = new_preferences WHERE id = profile_record.id;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Execute the migration function (uncomment to run)
-- SELECT migrate_legacy_preferences();
-- DROP FUNCTION migrate_legacy_preferences(); 