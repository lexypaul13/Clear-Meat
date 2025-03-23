-- Add new fields to products table for enhanced meat product tracking
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS processing_method TEXT,
    ADD COLUMN IF NOT EXISTS shelf_stability TEXT CHECK (shelf_stability IN ('refrigerated', 'shelf-stable')),
    ADD COLUMN IF NOT EXISTS sodium_mg FLOAT;

-- Add comment to explain meat_type field usage
COMMENT ON COLUMN products.meat_type IS 'Specifies the type of meat (e.g., beef, pork, chicken, turkey) and can include processing type (e.g., ground, whole muscle)';

-- Create index for processing method to optimize queries
CREATE INDEX IF NOT EXISTS products_processing_method_idx ON products(processing_method); 