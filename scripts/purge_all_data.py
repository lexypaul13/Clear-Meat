import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_purge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def purge_all_data():
    """Purge all data from the database"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        
        logger.info("Starting complete data purge...")
        
        # Get initial counts
        total_products = await conn.fetchval("SELECT COUNT(*) FROM products")
        total_ingredients = await conn.fetchval("SELECT COUNT(*) FROM ingredients")
        total_relationships = await conn.fetchval("SELECT COUNT(*) FROM product_ingredients")
        
        logger.info("Initial database state:")
        logger.info(f"- Products: {total_products}")
        logger.info(f"- Ingredients: {total_ingredients}")
        logger.info(f"- Ingredient relationships: {total_relationships}")
        
        # Delete all data
        await conn.execute("DELETE FROM product_ingredients")
        logger.info("Deleted all product-ingredient relationships")
        
        await conn.execute("DELETE FROM ingredients")
        logger.info("Deleted all ingredients")
        
        await conn.execute("DELETE FROM products")
        logger.info("Deleted all products")
        
        # Verify deletion
        remaining_products = await conn.fetchval("SELECT COUNT(*) FROM products")
        remaining_ingredients = await conn.fetchval("SELECT COUNT(*) FROM ingredients")
        remaining_relationships = await conn.fetchval("SELECT COUNT(*) FROM product_ingredients")
        
        logger.info("\nFinal database state:")
        logger.info(f"- Products: {remaining_products}")
        logger.info(f"- Ingredients: {remaining_ingredients}")
        logger.info(f"- Ingredient relationships: {remaining_relationships}")
        
        await conn.close()
        logger.info("Database connection closed")
        
    except Exception as e:
        logger.error(f"Error during data purge: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(purge_all_data()) 