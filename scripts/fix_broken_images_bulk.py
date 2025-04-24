#!/usr/bin/env python
"""
Fix Broken Images - Bulk Version
-------------------
This script replaces broken image URLs with new scraped images.
"""

import os
import sys
import time
import argparse
import logging
import concurrent.futures
from tqdm import tqdm
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from bs4 import BeautifulSoup
import random
from urllib.parse import quote
import io
from PIL import Image
import socket
import http.client
import asyncio
import aiohttp
import json
import asyncpg
import re
import backoff
from urllib.parse import urlparse
import base64
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("image_fix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
DATABASE_URL = "postgresql://postgres.szswmlkhirkmozwvhpnc:qvCRDhRRfcaNWnVh@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
BATCH_SIZE = 10  # Process only 10 products for testing
DEFAULT_MAX_WORKERS = 5
MAX_RETRIES = 3
RETRY_DELAY = 5
SUCCESS_LOG = "success_log.txt"
ERROR_LOG = "error_log.txt"
USE_PROXIES = False

# Minimum image requirements
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 200
MIN_IMAGE_SIZE_BYTES = 10000  # 10KB minimum
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB maximum

# User agent strings for rotating
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
]

# Search engines to try
SEARCH_ENGINES = [
    {
        "name": "google",
        "url": "https://www.google.com/search?q={query}&tbm=isch",
        "referer": "https://www.google.com/"
    },
    {
        "name": "bing",
        "url": "https://www.bing.com/images/search?q={query}",
        "referer": "https://www.bing.com/"
    }
]

# Global configuration
config = {
    "max_workers": DEFAULT_MAX_WORKERS,
    "use_proxies": USE_PROXIES,
    "min_image_width": MIN_IMAGE_WIDTH,
    "min_image_height": MIN_IMAGE_HEIGHT
}

def get_search_query(product: Dict[str, Any]) -> str:
    """Generate a search query for the product."""
    name = product.get('name', '').strip()
    brand = product.get('brand', '').strip()
    
    # Extract main product name without descriptors
    name_parts = name.split()
    # Remove common descriptive terms that might narrow results too much
    terms_to_remove = ['artificially', 'colored', 'imitation', 'style', 'flavored', 'processed', 'premium']
    main_terms = [word for word in name_parts if word.lower() not in terms_to_remove]
    
    # Take first 3 meaningful words
    simplified_name = " ".join(main_terms[:3])
    
    # Build the query
    query_parts = []
    if brand and len(brand.split()) <= 2:  # Only use short brand names
        query_parts.append(brand)
    query_parts.append(simplified_name)
    query_parts.append("product package")  # Add product package to focus on product images
    
    # Join and clean up extra spaces
    final_query = " ".join(query_parts).strip()
    logger.info(f"Search query for {name}: '{final_query}'")
    return final_query

async def validate_image(session: aiohttp.ClientSession, url: str) -> Tuple[bool, Optional[str]]:
    """Validate image URL and return if valid and any error message."""
    try:
        # Skip SVG images
        if url.lower().endswith('.svg'):
            return False, "SVG format not supported"
            
        # Skip data URLs
        if url.startswith('data:'):
            return False, "Data URLs not supported"
            
        # Validate URL format
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
            
        # Fetch image headers
        async with session.head(url, allow_redirects=True, timeout=10) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}"
                
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                return False, f"Not an image: {content_type}"
                
            # Skip small images (now 5KB minimum)
            content_length = int(response.headers.get('content-length', 0))
            if content_length < 5000:  # 5KB minimum
                return False, f"Image too small: {content_length} bytes"
                
            # Check image dimensions if available
            if 'content-disposition' in response.headers:
                dimensions = re.search(r'(\d+)x(\d+)', response.headers['content-disposition'])
                if dimensions:
                    width, height = map(int, dimensions.groups())
                    if width < 200 or height < 200:
                        return False, f"Image dimensions too small: {width}x{height}"
                        
        return True, None
        
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

async def search_images(session: aiohttp.ClientSession, query: str, retries: int = MAX_RETRIES) -> List[str]:
    """Search for images and return valid URLs."""
    search_engine = random.choice(SEARCH_ENGINES)
    encoded_query = quote(query)
    url = search_engine["url"].format(query=encoded_query)
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': search_engine["referer"]
    }
    
    for attempt in range(retries):
        try:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status != 200:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                    
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                image_urls = []
                
                # Extract image URLs from the page
                for img in soup.find_all('img'):
                    img_url = img.get('src')
                    if img_url and not img_url.startswith('data:'):
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        image_urls.append(img_url)
                
                # Filter out thumbnails and invalid formats
                image_urls = [url for url in image_urls if not any(x in url.lower() for x in ['thumb', 'icon', 'logo', '.svg'])]
                
                return image_urls
                
        except Exception as e:
            logger.warning(f"Search attempt {attempt + 1} failed: {str(e)}")
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    
    return []

def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise

def get_products_to_update(conn, batch_size: int) -> List[Dict[str, Any]]:
    """Get products that need image updates."""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM products 
                LIMIT %s
            """, (batch_size,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return []

def update_product(conn, product_id: str, new_image_url: str) -> bool:
    """Update a product's image URL in the database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE products
                SET image_url = %s,
                    last_updated = %s
                WHERE code = %s
            """, (new_image_url, datetime.now(), product_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {str(e)}")
        conn.rollback()
        return False

async def process_product(session: aiohttp.ClientSession, pool: asyncpg.Pool, product: Dict[str, Any]) -> None:
    """Process a single product and update its image if needed."""
    product_code = product['code']
    name = product['name']
    brand = product.get('brand', '')
    
    try:
        search_query = get_search_query(product)
        image_urls = await search_images(session, search_query)
        
        # Try each image URL until we find a valid one
        for url in image_urls:
            is_valid, error = await validate_image(session, url)
            if not is_valid:
                logging.info(f"Skipping invalid image for product {product_code} ({name}): {error}")
                continue
                
            try:
                # Download the actual image
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        continue
                        
                    image_data = await response.read()
                    
                    # Convert to base64
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    # Update database with new image
                    async with pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE products 
                            SET image_data = $1, 
                                image_url = $2,
                                last_updated = NOW()
                            WHERE code = $3
                            """,
                            image_base64, url, product_code
                        )
                        
                    logging.info(f"Successfully updated image for product {product_code} ({name})")
                    return
                    
            except Exception as e:
                logging.error(f"Error downloading image for product {product_code}: {str(e)}")
                continue
                
        logging.error(f"No valid images found for product {product_code} ({name})")
        
    except Exception as e:
        logging.error(f"Error processing product {product_code}: {str(e)}")

async def main():
    """Main function to process products without images."""
    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('image_update.log'),
            logging.StreamHandler()
        ]
    )
    
    # Load environment variables
    load_dotenv()
    
    # Create connection pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10
    )
    
    try:
        # Get products without images or with broken images
        async with pool.acquire() as conn:
            products = await conn.fetch(
                """
                SELECT code, name, brand 
                FROM products 
                WHERE image_data IS NULL 
                   OR image_url IS NULL 
                   OR image_url = ''
                LIMIT 10
                """
            )
            
        if not products:
            logging.info("No products found that need image updates")
            return
            
        # Process products
        async with aiohttp.ClientSession() as session:
            tasks = [process_product(session, pool, dict(p)) for p in products]
            await asyncio.gather(*tasks)
            
    except Exception as e:
        logging.error(f"Main process error: {str(e)}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main()) 