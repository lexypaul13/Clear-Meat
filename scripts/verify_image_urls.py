#!/usr/bin/env python
"""
Verify Image URLs Script
-----------------------
This script verifies and fixes image URLs in the database by checking them
and updating them with valid URLs from the OpenFoodFacts API.

Usage: python scripts/verify_image_urls.py [limit]
  where [limit] is the maximum number of products to check (default: 500)
"""

import os
import asyncio
import aiohttp
import logging
import json
import sys
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
import time
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_verification.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ImageUrlVerifier:
    """Verifies and updates image URLs in the database"""
    
    def __init__(self, target_count=500, batch_size=20):
        """Initialize the verifier with target count and batch size"""
        self.target_count = target_count
        self.batch_size = batch_size
        self.verified_count = 0
        self.updated_count = 0
        self.failed_count = 0
        self.start_time = datetime.now(timezone.utc)
        self.pool = None
        
        # Rate limiting parameters - respect OpenFoodFacts API limits
        self.requests_per_second = 2  # Maximum requests per second to API
        self.last_request_time = 0
    
    async def setup(self):
        """Set up database connection"""
        try:
            # Import here to avoid circular imports
            import asyncpg
            
            # Create database connection pool
            self.pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
            if not self.pool:
                logger.error("Failed to create database connection pool")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.pool:
                await self.pool.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    async def get_products_with_images(self, limit):
        """Get products that have image URLs"""
        try:
            async with self.pool.acquire() as conn:
                products = await conn.fetch("""
                    SELECT code, name, image_url FROM products 
                    WHERE image_url != '' AND image_url IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT $1
                """, limit)
                
                return products
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
    async def check_image_url(self, session, image_url):
        """Check if the image URL is valid"""
        try:
            # Implement rate limiting
            current_time = time.time()
            if current_time - self.last_request_time < 1/self.requests_per_second:
                await asyncio.sleep(1/self.requests_per_second - (current_time - self.last_request_time))
            
            self.last_request_time = time.time()
            
            # Try to GET the head of the URL
            async with session.head(image_url, allow_redirects=True, timeout=10) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if content_type.startswith('image/'):
                        return True, None
                    else:
                        return False, f"Invalid content type: {content_type}"
                else:
                    return False, f"Invalid status code: {response.status}"
        except aiohttp.ClientError as e:
            return False, f"Client error: {str(e)}"
        except asyncio.TimeoutError:
            return False, "Request timeout"
        except Exception as e:
            return False, f"Error checking URL: {str(e)}"
    
    async def fetch_product_data(self, session, product_code):
        """Fetch product data from OpenFoodFacts API"""
        # Implement rate limiting
        current_time = time.time()
        if current_time - self.last_request_time < 1/self.requests_per_second:
            await asyncio.sleep(1/self.requests_per_second - (current_time - self.last_request_time))
        
        self.last_request_time = time.time()
        
        url = f"https://world.openfoodfacts.org/api/v2/product/{product_code}.json"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 1:  # Status 1 means success
                        return data.get('product', {})
                    else:
                        logger.warning(f"API returned status {data.get('status')} for product {product_code}")
                elif response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', '60'))
                    logger.warning(f"Rate limited by API. Waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    # Retry the request after waiting
                    return await self.fetch_product_data(session, product_code)
                else:
                    logger.warning(f"Failed to fetch data for product {product_code}: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error fetching data for product {product_code}: {str(e)}")
        
        return None
    
    def extract_image_url(self, product_data, product_code):
        """Extract image URL from product data"""
        # Try various image URL formats
        image_url = ""
        
        # 1. Try direct image_url field
        if 'image_url' in product_data:
            image_url = product_data.get('image_url', '')
            
        # 2. Try front image URL
        elif 'image_front_url' in product_data:
            image_url = product_data.get('image_front_url', '')
            
        # 3. Try the image structure format
        elif 'images' in product_data:
            images = product_data.get('images', {})
            
            # Format the code with slashes
            formatted_code = '/'.join([product_code[i:i+3] for i in range(0, len(product_code), 3)])
            
            # Look for front image
            front_key = None
            for key in images.keys():
                if key.startswith('front'):
                    front_key = key
                    break
            
            if front_key:
                # Use language 'en' or extract from key
                lang = 'en'
                if '_' in front_key:
                    lang = front_key.split('_')[1]
                
                # Get revision if available
                if isinstance(images[front_key], dict) and 'rev' in images[front_key]:
                    rev = images[front_key]['rev']
                    image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/front_{lang}.{rev}.400.jpg"
                else:
                    # Try without revision
                    image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/front_{lang}.400.jpg"
            
            # If no front image, try alternative formats
            if not image_url and '1' in images:
                image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/1.400.jpg"
        
        # 4. If nothing worked, try the default format
        if not image_url:
            # Try some default variations
            formatted_code = '/'.join([product_code[i:i+3] for i in range(0, len(product_code), 3)])
            image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/front.400.jpg"
        
        return image_url
    
    async def update_product_image(self, conn, product_code, image_url):
        """Update product image URL in database"""
        try:
            await conn.execute("""
                UPDATE products 
                SET image_url = $1, last_updated = $2
                WHERE code = $3
            """, image_url, datetime.now(timezone.utc), product_code)
            
            return True
        except Exception as e:
            logger.error(f"Error updating image URL for product {product_code}: {str(e)}")
            return False
    
    async def process_product(self, session, conn, product):
        """Process a single product"""
        product_code = product['code']
        product_name = product['name']
        current_image_url = product['image_url']
        
        # Check if the current image URL is valid
        valid, error = await self.check_image_url(session, current_image_url)
        
        if valid:
            logger.debug(f"Image URL for {product_name} ({product_code}) is valid")
            self.verified_count += 1
            return True
        else:
            logger.info(f"Invalid image URL for {product_name} ({product_code}): {error}")
            
            # Fetch product data from API to get the correct image URL
            product_data = await self.fetch_product_data(session, product_code)
            
            if product_data:
                # Extract new image URL
                new_image_url = self.extract_image_url(product_data, product_code)
                
                if new_image_url and new_image_url != current_image_url:
                    # Verify the new image URL
                    new_valid, new_error = await self.check_image_url(session, new_image_url)
                    
                    if new_valid:
                        # Update product image URL
                        success = await self.update_product_image(conn, product_code, new_image_url)
                        if success:
                            self.updated_count += 1
                            logger.info(f"Updated image URL for {product_name} ({product_code}): {new_image_url}")
                            return True
                    else:
                        logger.warning(f"New image URL for {product_name} ({product_code}) is also invalid: {new_error}")
            
            self.failed_count += 1
            logger.warning(f"Failed to update image URL for {product_name} ({product_code})")
            return False
    
    async def process_batch(self, session, batch):
        """Process a batch of products"""
        async with self.pool.acquire() as conn:
            for product in batch:
                await self.process_product(session, conn, product)
    
    async def verify_images(self):
        """Verify and update image URLs"""
        try:
            logger.info(f"Starting image URL verification")
            logger.info(f"Target count: {self.target_count}")
            logger.info(f"Batch size: {self.batch_size}")
            
            # Fetch products with images
            products = await self.get_products_with_images(self.target_count)
            if not products:
                logger.info("No products found with image URLs")
                return
            
            logger.info(f"Found {len(products)} products with image URLs")
            
            # Configure connection pool and timeouts for aiohttp
            conn = aiohttp.TCPConnector(limit=10)
            timeout = aiohttp.ClientTimeout(total=3600, connect=30, sock_connect=30, sock_read=30)
            
            # Process products in batches
            async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                for i in range(0, len(products), self.batch_size):
                    batch = products[i:i+self.batch_size]
                    
                    # Process batch
                    start_batch = time.time()
                    await self.process_batch(session, batch)
                    batch_time = time.time() - start_batch
                    
                    # Log progress after each batch
                    batch_size = len(batch)
                    processed = i + batch_size
                    elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                    logger.info(f"Progress: {processed}/{len(products)} products")
                    logger.info(f"Verified: {self.verified_count}, Updated: {self.updated_count}, Failed: {self.failed_count}")
                    logger.info(f"Batch processing time: {batch_time:.2f}s, Total elapsed time: {elapsed:.2f}s")
                
            # Final statistics
            await self.log_statistics()
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
    
    def format_elapsed_time(self, seconds):
        """Format elapsed time in a human-readable way"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    async def log_statistics(self):
        """Log verification statistics"""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        formatted_time = self.format_elapsed_time(elapsed)
        
        logger.info("-" * 50)
        logger.info("IMAGE VERIFICATION STATISTICS")
        logger.info("-" * 50)
        logger.info(f"Total processed: {self.verified_count + self.updated_count + self.failed_count}")
        logger.info(f"URLs already valid: {self.verified_count}")
        logger.info(f"URLs updated: {self.updated_count}")
        logger.info(f"Failed updates: {self.failed_count}")
        logger.info(f"Elapsed time: {formatted_time}")
        if elapsed > 0:
            total_processed = self.verified_count + self.updated_count + self.failed_count
            if total_processed > 0:
                logger.info(f"Processing rate: {total_processed / elapsed:.2f} products/second")
                logger.info(f"Success rate: {(self.verified_count + self.updated_count) / total_processed:.2%}")
        logger.info("-" * 50)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Verify and update product image URLs")
    parser.add_argument("limit", nargs="?", type=int, default=500, help="Maximum number of products to verify")
    return parser.parse_args()

async def main():
    # Parse command line arguments
    args = parse_args()
    
    # Create verifier and run
    verifier = ImageUrlVerifier(args.limit)
    
    try:
        if not await verifier.setup():
            logger.error("Setup failed. Exiting.")
            return
            
        await verifier.verify_images()
    finally:
        await verifier.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 