#!/usr/bin/env python
"""
Update Product Images
--------------------
This script updates image URLs for existing products by fetching data from the OpenFoodFacts API.

Usage: python scripts/update_product_images.py [limit] [--resume]
  where [limit] is the maximum number of products to update (default: 1000)
  [--resume] optional flag to resume from last processed product
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
        logging.FileHandler('image_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ProductImageUpdater:
    """Updates product image URLs from OpenFoodFacts API"""
    
    def __init__(self, target_count=1000, batch_size=20, resume=False):
        """Initialize the updater with a target count and batch size"""
        self.target_count = target_count
        self.batch_size = batch_size
        self.parallel_requests = 10  # Number of concurrent API requests
        self.updated_count = 0
        self.processed_count = 0
        self.failed_count = 0
        self.start_time = datetime.now(timezone.utc)
        self.pool = None
        self.resume = resume
        self.progress_file = "image_update_progress.json"
        self.last_processed_id = None
        
        # Rate limiting parameters - respect OpenFoodFacts API limits
        self.requests_per_second = 2  # Maximum requests per second to API
        self.last_request_time = 0
    
    async def setup(self):
        """Set up database connection and load progress if resuming"""
        try:
            # Import here to avoid circular imports
            import asyncpg
            
            # Create database connection pool
            self.pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
            if not self.pool:
                logger.error("Failed to create database connection pool")
                return False
            
            # Load progress if resuming
            if self.resume and os.path.exists(self.progress_file):
                try:
                    with open(self.progress_file, 'r') as f:
                        progress = json.load(f)
                        self.last_processed_id = progress.get('last_id')
                        self.processed_count = progress.get('processed_count', 0)
                        self.updated_count = progress.get('updated_count', 0)
                        self.failed_count = progress.get('failed_count', 0)
                        logger.info(f"Resuming from product ID {self.last_processed_id}")
                        logger.info(f"Progress so far: processed {self.processed_count}, updated {self.updated_count}, failed {self.failed_count}")
                except Exception as e:
                    logger.error(f"Error loading progress file: {str(e)}")
                    # Continue without resuming
                    self.resume = False
                
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
    
    async def get_products_without_images(self, limit):
        """Get products without image URLs"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT id, code, name FROM products 
                    WHERE image_url = '' OR image_url IS NULL
                """
                
                # Add condition for resuming if needed
                params = []
                if self.resume and self.last_processed_id:
                    query += " AND id > $1"
                    params.append(self.last_processed_id)
                
                # Add ordering and limit
                query += " ORDER BY id LIMIT $" + str(len(params) + 1)
                params.append(limit)
                
                products = await conn.fetch(query, *params)
                
                return products
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
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
    
    async def update_product_image(self, conn, product_id, product_code, image_url):
        """Update product image URL in database"""
        try:
            await conn.execute("""
                UPDATE products 
                SET image_url = $1, last_updated = $2
                WHERE code = $3
            """, image_url, datetime.now(timezone.utc), product_code)
            
            # Save progress after each update
            await self.save_progress(product_id)
            
            return True
        except Exception as e:
            logger.error(f"Error updating image URL for product {product_code}: {str(e)}")
            return False
    
    async def save_progress(self, last_id):
        """Save progress to file for resume capability"""
        try:
            progress = {
                'last_id': last_id,
                'processed_count': self.processed_count,
                'updated_count': self.updated_count,
                'failed_count': self.failed_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f)
        except Exception as e:
            logger.error(f"Error saving progress: {str(e)}")
    
    async def process_product(self, session, conn, product):
        """Process a single product"""
        product_id = product['id']
        product_code = product['code']
        product_name = product['name']
        
        # Fetch product data from API
        product_data = await self.fetch_product_data(session, product_code)
        
        if product_data:
            # Try to extract image URL using various fields
            image_url = ""
            
            # First try the direct image_url or image_front_url fields
            if 'image_url' in product_data:
                image_url = product_data.get('image_url', '')
            elif 'image_front_url' in product_data:
                image_url = product_data.get('image_front_url', '')
            # Then try the front_thumb_url fields
            elif 'image_front_thumb_url' in product_data:
                # Replace thumb with medium size
                image_url = product_data.get('image_front_thumb_url', '').replace('.100.', '.400.')
            # If we still don't have an image but we have the images structure
            elif 'images' in product_data:
                images = product_data.get('images', {})
                # Format the barcode with slashes (every 3 digits)
                code = product_code
                # Add leading zeros if needed to ensure groups of 3
                while len(code) % 3 != 0:
                    code = '0' + code
                formatted_code = '/'.join([code[i:i+3] for i in range(0, len(code), 3)])
                
                # Look for front image
                front_key = None
                # First check if there's a front image key
                for key in images.keys():
                    if key.startswith('front'):
                        front_key = key
                        break
                
                if front_key:
                    # Try to get language and revision
                    lang = 'en'
                    if '_' in front_key:
                        lang = front_key.split('_')[1]
                    
                    if isinstance(images[front_key], dict) and 'rev' in images[front_key]:
                        rev = images[front_key]['rev']
                        image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/front_{lang}.{rev}.400.jpg"
                    else:
                        # Use a default version if no specific revision found
                        image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/front_{lang}.1.400.jpg"
                # If no front image, use the first available image
                elif '1' in images:
                    image_url = f"https://images.openfoodfacts.org/images/products/{formatted_code}/1.400.jpg"
            
            if image_url:
                # Update product image URL
                success = await self.update_product_image(conn, product_id, product_code, image_url)
                if success:
                    self.updated_count += 1
                    logger.info(f"Updated image URL for {product_name} ({product_code}): {image_url}")
                    return True
                else:
                    self.failed_count += 1
                    return False
            else:
                logger.warning(f"No image URL found for {product_name} ({product_code})")
                self.failed_count += 1
                return False
        else:
            logger.warning(f"Failed to fetch data for {product_name} ({product_code})")
            self.failed_count += 1
            return False
    
    async def process_batch(self, session, batch):
        """Process a batch of products"""
        async with self.pool.acquire() as conn:
            tasks = []
            for product in batch:
                self.processed_count += 1
                tasks.append(self.process_product(session, conn, product))
            
            # Execute tasks and collect results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing product: {str(result)}")
                    self.failed_count += 1
    
    async def update_images(self):
        """Update product image URLs"""
        try:
            logger.info(f"Starting image URL updates")
            logger.info(f"Target count: {self.target_count}")
            logger.info(f"Batch size: {self.batch_size}")
            logger.info(f"Parallel requests: {self.parallel_requests}")
            
            # Fetch products without images
            products = await self.get_products_without_images(self.target_count)
            if not products:
                logger.info("No products found without image URLs")
                return
            
            logger.info(f"Found {len(products)} products without image URLs")
            
            # Configure connection pool and timeouts for aiohttp
            conn = aiohttp.TCPConnector(limit=self.parallel_requests)
            timeout = aiohttp.ClientTimeout(total=3600, connect=60, sock_connect=60, sock_read=60)
            
            # Process products in batches
            async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
                for i in range(0, len(products), self.batch_size):
                    batch = products[i:i+self.batch_size]
                    
                    # Process batch with rate limiting
                    start_batch = time.time()
                    await self.process_batch(session, batch)
                    batch_time = time.time() - start_batch
                    
                    # Log progress after each batch
                    elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                    logger.info(f"Progress: {self.processed_count}/{len(products)} products")
                    logger.info(f"Updated: {self.updated_count}, Failed: {self.failed_count}")
                    logger.info(f"Batch processing time: {batch_time:.2f}s, Total elapsed time: {elapsed:.2f}s")
                    
                    # Save last processed ID
                    if batch:
                        await self.save_progress(batch[-1]['id'])
                    
                    # Check if we've processed enough products
                    if self.processed_count >= self.target_count:
                        logger.info(f"Reached target count of {self.target_count} processed products")
                        break
                
            # Final statistics
            await self.log_statistics()
            
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
    
    def format_elapsed_time(self, seconds):
        """Format elapsed time in a human-readable way"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    async def log_statistics(self):
        """Log update statistics"""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        formatted_time = self.format_elapsed_time(elapsed)
        
        logger.info("-" * 50)
        logger.info("IMAGE UPDATE STATISTICS")
        logger.info("-" * 50)
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Products updated: {self.updated_count}")
        logger.info(f"Failed updates: {self.failed_count}")
        logger.info(f"Elapsed time: {formatted_time}")
        if elapsed > 0:
            logger.info(f"Processing rate: {self.processed_count / elapsed:.2f} products/second")
            if self.updated_count > 0:
                logger.info(f"Success rate: {self.updated_count / self.processed_count:.2%}")
        logger.info("-" * 50)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Update product image URLs from OpenFoodFacts API")
    parser.add_argument("limit", nargs="?", type=int, default=1000, help="Maximum number of products to update")
    parser.add_argument("--resume", action="store_true", help="Resume from last processed product")
    return parser.parse_args()

async def main():
    # Parse command line arguments
    args = parse_args()
    
    # Create updater and run
    updater = ProductImageUpdater(args.limit, batch_size=20, resume=args.resume)
    
    try:
        if not await updater.setup():
            logger.error("Setup failed. Exiting.")
            return
            
        await updater.update_images()
    finally:
        await updater.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 