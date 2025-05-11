-- MeatWise PostgreSQL Schema for Local Development

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Products table
CREATE TABLE products (
    code TEXT PRIMARY KEY, -- Barcode as primary key
    name TEXT NOT NULL,
    brand TEXT,
    description TEXT,
    ingredients_text TEXT, -- Raw ingredients text
    ingredients_array TEXT[], -- Parsed ingredients as array
    
    -- Nutritional information
    calories FLOAT,
    protein FLOAT,
    fat FLOAT,
    carbohydrates FLOAT,
    salt FLOAT,
    
    -- Meat-specific information
    meat_type TEXT,
    
    -- Additives and criteria
    contains_nitrites BOOLEAN DEFAULT FALSE,
    contains_phosphates BOOLEAN DEFAULT FALSE,
    contains_preservatives BOOLEAN DEFAULT FALSE,
    
    -- Animal welfare criteria
    antibiotic_free BOOLEAN,
    hormone_free BOOLEAN,
    pasture_raised BOOLEAN,
    
    -- Risk rating (Green, Yellow, Red)
    risk_rating TEXT CHECK (risk_rating IN ('Green', 'Yellow', 'Red')),
    risk_score INTEGER, -- Numerical score for sorting
    
    -- Additional fields
    image_url TEXT,
    image_data TEXT,
    source TEXT DEFAULT 'openfoodfacts', -- Data source
    
    -- Metadata
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX products_meat_type_idx ON products(meat_type);
CREATE INDEX products_risk_rating_idx ON products(risk_rating);
CREATE INDEX products_name_idx ON products USING GIN (to_tsvector('english', name));

-- Create function to update the 'updated_at' field
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update 'last_updated'
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 