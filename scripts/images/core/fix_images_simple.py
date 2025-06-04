"""
Simplified image scraping script with better anti-detection.
Fixes rate limiting issues and uses proven scraping techniques.
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple
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
from bs4 import BeautifulSoup
from urllib.parse import quote
import random
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleImageFixer:
    def __init__(self, database_url: str, batch_size: int = 10, time_limit_hours: int = 2):
        self.database_url = database_url
        self.batch_size = batch_size
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=time_limit_hours)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Better user agents (mobile + desktop)
        self.user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0 Firefox/88.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        
        # Relaxed rate limiting (was too aggressive)
        self.min_delay = 8.0  # Increased from 2s
        self.max_delay = 15.0  # Increased from 5s
        self.last_request_time = 0
        self.failed_count = 0
        self.max_failures = 10  # Increased from 3

    def should_continue(self) -> bool:
        return datetime.now() < self.end_time and self.failed_count < self.max_failures

    async def make_request_safe(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Make request with human-like timing and headers"""
        # Wait between requests
        current_time = time.time()
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            delay = random.uniform(self.min_delay, self.max_delay)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        
        self.last_request_time = time.time()
        
        # Random headers to look more human
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        try:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    self.failed_count = max(0, self.failed_count - 1)  # Reduce failure count on success
                    return await response.text()
                else:
                    self.failed_count += 1
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            self.failed_count += 1
            logger.warning(f"Request error: {str(e)}")
            return None

    async def search_google_simple(self, session: aiohttp.ClientSession, product_name: str) -> Optional[str]:
        """Simple Google image search with better parsing"""
        query = f"{product_name} meat product package"
        url = f"https://www.google.com/search?q={quote(query)}&tbm=isch&safe=active"
        
        html = await self.make_request_safe(session, url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try multiple selectors
        selectors = [
            'img[data-src]',
            'img[src*="http"]',
            'img.t0fcAb',
            'img.Q4LuWd'
        ]
        
        for selector in selectors:
            imgs = soup.select(selector)
            for img in imgs[:3]:  # Check first 3 images
                image_url = img.get('data-src') or img.get('src')
                if image_url and 'http' in image_url and await self.verify_image_url(session, image_url):
                    return image_url
        
        return None

    async def search_bing_simple(self, session: aiohttp.ClientSession, product_name: str) -> Optional[str]:
        """Simple Bing image search"""
        query = f"{product_name} food product"
        url = f"https://www.bing.com/images/search?q={quote(query)}&first=1"
        
        html = await self.make_request_safe(session, url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Bing specific selectors
        for img in soup.select('img.mimg')[:3]:
            image_url = img.get('src')
            if image_url and await self.verify_image_url(session, image_url):
                return image_url
        
        return None

    async def verify_image_url(self, session: aiohttp.ClientSession, image_url: str) -> bool:
        """Quick image URL verification"""
        if not image_url or len(image_url) < 10:
            return False
        
        try:
            async with session.head(image_url, timeout=10) as response:
                return response.status == 200
        except:
            return False

    async def get_image_from_url(self, url: str, session: aiohttp.ClientSession) -> Tuple[bool, Optional[bytes]]:
        """Download image"""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    return True, await response.read()
        except Exception as e:
            logger.debug(f"Download error for {url}: {str(e)}")
        return False, None

    async def process_image(self, image_data: bytes) -> Optional[bytes]:
        """Simple image processing"""
        try:
            img = Image.open(io.BytesIO(image_data))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if needed
            if img.size[0] > 800 or img.size[1] > 800:
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.debug(f"Image processing error: {str(e)}")
            return None

    async def fix_product_image(self, product: Dict, session: aiohttp.ClientSession) -> bool:
        """Fix single product with simple approach"""
        if not self.should_continue():
            return False
            
        product_name = product['name']
        logger.info(f"Processing: {product_name}")
        
        # Try Google first, then Bing
        for search_func in [self.search_google_simple, self.search_bing_simple]:
            try:
                image_url = await search_func(session, product_name)
                if image_url:
                    success, image_data = await self.get_image_from_url(image_url, session)
                    if success and image_data:
                        processed_data = await self.process_image(image_data)
                        if processed_data:
                            await self.update_product_image(product['code'], processed_data)
                            logger.info(f"✅ Fixed: {product_name}")
                            return True
            except Exception as e:
                logger.debug(f"Error with {search_func.__name__}: {str(e)}")
                continue
        
        logger.warning(f"❌ Failed: {product_name}")
        return False

    async def update_product_image(self, product_code: str, image_data: bytes) -> bool:
        """Update database"""
        try:
            base64_data = base64.b64encode(image_data).decode('utf-8')
            conn = await asyncpg.connect(self.database_url, ssl=self.ssl_context)
            try:
                await conn.execute("""
                    UPDATE products SET image_data = $1, last_updated = $2 WHERE code = $3
                """, base64_data, datetime.now(), product_code)
                return True
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return False

    async def fix_images(self) -> Dict[str, int]:
        """Main fixing process"""
        stats = {'total': 0, 'fixed': 0, 'failed': 0}
        
        conn = await asyncpg.connect(self.database_url, ssl=self.ssl_context)
        try:
            products = await conn.fetch("""
                SELECT code, name FROM products 
                WHERE (image_data IS NULL OR octet_length(image_data) = 0)
                LIMIT 50
            """)
            stats['total'] = len(products)
            logger.info(f"Found {stats['total']} products to fix")
        finally:
            await conn.close()
        
        async with aiohttp.ClientSession() as session:
            for i, product in enumerate(products):
                if not self.should_continue():
                    break
                    
                success = await self.fix_product_image(product, session)
                if success:
                    stats['fixed'] += 1
                else:
                    stats['failed'] += 1
                
                if (i + 1) % 5 == 0:
                    logger.info(f"Progress: {i+1}/{stats['total']} - Success: {stats['fixed']}, Failed: {stats['failed']}")
        
        return stats

async def main():
    parser = argparse.ArgumentParser(description='Simple image fixing')
    parser.add_argument('--batch-size', type=int, default=10)
    parser.add_argument('--time-limit', type=int, default=2)
    args = parser.parse_args()
    
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error('DATABASE_URL not set')
        return
    
    fixer = SimpleImageFixer(database_url, args.batch_size, args.time_limit)
    stats = await fixer.fix_images()
    
    logger.info(f"\n🎯 Final Results:")
    logger.info(f"   Total: {stats['total']}")
    logger.info(f"   Fixed: {stats['fixed']}")
    logger.info(f"   Failed: {stats['failed']}")
    logger.info(f"   Success Rate: {stats['fixed']/stats['total']*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main()) 