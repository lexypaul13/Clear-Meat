-- Performance optimization indexes for Clear-Meat API
-- Created: 2024-03-24

-- Index for meat_type filtering (very common in searches)
CREATE INDEX IF NOT EXISTS idx_products_meat_type 
ON products(meat_type) 
WHERE meat_type IS NOT NULL;

-- Index for risk_rating filtering
CREATE INDEX IF NOT EXISTS idx_products_risk_rating 
ON products(risk_rating) 
WHERE risk_rating IS NOT NULL;

-- Composite index for common search patterns
CREATE INDEX IF NOT EXISTS idx_products_meat_type_risk 
ON products(meat_type, risk_rating) 
WHERE meat_type IS NOT NULL AND risk_rating IS NOT NULL;

-- Index for brand searches (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_products_brand_lower 
ON products(LOWER(brand)) 
WHERE brand IS NOT NULL;

-- Index for product name searches (trigram for partial matches)
CREATE INDEX IF NOT EXISTS idx_products_name_trgm 
ON products USING GIN (name gin_trgm_ops);

-- Index for ingredient text searches
CREATE INDEX IF NOT EXISTS idx_products_ingredients_trgm 
ON products USING GIN (ingredients_text gin_trgm_ops) 
WHERE ingredients_text IS NOT NULL;

-- Indexes for nutritional queries
CREATE INDEX IF NOT EXISTS idx_products_protein 
ON products(protein) 
WHERE protein IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_salt 
ON products(salt) 
WHERE salt IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_products_fat 
ON products(fat) 
WHERE fat IS NOT NULL;

-- Composite index for nutritional range queries
CREATE INDEX IF NOT EXISTS idx_products_nutrition_composite 
ON products(protein, salt, fat) 
WHERE protein IS NOT NULL AND salt IS NOT NULL AND fat IS NOT NULL;

-- Index for created_at (for recent products)
CREATE INDEX IF NOT EXISTS idx_products_created_at 
ON products(created_at DESC);

-- Index for barcode lookups (should be unique but adding for performance)
CREATE INDEX IF NOT EXISTS idx_products_code 
ON products(code) 
WHERE code IS NOT NULL;

-- Partial indexes for common filters using code as primary key
CREATE INDEX IF NOT EXISTS idx_products_organic 
ON products(code) 
WHERE LOWER(name) LIKE '%organic%' OR LOWER(description) LIKE '%organic%';

CREATE INDEX IF NOT EXISTS idx_products_grass_fed 
ON products(code) 
WHERE LOWER(description) LIKE '%grass%fed%' OR LOWER(description) LIKE '%grass-fed%';

-- Update table statistics for query planner
ANALYZE products; 