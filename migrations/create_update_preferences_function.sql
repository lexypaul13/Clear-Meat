-- Create a function to update user preferences that bypasses the problematic trigger
CREATE OR REPLACE FUNCTION update_user_preferences(
    user_id UUID,
    new_preferences JSONB
)
RETURNS JSONB AS $$
DECLARE
    updated_record RECORD;
BEGIN
    -- Directly update the preferences column
    UPDATE profiles
    SET preferences = new_preferences,
        updated_at = NOW()
    WHERE id = user_id
    RETURNING * INTO updated_record;
    
    -- Return the updated preferences
    RETURN updated_record.preferences;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION update_user_preferences(UUID, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION update_user_preferences(UUID, JSONB) TO service_role;