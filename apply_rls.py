import os
from dotenv import load_dotenv
import logging
import psycopg2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    exit(1)

# SQL statements for RLS policies
sql_statements = """
-- Enable RLS for products table
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Create policy for products
CREATE POLICY products_select_policy
ON products FOR SELECT
USING (true);

-- Note: The following tables have been removed as of 2024-05-15
-- product_alternatives
-- product_nutrition 
-- price_history
-- supply_chain
-- product_errors
-- ingredients_backup_20240430
-- product_ingredients_backup_20240430

-- Their RLS policies have been removed from this script

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
"""

def apply_rls():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql_statements)
            print("Successfully applied RLS policies!")
    except Exception as e:
        print(f"Error applying RLS policies: {str(e)}")
    finally:
        conn.close()

apply_rls() 