-- Enable RLS on all tables
ALTER TABLE public.product_ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_alternatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_analysis_cache ENABLE ROW LEVEL SECURITY;

-- Create policies for product_ingredients
CREATE POLICY "Enable read access for authenticated users" ON public.product_ingredients
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable write access for authenticated users" ON public.product_ingredients
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Create policies for product_alternatives
CREATE POLICY "Enable read access for authenticated users" ON public.product_alternatives
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable write access for authenticated users" ON public.product_alternatives
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Create policies for ai_analysis_cache
CREATE POLICY "Enable read access for authenticated users" ON public.ai_analysis_cache
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Enable write access for authenticated users" ON public.ai_analysis_cache
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Grant appropriate permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.product_ingredients TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.product_alternatives TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.ai_analysis_cache TO authenticated; 