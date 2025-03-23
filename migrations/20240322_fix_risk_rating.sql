-- Drop existing constraint
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_risk_rating_check;

-- Add new constraint that includes 'unknown' using array syntax
ALTER TABLE products 
    ADD CONSTRAINT products_risk_rating_check 
    CHECK (risk_rating = ANY (ARRAY['Green', 'Yellow', 'Red', 'unknown'])); 