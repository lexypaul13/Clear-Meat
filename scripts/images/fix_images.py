"""
Comprehensive image fixing script for the MeatWise API.
Handles both individual and bulk image fixes, with retry logic and progress tracking.
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
from datetime import datetime
import argparse
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageFixer:
    def __init__(self, database_url: str, batch_size: int = 50, max_retries: int = 3):
        self.database_url = database_url
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
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
            
            # Convert to RGB if needed
            if img.mode not in ('RGB', 'RGBA'):
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
            # Try to download image
            success, image_data = await self.get_image_from_url(product['image_url'], session)
            if not success or not image_data:
                return False
            
            # Process image
            processed_data = await self.process_image(image_data)
            if not processed_data:
                return False
            
            # Update database
            conn = await asyncpg.connect(self.database_url, ssl=self.ssl_context)
            try:
                await conn.execute("""
                    UPDATE products 
                    SET 
                        image_data = $1,
                        last_updated = $2
                    WHERE code = $3
                """, processed_data, datetime.now(), product['code'])
                return True
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error(f"Error fixing image for product {product['code']}: {str(e)}")
            return False

    async def fix_all_images(self) -> Dict[str, int]:
        """Fix all broken images in the database."""
        stats = {
            'total': 0,
            'fixed': 0,
            'failed': 0
        }
        
        # Connect to database
        conn = await asyncpg.connect(self.database_url, ssl=self.ssl_context)
        
        try:
            # Get products needing fixes
            products = await conn.fetch("""
                SELECT 
                    code,
                    image_url
                FROM products 
                WHERE 
                    image_url IS NOT NULL 
                    AND (image_data IS NULL OR octet_length(image_data) = 0)
            """)
            
            stats['total'] = len(products)
            logger.info(f"Found {stats['total']} products needing image fixes")
            
            # Process in batches
            async with aiohttp.ClientSession() as session:
                for i in range(0, len(products), self.batch_size):
                    batch = products[i:i + self.batch_size]
                    tasks = [self.fix_product_image(p, session) for p in batch]
                    results = await asyncio.gather(*tasks)
                    
                    stats['fixed'] += sum(1 for r in results if r)
                    stats['failed'] += sum(1 for r in results if not r)
                    
                    # Progress update
                    logger.info(f"Progress: {i + len(batch)}/{stats['total']} products processed")
                    
            return stats
            
        finally:
            await conn.close()

async def main():
    try:
        # Parse arguments
        parser = argparse.ArgumentParser(description='Fix broken product images')
        parser.add_argument('--batch-size', type=int, default=50, help='Number of images to process in parallel')
        parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for failed downloads')
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
            max_retries=args.max_retries
        )
        
        # Run fixes
        stats = await fixer.fix_all_images()
        
        # Print summary
        logger.info("\nFix complete:")
        logger.info(f"- Total products processed: {stats['total']}")
        logger.info(f"- Successfully fixed: {stats['fixed']}")
        logger.info(f"- Failed to fix: {stats['failed']}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 