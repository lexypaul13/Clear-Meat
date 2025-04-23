#!/usr/bin/env python
"""
Scrape Product Images
--------------------
This script scrapes product images directly from websites without using MCP.
It will retrieve images for products that are missing them in the database.

Usage: python scripts/scrape_product_images.py [--limit LIMIT] [--resume] [--demo]
  where LIMIT is the maximum number of products to process (default: 10)
  --resume: optional flag to resume from last processed product
  --demo: run in demo mode without database connection
"""

import os
import asyncio
import aiohttp
import logging
import json
import argparse
import time
import random
from datetime import datetime, timezone
import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ProductImageScraper:
    """Scrapes product images from various sources"""
    
    def __init__(self, limit=10, resume=False, demo=False):
        """Initialize the scraper with limit, resume, and demo options"""
        self.limit = limit
        self.resume = resume
        self.demo = demo
        self.progress_file = "image_scrape_progress.json"
        self.last_processed_id = None
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.start_time = datetime.now(timezone.utc)
        self.pool = None
        
        # Sample products for demo mode
        self.demo_products = [
            {"id": 1, "code": "3017620422003", "name": "Nutella"},
            {"id": 2, "code": "5449000000996", "name": "Coca-Cola Classic"},
            {"id": 3, "code": "7622210449283", "name": "Oreo Original"},
            {"id": 4, "code": "8000500033784", "name": "Kinder Bueno"},
            {"id": 5, "code": "5000112637922", "name": "Heinz Tomato Ketchup"},
            {"id": 6, "code": "3168930010265", "name": "Laughing Cow Cheese"},
            {"id": 7, "code": "5010029213019", "name": "Walkers Cheese & Onion Crisps"},
            {"id": 8, "code": "3175680011480", "name": "President Butter Unsalted"},
            {"id": 9, "code": "7613035429499", "name": "Nescafe Gold Blend"},
            {"id": 10, "code": "4005500096252", "name": "Haribo Goldbears"}
        ]
        
        # User agents for rotating to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/91.0.4472.80 Mobile/15E148 Safari/604.1'
        ]
        
        # Sources in priority order
        self.sources = [
            self.scrape_openfoodfacts_web,
            self.scrape_google_images,
            self.scrape_bing_images
        ]
        
        # Rate limiting
        self.min_delay = 1.0  # Minimum delay between requests in seconds
        self.max_delay = 3.0  # Maximum delay between requests in seconds
        self.last_request_time = {}  # Dictionary to track last request time per domain
    
    async def setup(self):
        """Set up database connection and load progress if resuming"""
        try:
            # If in demo mode, skip database connection
            if self.demo:
                logger.info("Running in demo mode, skipping database connection")
                return True
                
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
                        self.success_count = progress.get('success_count', 0)
                        self.failed_count = progress.get('failed_count', 0)
                        logger.info(f"Resuming from product ID {self.last_processed_id}")
                        logger.info(f"Progress so far: processed {self.processed_count}, success {self.success_count}, failed {self.failed_count}")
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
    
    async def get_products_without_images(self):
        """Get products without image URLs"""
        # If in demo mode, return demo products
        if self.demo:
            return self.demo_products[:self.limit]
            
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT id, code, name FROM products 
                    WHERE (image_url = '' OR image_url IS NULL)
                """
                
                # Add condition for resuming if needed
                params = []
                if self.resume and self.last_processed_id:
                    query += " AND id > $1"
                    params.append(self.last_processed_id)
                
                # Add ordering and limit
                query += " ORDER BY id LIMIT $" + str(len(params) + 1)
                params.append(self.limit)
                
                products = await conn.fetch(query, *params)
                
                return products
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
    async def update_product_image(self, product_id, product_code, image_url):
        """Update product image URL in database"""
        # If in demo mode, just log and return success
        if self.demo:
            logger.info(f"[DEMO] Would update product {product_code} with image URL: {image_url}")
            return True
            
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE products 
                    SET image_url = $1, last_updated = $2
                    WHERE code = $3
                """, image_url, datetime.now(timezone.utc), product_code)
                
                # Save progress
                await self.save_progress(product_id)
                
                return True
        except Exception as e:
            logger.error(f"Error updating image URL for product {product_code}: {str(e)}")
            return False
    
    async def save_progress(self, last_id):
        """Save progress to file for resume capability"""
        # Skip in demo mode
        if self.demo:
            return
            
        try:
            progress = {
                'last_id': last_id,
                'processed_count': self.processed_count,
                'success_count': self.success_count,
                'failed_count': self.failed_count,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f)
        except Exception as e:
            logger.error(f"Error saving progress: {str(e)}")
    
    async def make_request(self, session, url, headers=None):
        """Make HTTP request with rate limiting based on domain"""
        # Extract domain for per-domain rate limiting
        domain = urlparse(url).netloc
        
        # Wait if we've made a request to this domain recently
        current_time = time.time()
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            delay = random.uniform(self.min_delay, self.max_delay)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        
        # Update last request time for this domain
        self.last_request_time[domain] = time.time()
        
        # Make the request
        try:
            # Rotate user agents
            if not headers:
                headers = {}
            if 'User-Agent' not in headers:
                headers['User-Agent'] = random.choice(self.user_agents)
            
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', '60'))
                    logger.warning(f"Rate limited by {domain}. Waiting {retry_after} seconds.")
                    await asyncio.sleep(retry_after)
                    # Retry recursively after waiting
                    return await self.make_request(session, url, headers)
                else:
                    logger.warning(f"Error response from {url}: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Request error for {url}: {str(e)}")
            return None
    
    async def verify_image_url(self, session, image_url):
        """Verify that image URL is valid and accessible"""
        if not image_url:
            return False
        
        try:
            domain = urlparse(image_url).netloc
            current_time = time.time()
            if domain in self.last_request_time:
                elapsed = current_time - self.last_request_time[domain]
                delay = random.uniform(self.min_delay, self.max_delay)
                if elapsed < delay:
                    await asyncio.sleep(delay - elapsed)
            
            self.last_request_time[domain] = time.time()
            
            async with session.head(image_url, allow_redirects=True, timeout=10) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    return content_type.startswith('image/')
                return False
        except Exception:
            return False
    
    async def scrape_openfoodfacts_web(self, session, product_code, product_name):
        """Scrape image from OpenFoodFacts website (not API)"""
        # Construct the URL for the product page
        url = f"https://world.openfoodfacts.org/product/{product_code}"
        
        try:
            html = await self.make_request(session, url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to find the product image
            # Look for the main product image
            img_container = soup.select_one('#og_image')
            if img_container and img_container.get('src'):
                image_url = img_container.get('src')
                if await self.verify_image_url(session, image_url):
                    return image_url
            
            # Check product images section
            product_images = soup.select('.product-images img')
            for img in product_images:
                if img.get('src'):
                    image_url = img.get('src')
                    # Often thumbnails, try to get larger version
                    image_url = image_url.replace('.100.', '.400.')
                    image_url = image_url.replace('.200.', '.400.')
                    if await self.verify_image_url(session, image_url):
                        return image_url
            
            # No image found
            return None
        except Exception as e:
            logger.error(f"Error scraping OpenFoodFacts for {product_code}: {str(e)}")
            return None
    
    async def scrape_google_images(self, session, product_code, product_name):
        """Scrape image from Google Images"""
        # Construct a search query
        query = f"{product_name} {product_code} product package"
        url = f"https://www.google.com/search?q={quote(query)}&tbm=isch"
        
        try:
            html = await self.make_request(session, url)
            if not html:
                return None
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract image URLs - Google Images has different formats, so try multiple patterns
            
            # Try data-src attributes first
            for img in soup.select('img[data-src]'):
                image_url = img.get('data-src')
                if await self.verify_image_url(session, image_url):
                    return image_url
            
            # Try src attributes
            for img in soup.select('img.Q4LuWd'):  # Known class for Google Images thumbnails
                image_url = img.get('src')
                if image_url and 'http' in image_url:
                    if await self.verify_image_url(session, image_url):
                        return image_url
            
            # Look for JSON data in the page which contains image URLs
            pattern = r'AF_initDataCallback\(({.*?})\);'
            matches = re.findall(pattern, html)
            for match in matches[:3]:  # Only check first few matches to avoid high processing time
                try:
                    json_str = match
                    if 'https' in json_str:
                        urls = re.findall(r'https://[^"\']+\.(?:jpg|jpeg|png|webp|gif)', json_str)
                        for url in urls:
                            if await self.verify_image_url(session, url):
                                return url
                except Exception:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Error scraping Google Images for {product_name}: {str(e)}")
            return None
    
    async def scrape_bing_images(self, session, product_code, product_name):
        """Scrape image from Bing Images"""
        # Construct a search query
        query = f"{product_name} {product_code} food package"
        url = f"https://www.bing.com/images/search?q={quote(query)}&form=HDRSC2&first=1"
        
        try:
            html = await self.make_request(session, url)
            if not html:
                return None
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract image URLs - find murl attributes which contain original images
            for link in soup.find_all('a', {'class': 'iusc', 'm': True}):
                try:
                    m_val = link.get('m')
                    if m_val:
                        data = json.loads(m_val)
                        if 'murl' in data:
                            image_url = data['murl']
                            if await self.verify_image_url(session, image_url):
                                return image_url
                except Exception as e:
                    continue
            
            # If we can't find with the above method, try the simpler way (less reliable)
            for img in soup.select('img.mimg'):
                image_url = img.get('src')
                if image_url and 'http' in image_url:
                    if await self.verify_image_url(session, image_url):
                        return image_url
            
            return None
        except Exception as e:
            logger.error(f"Error scraping Bing Images for {product_name}: {str(e)}")
            return None
    
    async def scrape_product_image(self, session, product_id, product_code, product_name):
        """
        Attempt to scrape product image from multiple sources.
        Returns the first successful image URL, or None if all sources fail.
        """
        logger.info(f"Scraping image for {product_name} ({product_code})")
        
        # Try each source in order until we find an image
        for source_method in self.sources:
            try:
                image_url = await source_method(session, product_code, product_name)
                if image_url:
                    logger.info(f"Found image for {product_code} from {source_method.__name__}")
                    return image_url
            except Exception as e:
                logger.error(f"Error in {source_method.__name__} for {product_code}: {str(e)}")
                continue
        
        logger.warning(f"Failed to find image for {product_name} ({product_code}) from any source")
        return None
    
    async def process_product(self, session, product):
        """Process a single product to find and update its image"""
        product_id = product['id']
        product_code = product['code']
        product_name = product['name']
        
        # Scrape product image
        image_url = await self.scrape_product_image(session, product_id, product_code, product_name)
        
        self.processed_count += 1
        
        if image_url:
            # Update product image in database
            success = await self.update_product_image(product_id, product_code, image_url)
            if success:
                self.success_count += 1
                logger.info(f"Updated image for {product_name} ({product_code})")
                return True
        
        self.failed_count += 1
        logger.warning(f"Failed to update image for {product_name} ({product_code})")
        return False
    
    async def process_products(self):
        """Process products to find and update images"""
        # Get products without images
        products = await self.get_products_without_images()
        
        if not products:
            logger.info("No products found without images")
            return
        
        logger.info(f"Found {len(products)} products without images, processing up to {self.limit}")
        
        # Create HTTP session
        async with aiohttp.ClientSession() as session:
            # Process each product sequentially to respect rate limits
            for product in products:
                await self.process_product(session, product)
                # Small delay between products
                await asyncio.sleep(random.uniform(0.5, 1.5))
        
        await self.log_statistics()
    
    def format_elapsed_time(self, seconds):
        """Format elapsed time in a readable format"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    async def log_statistics(self):
        """Log statistics about the scraping process"""
        end_time = datetime.now(timezone.utc)
        elapsed_seconds = (end_time - self.start_time).total_seconds()
        
        logger.info("Scraping completed!")
        logger.info(f"Time elapsed: {self.format_elapsed_time(elapsed_seconds)}")
        logger.info(f"Products processed: {self.processed_count}")
        logger.info(f"Images updated successfully: {self.success_count}")
        logger.info(f"Failed updates: {self.failed_count}")
        
        success_rate = (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0
        logger.info(f"Success rate: {success_rate:.2f}%")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Scrape product images from various sources')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of products to process')
    parser.add_argument('--resume', action='store_true', help='Resume from last processed product')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode without database connection')
    return parser.parse_args()

async def main():
    """Main function"""
    # Parse command line arguments
    args = parse_args()
    
    # Create scraper
    scraper = ProductImageScraper(limit=args.limit, resume=args.resume, demo=args.demo)
    
    # Set up scraper
    if not await scraper.setup():
        logger.error("Failed to set up scraper, exiting")
        return
    
    try:
        # Process products
        await scraper.process_products()
    finally:
        # Clean up resources
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 