#!/usr/bin/env python
"""
Upload Meat Product Images to Supabase
------------------------------------
Downloads images for meat products from various sources and uploads them to Supabase storage.
Updates the database with the new Supabase storage URLs.

Usage: python scripts/upload_meat_images.py --url SUPABASE_URL --key SUPABASE_KEY
"""

import os
import sys
import time
import argparse
import logging
import requests
import io
from PIL import Image
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from supabase import create_client, Client
from bs4 import BeautifulSoup
import random
from urllib.parse import quote
import asyncio
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("meat_images_upload.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 50
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
]

class ImageUploader:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.bucket_name = "product-images"
        self.setup_storage()

    def setup_storage(self):
        """Ensure the storage bucket exists"""
        try:
            # Try to get the bucket, create if doesn't exist
            buckets = self.supabase.storage.list_buckets()
            if not any(b.name == self.bucket_name for b in buckets):
                self.supabase.storage.create_bucket(self.bucket_name, options={'public': True})
                logger.info(f"Created new bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error setting up storage: {str(e)}")
            raise

    async def get_meat_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get meat products from the database"""
        try:
            response = self.supabase.table('products') \
                .select('code, name, meat_type') \
                .eq('meat_type', 'beef') \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []

    async def search_images(self, product: Dict[str, Any]) -> Optional[str]:
        """Search for product images using multiple sources"""
        name = product['name']
        code = product['code']
        meat_type = product['meat_type']
        
        # Try OpenFoodFacts first
        off_url = f"https://world.openfoodfacts.org/product/{code}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(off_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        img = soup.select_one('#og_image')
                        if img and img.get('src'):
                            return img['src']
        except Exception as e:
            logger.warning(f"OpenFoodFacts error for {code}: {str(e)}")

        # Try Bing Images as fallback
        search_query = quote(f"{name} {meat_type} meat product package")
        bing_url = f"https://www.bing.com/images/search?q={search_query}"
        headers = {'User-Agent': random.choice(USER_AGENTS)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(bing_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        for img in soup.select('img.mimg'):
                            if img.get('src'):
                                return img['src']
        except Exception as e:
            logger.warning(f"Bing search error for {name}: {str(e)}")

        return None

    async def download_and_upload_image(self, image_url: str, product_code: str) -> Optional[str]:
        """Download image and upload to Supabase storage"""
        try:
            # Download image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return None
                    image_data = await response.read()

            # Upload to Supabase storage
            file_name = f"{product_code}.jpg"
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_name,
                file=image_data,
                file_options={"content-type": "image/jpeg"}
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_name)
            return public_url

        except Exception as e:
            logger.error(f"Error processing image for {product_code}: {str(e)}")
            return None

    async def update_product_image(self, product_code: str, image_url: str):
        """Update product's image URL in database"""
        try:
            self.supabase.table('products') \
                .update({'image_url': image_url, 'last_updated': datetime.now().isoformat()}) \
                .eq('code', product_code) \
                .execute()
            logger.info(f"Updated image URL for product {product_code}")
        except Exception as e:
            logger.error(f"Error updating product {product_code}: {str(e)}")

    async def process_product(self, product: Dict[str, Any]):
        """Process a single product"""
        try:
            # Search for image
            image_url = await self.search_images(product)
            if not image_url:
                logger.warning(f"No image found for {product['name']}")
                return

            # Download and upload to Supabase
            storage_url = await self.download_and_upload_image(image_url, product['code'])
            if storage_url:
                # Update database
                await self.update_product_image(product['code'], storage_url)
                logger.info(f"Successfully processed {product['name']}")
            else:
                logger.warning(f"Failed to process image for {product['name']}")

        except Exception as e:
            logger.error(f"Error processing {product['name']}: {str(e)}")

    async def process_all_products(self, limit: int = 50):
        """Process all products"""
        products = await self.get_meat_products(limit)
        logger.info(f"Found {len(products)} products to process")

        for product in products:
            await self.process_product(product)
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)

def main():
    parser = argparse.ArgumentParser(description='Upload meat product images to Supabase')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    args = parser.parse_args()

    # Get Supabase credentials
    supabase_url = args.url or os.getenv('SUPABASE_URL')
    supabase_key = args.key or os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be provided")
        sys.exit(1)

    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        uploader = ImageUploader(supabase)

        # Run the async process
        asyncio.run(uploader.process_all_products(50))
        
        logger.info("Processing completed successfully")

    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 