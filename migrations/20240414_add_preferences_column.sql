-- Add preferences column to profiles table
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS preferences JSONB;

-- Add personalized_insights column to scan_history table
ALTER TABLE scan_history ADD COLUMN IF NOT EXISTS personalized_insights JSONB;

-- Add comments
COMMENT ON COLUMN profiles.preferences IS 'User preferences from onboarding questionnaire';
COMMENT ON COLUMN scan_history.personalized_insights IS 'Personalized insights based on user preferences';

-- Update triggers to include new columns
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql; 