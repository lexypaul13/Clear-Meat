-- Migration to add a function that returns maximum values for product attributes
-- This is used for normalizing values in the weighted scoring algorithm

-- Create function to get maximum values of protein, fat, and salt
CREATE OR REPLACE FUNCTION get_product_max_values()
RETURNS JSON AS $$
DECLARE
    max_protein FLOAT;
    max_fat FLOAT;
    max_salt FLOAT;
    result JSON;
BEGIN
    -- Get maximum protein value
    SELECT MAX(protein) INTO max_protein FROM products WHERE protein IS NOT NULL;
    
    -- Get maximum fat value
    SELECT MAX(fat) INTO max_fat FROM products WHERE fat IS NOT NULL;
    
    -- Get maximum salt value
    SELECT MAX(salt) INTO max_salt FROM products WHERE salt IS NOT NULL;
    
    -- Ensure we don't have nulls or zeros (fallback to reasonable values)
    IF max_protein IS NULL OR max_protein = 0 THEN
        max_protein := 100;
    END IF;
    
    IF max_fat IS NULL OR max_fat = 0 THEN
        max_fat := 100;
    END IF;
    
    IF max_salt IS NULL OR max_salt = 0 THEN
        max_salt := 100;
    END IF;
    
    -- Create JSON result
    result := json_build_object(
        'max_protein', max_protein,
        'max_fat', max_fat,
        'max_salt', max_salt
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Create function to execute dynamic SQL queries
-- This allows us to run the weighted scoring query from the application
CREATE OR REPLACE FUNCTION execute_sql(sql_query TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    -- Execute the query and get results as JSON
    EXECUTE 'SELECT array_to_json(array_agg(row_to_json(t))) FROM (' || sql_query || ') t' INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql; 