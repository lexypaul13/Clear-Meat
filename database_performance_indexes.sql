-- Critical Performance Indexes for Clear-Meat Database
-- Run these to dramatically improve query performance

-- 1. Product search indexes (most common queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_meat_type_risk ON products(meat_type, risk_rating);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_code ON products(code);

-- 2. Full-text search for ingredients and product info
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_search_gin ON products 
USING gin(to_tsvector('english', 
  coalesce(name, '') || ' ' || 
  coalesce(brand, '') || ' ' || 
  coalesce(ingredients_text, '')
));

-- 3. Nutrition-based filtering (for health recommendations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_nutrition ON products(protein DESC, fat ASC, salt ASC) 
WHERE protein IS NOT NULL AND fat IS NOT NULL AND salt IS NOT NULL;

-- 4. Health assessment caching lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_updated_at ON products(last_updated DESC);

-- 5. Ingredients text for fast searching
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_ingredients ON products USING gin(ingredients_text gin_trgm_ops);

-- 6. Brand and name searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_name_brand ON products(name, brand);

-- Add search vector column for ultra-fast text search
ALTER TABLE products ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Update existing products with search vectors
UPDATE products SET search_vector = 
  setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
  setweight(to_tsvector('english', coalesce(brand, '')), 'B') ||
  setweight(to_tsvector('english', coalesce(ingredients_text, '')), 'D');

-- Create index on search vector
CREATE INDEX CONCURRENTLY idx_products_search_vector ON products USING gin(search_vector);

-- Auto-update search vector trigger
CREATE OR REPLACE FUNCTION update_product_search_vector() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := 
    setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.brand, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.ingredients_text, '')), 'D');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_search_vector 
  BEFORE INSERT OR UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION update_product_search_vector();