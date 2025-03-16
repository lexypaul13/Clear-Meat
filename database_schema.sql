-- MeatWise PostgreSQL Schema for Supabase

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector"; -- For AI similarity searches later

-- Users table (extends Supabase auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    preferences JSONB DEFAULT '{}'::jsonb -- Store user preferences as JSON
);

-- Ingredients table
CREATE TABLE ingredients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT, -- e.g., preservative, color, flavor, etc.
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'unknown')),
    concerns TEXT[], -- Array of potential health concerns
    alternatives TEXT[], -- Array of healthier alternatives
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on ingredient name for faster lookups
CREATE INDEX ingredients_name_idx ON ingredients USING GIN (to_tsvector('english', name));

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
    source TEXT DEFAULT 'openfoodfacts', -- Data source
    
    -- Metadata
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX products_meat_type_idx ON products(meat_type);
CREATE INDEX products_risk_rating_idx ON products(risk_rating);
CREATE INDEX products_name_idx ON products USING GIN (to_tsvector('english', name));

-- Product-Ingredient relationship table
CREATE TABLE product_ingredients (
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    ingredient_id UUID REFERENCES ingredients(id) ON DELETE CASCADE,
    position INTEGER, -- Position in the ingredients list
    PRIMARY KEY (product_code, ingredient_id)
);

-- Scan history table
CREATE TABLE scan_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    product_code TEXT REFERENCES products(code) ON DELETE SET NULL,
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    location JSONB, -- Optional location data
    device_info TEXT -- Optional device information
);

-- Create index on user_id for faster user history lookups
CREATE INDEX scan_history_user_id_idx ON scan_history(user_id);

-- Alternative product suggestions
CREATE TABLE product_alternatives (
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    alternative_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    similarity_score FLOAT, -- How similar the products are
    reason TEXT, -- Why this is a better alternative
    PRIMARY KEY (product_code, alternative_code)
);

-- User favorites
CREATE TABLE user_favorites (
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    PRIMARY KEY (user_id, product_code)
);

-- AI analysis cache (for storing results of AI processing)
CREATE TABLE ai_analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_hash TEXT UNIQUE NOT NULL, -- Hash of the query parameters
    result JSONB NOT NULL, -- Cached result
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE -- When this cache entry expires
);

-- Create index on query_hash for faster lookups
CREATE INDEX ai_analysis_cache_query_hash_idx ON ai_analysis_cache(query_hash);

-- Row Level Security Policies

-- Profiles: Users can only read/write their own profile
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Scan History: Users can only access their own scan history
ALTER TABLE scan_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own scan history"
    ON scan_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own scan history"
    ON scan_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- User Favorites: Users can only access their own favorites
ALTER TABLE user_favorites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own favorites"
    ON user_favorites FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own favorites"
    ON user_favorites FOR ALL
    USING (auth.uid() = user_id);

-- Products and Ingredients are publicly readable
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Products are viewable by everyone"
    ON products FOR SELECT
    USING (true);

CREATE POLICY "Ingredients are viewable by everyone"
    ON ingredients FOR SELECT
    USING (true);

-- Create function to update the 'updated_at' field
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update 'updated_at'
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ingredients_updated_at
    BEFORE UPDATE ON ingredients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 