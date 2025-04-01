#!/usr/bin/env python
"""
Mock Data Cleanup Script
-----------------------------
This script removes all mock data from the database by deleting products
with codes that start with 'mock_' and their associated ingredients.

Purpose:
- Use this script to clean up any mock data that was accidentally generated
- Ensures the database only contains real product data from OpenFoodFacts
- Optimizes database by removing unused ingredients after mock product deletion

Usage:
- Run this script after purging mock data: python scripts/cleanup_mock_data.py
- Check results with verify_data.py to confirm all mock data was removed
"""

import os
import asyncio
import asyncpg
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mock_data_cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def cleanup_mock_data():
    """Clean up mock data from the database"""
    # Load environment variables
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    
    # Connect to database
    logger.info("Connecting to database")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Start a transaction
        async with conn.transaction():
            # Count mock products before deletion
            mock_count = await conn.fetchval(
                "SELECT COUNT(*) FROM products WHERE code LIKE 'mock_%'"
            )
            logger.info(f"Found {mock_count} mock products to delete")
            
            # Remove product_ingredients entries first (foreign key constraint)
            removed_relations = await conn.execute(
                """
                DELETE FROM product_ingredients 
                WHERE product_code LIKE 'mock_%'
                """
            )
            logger.info(f"Removed product-ingredient relationships for mock products")
            
            # Remove mock products
            removed_products = await conn.execute(
                """
                DELETE FROM products 
                WHERE code LIKE 'mock_%'
                """
            )
            logger.info(f"Removed mock products")
            
            # Clean up orphaned ingredients
            removed_ingredients = await conn.execute(
                """
                DELETE FROM ingredients 
                WHERE id NOT IN (
                    SELECT DISTINCT ingredient_id FROM product_ingredients
                )
                """
            )
            logger.info(f"Cleaned up orphaned ingredients")
            
            # Get final counts
            product_count = await conn.fetchval("SELECT COUNT(*) FROM products")
            ingredient_count = await conn.fetchval("SELECT COUNT(*) FROM ingredients")
            relation_count = await conn.fetchval("SELECT COUNT(*) FROM product_ingredients")
            
            logger.info("Mock data cleanup complete")
            logger.info(f"Remaining products: {product_count}")
            logger.info(f"Remaining ingredients: {ingredient_count}")
            logger.info(f"Remaining product-ingredient relations: {relation_count}")
            
    except Exception as e:
        logger.error(f"Error cleaning up mock data: {str(e)}")
    finally:
        await conn.close()
        logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(cleanup_mock_data()) 