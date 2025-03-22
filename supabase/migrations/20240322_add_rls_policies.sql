-- Enable RLS for product_ingredients table
ALTER TABLE product_ingredients ENABLE ROW LEVEL SECURITY;

-- Create policy for product_ingredients
CREATE POLICY "Product ingredients are viewable by everyone"
    ON product_ingredients FOR SELECT
    USING (true);

-- Enable RLS for product_alternatives table
ALTER TABLE product_alternatives ENABLE ROW LEVEL SECURITY;

-- Create policy for product_alternatives
CREATE POLICY "Product alternatives are viewable by everyone"
    ON product_alternatives FOR SELECT
    USING (true);

-- Enable RLS for ai_analysis_cache table
ALTER TABLE ai_analysis_cache ENABLE ROW LEVEL SECURITY;

-- Create policy for ai_analysis_cache
-- Only authenticated users can view cached results
CREATE POLICY "Authenticated users can view cached results"
    ON ai_analysis_cache FOR SELECT
    USING (auth.role() = 'authenticated');

-- Only service role can insert/update cache entries
CREATE POLICY "Service role can manage cache entries"
    ON ai_analysis_cache FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role'); 