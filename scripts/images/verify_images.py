"""
Comprehensive image verification script for the MeatWise API.
Combines functionality for verifying image existence, accessibility, and validity.
"""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
import asyncpg
from PIL import Image
import io
import os
from dotenv import load_dotenv
import ssl
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageVerifier:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def verify_image_data(self, image_data: bytes) -> Dict:
        """Verify if image data is valid and get its properties."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return {
                    'valid': True,
                    'format': img.format,
                    'size': img.size,
                    'mode': img.mode
                }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }

    async def verify_image_url(self, url: str, session: aiohttp.ClientSession) -> Dict:
        """Verify if an image URL is accessible and valid."""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        'valid': False,
                        'error': f'HTTP {response.status}'
                    }
                
                image_data = await response.read()
                result = await self.verify_image_data(image_data)
                result['url'] = url
                result['size_bytes'] = len(image_data)
                return result
                
        except Exception as e:
            return {
                'valid': False,
                'url': url,
                'error': str(e)
            }

    async def verify_product_images(self) -> List[Dict]:
        """Verify all product images in the database."""
        results = []
        
        # Connect to database
        conn = await asyncpg.connect(
            self.database_url,
            ssl=self.ssl_context
        )
        
        try:
            # Get all products with images
            products = await conn.fetch("""
                SELECT 
                    code,
                    image_data,
                    last_updated
                FROM products 
                WHERE image_data IS NOT NULL
            """)
            
            logger.info(f"Found {len(products)} products with images")
            
            async with aiohttp.ClientSession() as session:
                for product in products:
                    result = {
                        'code': product['code'],
                        'last_updated': product['last_updated']
                    }
                    
                    # Verify image data
                    if product['image_data']:
                        image_result = await self.verify_image_data(product['image_data'])
                        result.update(image_result)
                    
                    results.append(result)
                    
            # Generate summary
            valid_count = sum(1 for r in results if r.get('valid', False))
            invalid_count = len(results) - valid_count
            
            logger.info(f"Verification complete:")
            logger.info(f"- Total images: {len(results)}")
            logger.info(f"- Valid images: {valid_count}")
            logger.info(f"- Invalid images: {invalid_count}")
            
            return results
            
        finally:
            await conn.close()

    async def update_invalid_images(self, results: List[Dict]) -> None:
        """Update database to mark invalid images."""
        conn = await asyncpg.connect(
            self.database_url,
            ssl=self.ssl_context
        )
        
        try:
            invalid_products = [r['code'] for r in results if not r.get('valid', False)]
            
            if invalid_products:
                await conn.execute("""
                    UPDATE products 
                    SET 
                        image_data = NULL,
                        last_updated = $1
                    WHERE code = ANY($2)
                """, datetime.now(), invalid_products)
                
                logger.info(f"Marked {len(invalid_products)} products as having invalid images")
        
        finally:
            await conn.close()

async def main():
    try:
        # Load environment variables
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error('DATABASE_URL not set')
            return
            
        # Create verifier
        verifier = ImageVerifier(database_url)
        
        # Run verification
        results = await verifier.verify_product_images()
        
        # Update invalid images
        await verifier.update_invalid_images(results)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 