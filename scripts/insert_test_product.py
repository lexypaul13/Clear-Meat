#!/usr/bin/env python
"""
Insert Test Product
------------------
This script inserts a test product with a known code that has images in OpenFoodFacts.

Usage: python scripts/insert_test_product.py
"""

import os
import asyncio
import asyncpg
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def insert_test_product():
    """Insert a test product with known image in OpenFoodFacts"""
    conn = None
    try:
        # Connect to the database
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        
        # Insert the test product
        await conn.execute("""
            INSERT INTO products (
                code, name, brand, description, ingredients_text, 
                image_url, source, meat_type, risk_rating, 
                last_updated, created_at
            ) VALUES (
                '737628064502', 
                'Thai Peanut Noodle Kit', 
                'Simply Asia', 
                'Thai peanut noodle kit includes stir-fry rice noodles & thai peanut seasoning', 
                'Rice Noodles (rice, water), seasoning packet (peanut, sugar, salt, corn starch, spices)', 
                '', 
                'OpenFoodFacts', 
                'chicken', 
                'Yellow', 
                $1, 
                $1
            ) ON CONFLICT (code) DO UPDATE SET 
                image_url = '', 
                last_updated = $1
        """, datetime.now(timezone.utc))
        
        # Get the product to verify
        product = await conn.fetchrow("""
            SELECT code, name, image_url FROM products 
            WHERE code = '737628064502'
        """)
        
        if product:
            print(f"Test product inserted/updated: {product['code']} - {product['name']}")
            print(f"Current image URL: {product['image_url']}")
            return True
        else:
            print("Failed to insert/update test product")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    finally:
        if conn:
            await conn.close()

async def main():
    success = await insert_test_product()
    if success:
        print("\nNow run the update script:")
        print("python scripts/update_product_images.py 1")

if __name__ == "__main__":
    asyncio.run(main()) 