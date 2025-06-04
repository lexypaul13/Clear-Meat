"""
Comprehensive image fixing script for the MeatWise API.
Handles both individual and bulk image fixes, with retry logic and progress tracking.
Now uses Google Custom Search API and Bing Image Search API instead of scraping.
Will run for 8 hours to process all images.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
import aiohttp
import asyncpg
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv
import ssl
from datetime import datetime, timedelta
import argparse
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse
import random
import re
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageFixer:
    def __init__(self, database_url: str, batch_size: int = 50, max_retries: int = 3, time_limit_hours: int = 8):
        self.database_url = database_url
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.time_limit_hours = time_limit_hours
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=time_limit_hours)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # User agents for rotating to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/91.0.4472.80 Mobile/15E148 Safari/604.1'
        ]
        
        # Domain-specific rate limiting
        self.domain_delays = {
            'google.com': (5.0, 10.0),
            'bing.com': (4.0, 8.0),
            'images.google.com': (5.0, 10.0),
            'images.bing.com': (4.0, 8.0)
        }
        
        # Default rate limiting
        self.min_delay = 2.0  # Minimum delay between requests in seconds
        self.max_delay = 5.0  # Maximum delay between requests in seconds
        self.last_request_time = {}  # Dictionary to track last request time per domain
        self.failed_domains = {}  # Track failed domains to avoid retrying too soon
        self.domain_failure_count = {}  # Track number of failures per domain
        self.max_domain_failures = 3  # Maximum number of failures before longer cooldown
        
        # API Configuration
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        self.bing_api_key = os.getenv('BING_API_KEY')
        
        # Request tracking
        self.api_request_counts = {'google': 0, 'bing': 0}
        self.api_daily_limits = {'google': 100, 'bing': 1000}  # Free tier limits

    def should_continue(self) -> bool:
        """Check if we should continue processing based on time limit"""
        return datetime.now() < self.end_time

    async def make_request(self, session: aiohttp.ClientSession, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        """Make HTTP request with rate limiting based on domain"""
        # Extract domain for per-domain rate limiting
        domain = urlparse(url).netloc
        
        # Check if domain is in failed state
        if domain in self.failed_domains:
            if time.time() - self.failed_domains[domain] < 300:  # 5 minutes cooldown
                logger.warning(f"Skipping {domain} due to recent failures")
                return None
            else:
                del self.failed_domains[domain]
                self.domain_failure_count[domain] = 0
        
        # Get domain-specific delays
        min_delay, max_delay = self.domain_delays.get(domain, (self.min_delay, self.max_delay))
        
        # Wait if we've made a request to this domain recently
        current_time = time.time()
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            delay = random.uniform(min_delay, max_delay)
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
            
            logger.debug(f"Making request to {url} with headers: {headers}")
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    # Reset failure count on success
                    self.domain_failure_count[domain] = 0
                    return await response.text()
                elif response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', '300'))  # 5 minutes default
                    logger.warning(f"Rate limited by {domain}. Waiting {retry_after} seconds.")
                    self.failed_domains[domain] = time.time()
                    self.domain_failure_count[domain] = self.domain_failure_count.get(domain, 0) + 1
                    
                    # If too many failures, increase cooldown time
                    if self.domain_failure_count[domain] >= self.max_domain_failures:
                        retry_after = 600  # 10 minutes
                        logger.warning(f"Too many failures for {domain}, increasing cooldown to {retry_after} seconds")
                    
                    await asyncio.sleep(retry_after)
                    return None
                else:
                    logger.warning(f"Error response from {url}: HTTP {response.status}")
                    self.domain_failure_count[domain] = self.domain_failure_count.get(domain, 0) + 1
                    return None
        except Exception as e:
            logger.error(f"Request error for {url}: {str(e)}")
            self.failed_domains[domain] = time.time()
            self.domain_failure_count[domain] = self.domain_failure_count.get(domain, 0) + 1
            return None

    async def search_google_images_api(self, session: aiohttp.ClientSession, product_code: str, product_name: str) -> Optional[str]:
        """Search for images using Google Custom Search API"""
        if not self.google_api_key or not self.google_search_engine_id:
            logger.warning("Google API key or Search Engine ID not configured")
            return None
            
        if self.api_request_counts['google'] >= self.api_daily_limits['google']:
            logger.warning("Google API daily limit reached")
            return None
        
        query = f"{product_name} {product_code} product package"
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_search_engine_id,
            'q': query,
            'searchType': 'image',
            'num': 5,
            'imgSize': 'medium',
            'imgType': 'photo',
            'safe': 'active'
        }
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    self.api_request_counts['google'] += 1
                    data = await response.json()
                    
                    if 'items' in data:
                        for item in data['items']:
                            image_url = item.get('link')
                            if image_url and await self.verify_image_url(session, image_url):
                                return image_url
                elif response.status == 403:
                    logger.error("Google API quota exceeded or invalid key")
                    return None
                else:
                    logger.warning(f"Google API error: HTTP {response.status}")
                    
            return None
        except Exception as e:
            logger.error(f"Error with Google Custom Search API for {product_name}: {str(e)}")
            return None

    async def search_bing_images_api(self, session: aiohttp.ClientSession, product_code: str, product_name: str) -> Optional[str]:
        """Search for images using Bing Image Search API"""
        if not self.bing_api_key:
            logger.warning("Bing API key not configured")
            return None
            
        if self.api_request_counts['bing'] >= self.api_daily_limits['bing']:
            logger.warning("Bing API daily limit reached")
            return None
        
        query = f"{product_name} {product_code} food package"
        url = "https://api.bing.microsoft.com/v7.0/images/search"
        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_api_key
        }
        params = {
            'q': query,
            'count': 5,
            'size': 'Medium',
            'imageType': 'Photo',
            'safeSearch': 'Moderate'
        }
        
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    self.api_request_counts['bing'] += 1
                    data = await response.json()
                    
                    if 'value' in data:
                        for item in data['value']:
                            image_url = item.get('contentUrl')
                            if image_url and await self.verify_image_url(session, image_url):
                                return image_url
                elif response.status == 401:
                    logger.error("Bing API key invalid")
                    return None
                elif response.status == 403:
                    logger.error("Bing API quota exceeded")
                    return None
                else:
                    logger.warning(f"Bing API error: HTTP {response.status}")
                    
            return None
        except Exception as e:
            logger.error(f"Error with Bing Image Search API for {product_name}: {str(e)}")
            return None

    async def search_fallback_generic(self, session: aiohttp.ClientSession, product_code: str, product_name: str) -> Optional[str]:
        """Fallback to generic food images based on meat type"""
        # Extract meat type from product name
        meat_type = "meat"
        if any(word in product_name.lower() for word in ['beef', 'steak', 'burger']):
            meat_type = "beef"
        elif any(word in product_name.lower() for word in ['chicken', 'poultry']):
            meat_type = "chicken"
        elif any(word in product_name.lower() for word in ['pork', 'ham', 'bacon']):
            meat_type = "pork"
        elif any(word in product_name.lower() for word in ['turkey']):
            meat_type = "turkey"
        elif any(word in product_name.lower() for word in ['lamb']):
            meat_type = "lamb"
        
        # Use a curated list of high-quality generic food images
        generic_images = {
            'beef': 'https://images.unsplash.com/photo-1551782450-17144efb9c50?w=400',
            'chicken': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400',
            'pork': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=400',
            'turkey': 'https://images.unsplash.com/photo-1574672280600-4accfa5b6f98?w=400',
            'lamb': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400',
            'meat': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400'
        }
        
        fallback_url = generic_images.get(meat_type, generic_images['meat'])
        if await self.verify_image_url(session, fallback_url):
            logger.info(f"Using generic {meat_type} image for {product_name}")
            return fallback_url
            
        return None

    async def verify_image_url(self, session: aiohttp.ClientSession, image_url: str) -> bool:
        """Verify that image URL is valid and accessible"""
        if not image_url:
            return False
        
        try:
            async with session.head(image_url, allow_redirects=True, timeout=10) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    return content_type.startswith('image/')
                return False
        except Exception:
            return False

    async def get_image_from_url(self, url: str, session: aiohttp.ClientSession, retries: int = 0) -> Tuple[bool, Optional[bytes]]:
        """Download image from URL with retry logic."""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return True, await response.read()
                elif response.status in [429, 500, 502, 503, 504] and retries < self.max_retries:
                    await asyncio.sleep(2 ** retries)  # Exponential backoff
                    return await self.get_image_from_url(url, session, retries + 1)
                else:
                    return False, None
        except Exception as e:
            if retries < self.max_retries:
                await asyncio.sleep(2 ** retries)
                return await self.get_image_from_url(url, session, retries + 1)
            logger.error(f"Error downloading image from {url}: {str(e)}")
            return False, None

    async def process_image(self, image_data: bytes) -> Optional[bytes]:
        """Process and validate image data."""
        try:
            # Validate image
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed (including RGBA)
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # Create a white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                # Paste the image on the background
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                else:
                    background.paste(img)
                img = background
            elif img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Resize if too large
            max_size = (800, 800)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save as JPEG
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return None

    async def fix_product_image(self, product: Dict, session: aiohttp.ClientSession) -> bool:
        """Fix a single product's image."""
        try:
            # Try API-based image search
            sources = [
                self.search_google_images_api,
                self.search_bing_images_api,
                self.search_fallback_generic
            ]
            
            for source in sources:
                try:
                    # Check if we should continue based on time limit
                    if not self.should_continue():
                        return False
                        
                    logger.info(f"Trying {source.__name__} for product {product['code']}")
                    image_url = await source(session, product['code'], product['name'])
                    if image_url:
                        logger.info(f"Found image URL from {source.__name__} for {product['code']}: {image_url}")
                        success, image_data = await self.get_image_from_url(image_url, session)
                        if success and image_data:
                            processed_data = await self.process_image(image_data)
                            if processed_data:
                                logger.info(f"Successfully processed image for {product['code']} using {source.__name__}")
                                return await self.update_product_image(product['code'], processed_data)
                            else:
                                logger.warning(f"Failed to process image for {product['code']} from {source.__name__}")
                        else:
                            logger.warning(f"Failed to download image for {product['code']} from {source.__name__}")
                    else:
                        logger.warning(f"No image URL found from {source.__name__} for {product['code']}")
                except Exception as e:
                    logger.error(f"Error with source {source.__name__} for product {product['code']}: {str(e)}")
                    continue
            
            logger.warning(f"Failed to find image for product {product['code']} from any source")
            return False
                
        except Exception as e:
            logger.error(f"Error fixing image for product {product['code']}: {str(e)}")
            return False

    async def update_product_image(self, product_code: str, image_data: bytes) -> bool:
        """Update product image in database"""
        try:
            # Convert image data to base64 string
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            conn = await asyncpg.connect(self.database_url, ssl=self.ssl_context)
            try:
                await conn.execute("""
                    UPDATE products 
                    SET 
                        image_data = $1,
                        last_updated = $2
                    WHERE code = $3
                """, base64_data, datetime.now(), product_code)
                return True
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error updating image for product {product_code}: {str(e)}")
            return False

    async def fix_all_images(self) -> Dict[str, int]:
        """Fix all broken images in the database."""
        stats = {
            'total': 0,
            'fixed': 0,
            'failed': 0,
            'remaining': 0
        }
        
        # Connect to database
        conn = await asyncpg.connect(self.database_url, ssl=self.ssl_context)
        
        try:
            # Get products needing fixes - now looking for any products without image data
            products = await conn.fetch("""
                SELECT 
                    code,
                    name,
                    image_url
                FROM products 
                WHERE 
                    (image_data IS NULL OR octet_length(image_data) = 0)
                ORDER BY code
            """)
            
            stats['total'] = len(products)
            logger.info(f"Found {stats['total']} products needing image fixes")
            
            # Process in batches
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=self.ssl_context),
                timeout=aiohttp.ClientTimeout(total=60)
            ) as session:
                for i in range(0, len(products), self.batch_size):
                    if not self.should_continue():
                        stats['remaining'] = len(products) - i
                        logger.info(f"Time limit reached. {stats['remaining']} products remaining.")
                        break
                        
                    batch = products[i:i + self.batch_size]
                    tasks = [self.fix_product_image(p, session) for p in batch]
                    results = await asyncio.gather(*tasks)
                    
                    stats['fixed'] += sum(1 for r in results if r)
                    stats['failed'] += sum(1 for r in results if not r)
                    
                    # Progress update
                    elapsed = datetime.now() - self.start_time
                    remaining = self.end_time - datetime.now()
                    logger.info(f"Progress: {i + len(batch)}/{stats['total']} products processed")
                    logger.info(f"Time elapsed: {elapsed}, Time remaining: {remaining}")
                    
            return stats
            
        finally:
            await conn.close()

async def main():
    try:
        # Parse arguments
        parser = argparse.ArgumentParser(description='Fix broken product images')
        parser.add_argument('--batch-size', type=int, default=50, help='Number of images to process in parallel')
        parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed downloads')
        parser.add_argument('--time-limit', type=int, default=8, help='Time limit in hours')
        args = parser.parse_args()
        
        # Load environment variables
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error('DATABASE_URL not set')
            return
            
        # Create fixer
        fixer = ImageFixer(
            database_url=database_url,
            batch_size=args.batch_size,
            max_retries=args.max_retries,
            time_limit_hours=args.time_limit
        )
        
        # Run fixes
        stats = await fixer.fix_all_images()
        
        # Print summary
        logger.info("\nFix complete:")
        logger.info(f"- Total products processed: {stats['total']}")
        logger.info(f"- Successfully fixed: {stats['fixed']}")
        logger.info(f"- Failed to fix: {stats['failed']}")
        if stats['remaining'] > 0:
            logger.info(f"- Products remaining: {stats['remaining']}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 