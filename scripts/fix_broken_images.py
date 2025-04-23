#!/usr/bin/env python
"""
Fix Broken Image Links
---------------------
This script identifies products with broken image links (404 errors) and
scrapes new images for about 20% of them.

Usage: python scripts/fix_broken_images.py --url SUPABASE_URL --key SUPABASE_KEY [--limit LIMIT]

Command-line arguments:
  --url SUPABASE_URL: URL of your Supabase instance
  --key SUPABASE_KEY: API key for your Supabase instance
  --limit LIMIT: Maximum number of products to process (default: 50)
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
import sys
from supabase import create_client, Client
from tabulate import tabulate

# Add the parent directory to the Python path to import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_fixer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class BrokenImageFixer:
    """Fixes broken image links by scraping new images"""
    
    def __init__(self, supabase_url=None, supabase_key=None, limit=50):
        """Initialize the fixer with Supabase credentials and options"""
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.limit = limit
        self.supabase = None
        self.progress_file = "image_fix_progress.json"
        self.last_processed_id = None
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.start_time = datetime.now(timezone.utc)
        
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
        
        # Ensure we have the required credentials
        if not self.supabase_url or not self.supabase_key:
            logger.error("SUPABASE_URL and SUPABASE_KEY must be provided (via args or env vars)")
            sys.exit(1)
    
    async def setup(self):
        """Set up Supabase client"""
        try:
            logger.info(f"Connecting to Supabase at {self.supabase_url[:30]}...")
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            
            # Test the connection
            response = self.supabase.table('products').select('code').limit(1).execute()
            if hasattr(response, 'data'):
                logger.info("Successfully connected to Supabase")
                return True
            else:
                logger.error("Failed to connect to Supabase - no data returned")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            return False
    
    async def get_products_with_broken_images(self):
        """Get products with broken image links"""
        try:
            # Get products with image URLs
            response = self.supabase.table('products') \
                .select('code, name, image_url') \
                .not_.is_('image_url', 'null') \
                .neq('image_url', '') \
                .limit(self.limit * 5) \
                .execute()
            
            if not hasattr(response, 'data'):
                return []
                
            # Filter for products with broken image links
            products = []
            async with aiohttp.ClientSession() as session:
                for product in response.data:
                    image_url = product.get('image_url')
                    if image_url:
                        # Check if the image URL is broken
                        is_broken = await self.is_broken_image(session, image_url)
                        if is_broken:
                            products.append(product)
                            if len(products) >= self.limit:
                                break
            
            return products
        except Exception as e:
            logger.error(f"Error getting products with broken images: {str(e)}")
            return []
    
    async def is_broken_image(self, session, image_url):
        """Check if an image URL is broken (returns 404)"""
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
                return response.status == 404
        except Exception:
            return True  # If we can't check, assume it's broken
    
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
    
    async def scrape_product_image(self, session, product_code, product_name):
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
    
    async def update_product_image(self, product_code, image_url):
        """Update product image URL in database"""
        try:
            # First check if we can fetch the product with this code
            check_response = self.supabase.table('products') \
                .select('code') \
                .eq('code', product_code) \
                .execute()
                
            if not hasattr(check_response, 'data') or not check_response.data:
                logger.error(f"Product with code {product_code} not found or cannot be read")
                return False
                
            # Try to update
            try:
                response = self.supabase.table('products') \
                    .update({'image_url': image_url, 'last_updated': datetime.now(timezone.utc).isoformat()}) \
                    .eq('code', product_code) \
                    .execute()
                
                if hasattr(response, 'data') and response.data and len(response.data) > 0:
                    logger.info(f"Successfully updated image for product {product_code}")
                    return True
                else:
                    logger.error(f"Update response has no data: {response.__dict__ if hasattr(response, '__dict__') else response}")
                    return False
            except Exception as update_error:
                error_message = str(update_error).lower()
                if 'permission' in error_message or 'unauthorized' in error_message or '401' in error_message or '403' in error_message:
                    logger.error("=== PERMISSION ERROR ===")
                    logger.error("Your API key does not have permission to update the database.")
                    logger.error("You need to use a 'service_role' key instead of the 'anon/public' key.")
                    logger.error("Get this from your Supabase dashboard under Project Settings > API.")
                    logger.error("The service_role key starts with 'eyJ...' and has 'role':'service_role' in it.")
                    logger.error("=== PERMISSION ERROR ===")
                else:
                    logger.error(f"Update error: {update_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating image URL for product {product_code}: {str(e)}")
            return False
    
    async def process_product(self, session, product):
        """Process a single product to find and update its image"""
        product_code = product['code']
        product_name = product['name']
        
        # Scrape product image
        image_url = await self.scrape_product_image(session, product_code, product_name)
        
        self.processed_count += 1
        
        if image_url:
            # Update product image in database
            success = await self.update_product_image(product_code, image_url)
            if success:
                self.success_count += 1
                logger.info(f"Updated image for {product_name} ({product_code})")
                return True
        
        self.failed_count += 1
        logger.warning(f"Failed to update image for {product_name} ({product_code})")
        return False
    
    async def fix_broken_images(self):
        """Fix broken image links for products"""
        # Get products with broken images
        products = await self.get_products_with_broken_images()
        
        if not products:
            logger.info("No products found with broken images")
            return
        
        logger.info(f"Found {len(products)} products with broken images, processing up to {self.limit}")
        
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
        """Log statistics about the image fixing process"""
        end_time = datetime.now(timezone.utc)
        elapsed_seconds = (end_time - self.start_time).total_seconds()
        
        logger.info("Image fixing completed!")
        logger.info(f"Time elapsed: {self.format_elapsed_time(elapsed_seconds)}")
        logger.info(f"Products processed: {self.processed_count}")
        logger.info(f"Images updated successfully: {self.success_count}")
        logger.info(f"Failed updates: {self.failed_count}")
        
        success_rate = (self.success_count / self.processed_count * 100) if self.processed_count > 0 else 0
        logger.info(f"Success rate: {success_rate:.2f}%")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Fix broken image links in the meat products database')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of products to process')
    return parser.parse_args()

async def main():
    """Main function"""
    # Parse arguments
    args = parse_args()
    
    # Create fixer
    fixer = BrokenImageFixer(
        supabase_url=args.url,
        supabase_key=args.key,
        limit=args.limit
    )
    
    # Set up fixer
    if not await fixer.setup():
        logger.error("Failed to set up image fixer, exiting")
        return
    
    # Fix broken images
    await fixer.fix_broken_images()

if __name__ == "__main__":
    asyncio.run(main()) 