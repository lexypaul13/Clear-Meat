import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import logging

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

async def main():
    # Create connection pool
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=1
        )
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        exit(1)
    
    try:
        async with pool.acquire() as conn:
            # Get total count
            total_count = await conn.fetchval("SELECT COUNT(*) FROM products")
            print(f"\nTotal number of products: {total_count}")
            
            # Get count of products with scraped images
            with_images = await conn.fetchval("SELECT COUNT(*) FROM products WHERE image_data IS NOT NULL")
            print(f"Products with scraped images: {with_images}")
            
            # Get count of products without scraped images
            without_images = await conn.fetchval("SELECT COUNT(*) FROM products WHERE image_data IS NULL")
            print(f"Products without scraped images: {without_images}\n")
            
            # Show details of products with image data
            print("Products with image data:")
            print("-" * 80)
            products_with_images = await conn.fetch("""
                SELECT code, name, brand, 
                       length(image_data) as image_data_length,
                       image_url,
                       last_updated
                FROM products 
                WHERE image_data IS NOT NULL
                ORDER BY last_updated DESC
            """)
            
            if products_with_images:
                for product in products_with_images:
                    print(f"Code: {product['code']}")
                    print(f"Name: {product['name']}")
                    print(f"Brand: {product['brand']}")
                    print(f"Image data size: {product['image_data_length']} bytes")
                    print(f"Image URL: {product['image_url']}")
                    print(f"Last updated: {product['last_updated']}")
                    print("-" * 80)
            else:
                print("No products found with actual image data.")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main()) 