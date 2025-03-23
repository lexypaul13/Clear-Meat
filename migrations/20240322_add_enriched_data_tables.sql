-- Detailed nutritional information
CREATE TABLE IF NOT EXISTS product_nutrition (
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    serving_size TEXT,
    serving_unit TEXT,
    vitamins JSONB,  -- Store detailed vitamin content
    minerals JSONB,  -- Store detailed mineral content
    allergens TEXT[],
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (product_code)
);

-- Environmental impact data
CREATE TABLE IF NOT EXISTS environmental_impact (
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    carbon_footprint_per_kg FLOAT,
    water_usage_liters_per_kg FLOAT,
    land_use_sqm_per_kg FLOAT,
    packaging_recyclable BOOLEAN,
    source TEXT,  -- Source of the environmental data
    calculation_method TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (product_code)
);

-- Price tracking
CREATE TABLE IF NOT EXISTS price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    price FLOAT,
    currency TEXT,
    store TEXT,
    region TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    unit TEXT,  -- e.g., 'per_kg', 'per_pound', 'per_package'
    quantity FLOAT  -- Amount in the package
);

-- Supply chain information
CREATE TABLE IF NOT EXISTS supply_chain (
    product_code TEXT REFERENCES products(code) ON DELETE CASCADE,
    origin_country TEXT,
    processing_location TEXT,
    distribution_method TEXT,
    storage_requirements TEXT,
    shelf_life_days INTEGER,
    certifications TEXT[],
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (product_code)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_product_nutrition_updated ON product_nutrition(updated_at);
CREATE INDEX IF NOT EXISTS idx_environmental_impact_updated ON environmental_impact(updated_at);
CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_code);
CREATE INDEX IF NOT EXISTS idx_supply_chain_origin ON supply_chain(origin_country);

-- Add triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_enriched()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_product_nutrition_updated_at
    BEFORE UPDATE ON product_nutrition
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_enriched();

CREATE TRIGGER update_environmental_impact_updated_at
    BEFORE UPDATE ON environmental_impact
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_enriched();

CREATE TRIGGER update_supply_chain_updated_at
    BEFORE UPDATE ON supply_chain
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_enriched(); 