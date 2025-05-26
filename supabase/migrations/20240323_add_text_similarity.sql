-- Enable pg_trgm extension for text similarity functions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create description cache table
CREATE TABLE IF NOT EXISTS description_cache (
    query_hash TEXT PRIMARY KEY,
    query_data JSONB,          -- Original query parameters
    search_results JSONB,      -- Cached web search results
    generated_description TEXT, -- Final description
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    source TEXT,               -- 'web_search', 'similar_product', etc.
    confidence_score FLOAT     -- How confident we are in this description
);

-- Create index for expiration checks
CREATE INDEX IF NOT EXISTS idx_description_cache_expires 
ON description_cache(expires_at);

-- Create trigram index on query_data for similarity searches
CREATE INDEX IF NOT EXISTS idx_description_cache_product_text 
ON description_cache USING GIN ((query_data->>'product_text') gin_trgm_ops); 