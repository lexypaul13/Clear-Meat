import asyncio
import aiohttp
import asyncpg
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    exit(1)

async def check_image_url(session: aiohttp.ClientSession, url: str) -> tuple[bool, str]:
    """Check if an image URL is still valid and accessible."""
    try:
        async with session.head(url, allow_redirects=True, timeout=10) as response:
            if response.status != 200:
                return False, f"HTTP status {response.status}"
                
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return False, f"Not an image: {content_type}"
                
            content_length = response.headers.get('content-length')
            if content_length:
                size_kb = int(content_length) / 1024
                return True, f"Valid image ({size_kb:.1f}KB, {content_type})"
            else:
                return True, f"Valid image (size unknown, {content_type})"
                
    except asyncio.TimeoutError:
        return False, "Timeout error"
    except Exception as e:
        return False, f"Error: {str(e)}"

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
            # Get products with image data
            products = await conn.fetch("""
                SELECT code, name, brand, image_url, length(image_data) as stored_size
                FROM products 
                WHERE image_data IS NOT NULL
                ORDER BY last_updated DESC
            """)
            
            if not products:
                print("\nNo products found with image data.")
                return
                
            print("\nChecking image URLs...")
            print("-" * 80)
            
            async with aiohttp.ClientSession() as session:
                for product in products:
                    code = product['code']
                    name = product['name']
                    brand = product['brand']
                    url = product['image_url']
                    stored_size = product['stored_size']
                    
                    print(f"\nProduct: {name} ({brand})")
                    print(f"Code: {code}")
                    print(f"Stored image size: {stored_size / 1024:.1f}KB")
                    print(f"URL: {url}")
                    
                    is_valid, status = await check_image_url(session, url)
                    if is_valid:
                        print(f"Status: ✅ {status}")
                    else:
                        print(f"Status: ❌ {status}")
                    
                    print("-" * 80)
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main()) 