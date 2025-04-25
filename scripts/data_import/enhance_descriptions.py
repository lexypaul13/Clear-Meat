"""Enhance product descriptions using web search and caching.

This script:
1. Groups similar products to minimize redundant searches
2. Implements aggressive caching of web search and AI results
3. Batches updates to minimize database operations
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class DescriptionEnhancer:
    def __init__(self):
        self.conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Setup database extensions and tables
        self._setup_database()
    
    def _setup_database(self):
        """Set up necessary database extensions and tables."""
        try:
            # Enable pg_trgm extension
            self.cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            self.conn.commit()
        except psycopg2.Error as e:
            print("Warning: Could not create pg_trgm extension. Some similarity functions may not work.")
            print(f"Error: {e}")
            self.conn.rollback()
        
        # Create cache table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS description_cache (
                query_hash TEXT PRIMARY KEY,
                query_data JSONB,          -- Original query parameters
                search_results JSONB,      -- Cached web search results
                generated_description TEXT, -- Final description
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE,
                source TEXT,               -- 'web_search', 'similar_product', etc.
                confidence_score FLOAT      -- How confident we are in this description
            );
            
            CREATE INDEX IF NOT EXISTS idx_description_cache_expires 
            ON description_cache(expires_at);
            
            CREATE INDEX IF NOT EXISTS idx_description_cache_product_text 
            ON description_cache USING GIN ((query_data->>'product_text') gin_trgm_ops);
        """)
        self.conn.commit()

    def _get_products_needing_enhancement(self):
        """Get products that need description enhancement."""
        query = """
            SELECT id, name, brand, description, meat_type
            FROM products
            WHERE enhanced_description IS NULL
            OR description_enhanced_at < NOW() - INTERVAL '30 days'
            ORDER BY meat_type, brand NULLS LAST, name;
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def _get_cached_description(self, product_id):
        """Check if we have a cached description for this product."""
        query = """
            SELECT enhanced_description, confidence_score
            FROM description_cache
            WHERE product_id = %s
            AND expires_at > NOW();
        """
        self.cursor.execute(query, (product_id,))
        return self.cursor.fetchone()

    def _cache_description(self, product_id, product_data, enhanced_description, confidence_score):
        """Store the enhanced description in cache."""
        query = """
            INSERT INTO description_cache 
            (product_id, meat_type, brand, name, original_description, 
             enhanced_description, confidence_score, web_sources)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id) 
            DO UPDATE SET
                enhanced_description = EXCLUDED.enhanced_description,
                confidence_score = EXCLUDED.confidence_score,
                web_sources = EXCLUDED.web_sources,
                expires_at = CURRENT_TIMESTAMP + INTERVAL '30 days';
        """
        web_sources = json.dumps({'pending': True})  # Placeholder for actual web search results
        self.cursor.execute(query, (
            product_id,
            product_data[4],  # meat_type
            product_data[2],  # brand
            product_data[1],  # name
            product_data[3],  # original description
            enhanced_description,
            confidence_score,
            web_sources
        ))
        self.conn.commit()

    def _update_product_description(self, product_id, enhanced_description, confidence_score):
        """Update the product with enhanced description."""
        query = """
            UPDATE products 
            SET enhanced_description = %s,
                description_confidence = %s
            WHERE id = %s;
        """
        self.cursor.execute(query, (enhanced_description, confidence_score, product_id))
        self.conn.commit()

    def enhance_descriptions(self):
        """Main method to enhance product descriptions."""
        products = self._get_products_needing_enhancement()
        
        # Group products by meat type for efficient processing
        meat_type_groups = {}
        for product in products:
            meat_type = product[4]  # meat_type is at index 4
            if meat_type not in meat_type_groups:
                meat_type_groups[meat_type] = []
            meat_type_groups[meat_type].append(product)

        # Process each meat type group
        for meat_type, products in meat_type_groups.items():
            print(f"\nProcessing {len(products)} {meat_type} products:")
            
            # Create output file for this meat type
            output_file = f"data/descriptions_{meat_type.lower()}.json"
            products_data = []
            
            for product in products:
                product_id, name, brand, description, _ = product
                current_desc_len = len(description or '')
                
                # Check cache first
                cached = self._get_cached_description(product_id)
                if cached:
                    enhanced_description, confidence = cached
                    print(f"Cache hit for {name} (Confidence: {confidence:.2f})")
                    self._update_product_description(product_id, enhanced_description, confidence)
                    continue

                print(f"- {name} (Barcode: {product_id})")
                print(f"  Brand: {brand or 'Unknown'}")
                print(f"  Current description length: {current_desc_len}")
                print("  No cache hit - will process with AI")
                
                # Store product data for AI processing
                products_data.append({
                    'id': product_id,
                    'name': name,
                    'brand': brand,
                    'description': description,
                    'meat_type': meat_type
                })

            # Save products needing AI processing to file
            if products_data:
                os.makedirs('data', exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(products_data, f, indent=2)
                print(f"\nSaved {len(products_data)} products to {output_file}")

    def close(self):
        """Close database connection."""
        self.cursor.close()
        self.conn.close()

def main():
    enhancer = DescriptionEnhancer()
    try:
        enhancer.enhance_descriptions()
    finally:
        enhancer.close()

if __name__ == "__main__":
    main() 