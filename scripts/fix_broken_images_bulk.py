#!/usr/bin/env python
"""
Fix Broken Images - Bulk Version
-------------------
This script processes all products with missing or broken image URLs in batches,
scraping the web for images and updating them in the Supabase database.

Usage: python scripts/fix_broken_images_bulk.py --url SUPABASE_URL --key SUPABASE_KEY
"""

import os
import sys
import time
import argparse
import logging
import concurrent.futures
from tqdm import tqdm
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import requests
from supabase import create_client
from bs4 import BeautifulSoup
import random
from urllib.parse import quote
import io
from PIL import Image
import socket
import http.client

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
BATCH_SIZE = 50  # Process products in batches of 50
DEFAULT_MAX_WORKERS = 5  # Number of parallel workers
MAX_RETRIES = 5  # Max retries for requests
RETRY_DELAY = 5  # Delay between retries in seconds
SUCCESS_LOG = "success_log.txt"
ERROR_LOG = "error_log.txt"
USE_PROXIES = False  # Set to True to enable proxy rotation

# Minimum acceptable image dimensions
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 200
MIN_IMAGE_SIZE_BYTES = 10000  # 10KB

# User agent strings for rotating to avoid rate limiting
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76'
]

# Proxy list - replace with your actual proxies if using
PROXIES = [
    # Format: {"http": "http://username:password@proxy-server:port", "https": "https://username:password@proxy-server:port"}
    {"http": "http://proxy1.example.com:8080", "https": "https://proxy1.example.com:8080"},
    {"http": "http://proxy2.example.com:8080", "https": "https://proxy2.example.com:8080"},
    {"http": "http://proxy3.example.com:8080", "https": "https://proxy3.example.com:8080"},
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

# Global configuration that will be updated from command-line args
config = {
    "max_workers": DEFAULT_MAX_WORKERS,
    "use_proxies": USE_PROXIES,
    "min_image_width": MIN_IMAGE_WIDTH,
    "min_image_height": MIN_IMAGE_HEIGHT
}


def get_search_query(product: Dict[str, Any]) -> str:
    """Generate a search query for the product."""
    name = product.get('name', '')
    code = product.get('code', '')
    meat_type = product.get('meat_type', '')
    
    # Build a specific search query
    query = f"{name} {code} {meat_type} meat product"
    
    # Remove very common words to make query more specific
    for common_word in ['the', 'a', 'an', 'of', 'and', 'or', 'for', 'with']:
        query = query.replace(f" {common_word} ", " ")
    
    return query.strip()


def get_proxy() -> Optional[Dict[str, str]]:
    """Get a random proxy from the list."""
    if not config["use_proxies"] or not PROXIES:
        return None
    return random.choice(PROXIES)


def validate_image(image_url: str, product_name: str) -> Tuple[bool, Union[str, Dict[str, Any]]]:
    """
    Validate the quality and relevance of an image.
    
    Returns:
        Tuple[bool, Union[str, Dict]]: (is_valid, result_or_error_message)
    """
    try:
        # Use different user agent for validation to avoid detection
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
        }
        
        # Add a small delay to appear more natural
        time.sleep(random.uniform(0.5, 1.5))
        
        # Download the image
        response = requests.get(image_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return False, f"Failed to download image: HTTP {response.status_code}"
            
        # Check image size in bytes
        image_size = len(response.content)
        if image_size < MIN_IMAGE_SIZE_BYTES:
            return False, f"Image too small: {image_size} bytes"
        
        # Check image dimensions and format
        try:
            img = Image.open(io.BytesIO(response.content))
            width, height = img.size
            format = img.format
            
            if width < config["min_image_width"] or height < config["min_image_height"]:
                return False, f"Image dimensions too small: {width}x{height}"
                
            # Check if image is likely to be a logo or icon
            if width == height and width < 300:
                # Square small images are often logos
                return False, "Image appears to be a logo or icon"
                
            # Check for transparent PNGs (often logos or graphics, not photos)
            if format == "PNG" and img.mode == 'RGBA':
                # Count transparent pixels
                transparent_pixels = 0
                for pixel in img.getdata():
                    if len(pixel) == 4 and pixel[3] == 0:  # RGBA with alpha=0
                        transparent_pixels += 1
                
                # If more than 20% of pixels are transparent, likely a logo
                if transparent_pixels > (width * height * 0.2):
                    return False, "Image appears to be a logo or graphic with transparency"
            
            # Calculate aspect ratio
            aspect_ratio = width / height
            
            # Analyze image relevance based on filename
            filename = image_url.split('/')[-1].lower()
            product_keywords = set(product_name.lower().split())
            common_words = {'the', 'a', 'an', 'of', 'in', 'for', 'and', 'with'}
            meaningful_keywords = product_keywords - common_words
            
            # If any meaningful keyword appears in the filename, it's a good sign
            keyword_match = any(keyword in filename for keyword in meaningful_keywords)
            
            # If the image is from a stock photo site, it's less likely to be specific to this product
            is_stock_photo = any(stock_site in image_url.lower() for stock_site in 
                               ['shutterstock', 'istockphoto', 'gettyimages', 'stock', 'depositphotos'])
            
            # Calculate a relevance score (higher is better)
            relevance_score = 0.5
            if keyword_match:
                relevance_score += 0.3
            if not is_stock_photo:
                relevance_score += 0.2
            
            return True, {
                "dimensions": (width, height),
                "size_bytes": image_size,
                "format": format,
                "aspect_ratio": aspect_ratio,
                "relevance_score": relevance_score
            }
            
        except Exception as img_error:
            return False, f"Invalid image format: {str(img_error)}"
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def search_images(query: str, retries: int = MAX_RETRIES) -> List[str]:
    """
    Search for images related to the query and return a list of image URLs.
    Uses multiple search engines and implements sophisticated rate limiting handling.
    """
    # Select a search engine to try
    search_engine = random.choice(SEARCH_ENGINES)
    encoded_query = quote(query)
    url = search_engine["url"].format(query=encoded_query)
    
    # Prepare headers with rotating user agent
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': search_engine["referer"],
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    # Exponential backoff variables
    min_delay = RETRY_DELAY  # Starting delay in seconds
    max_delay = 120  # Maximum delay in seconds
    
    for attempt in range(retries):
        try:
            # Get a random proxy if enabled
            proxies = get_proxy()
            
            # Add random delay with jitter to appear more human-like
            if attempt > 0:
                # Longer delay for retry attempts
                time.sleep(random.uniform(1, 3))
            
            # Set a longer timeout for the request
            timeout = 15
            
            # Make the request
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxies, 
                timeout=timeout
            )
            
            # Handle specific status codes
            if response.status_code == 429:  # Too Many Requests
                delay = min(max_delay, min_delay * (2 ** attempt)) + random.uniform(0, 2)
                logger.warning(f"Rate limited (429). Cooling down for {delay:.2f} seconds")
                time.sleep(delay)
                # Try a different search engine on the next attempt
                search_engine = random.choice([se for se in SEARCH_ENGINES if se["name"] != search_engine["name"]])
                url = search_engine["url"].format(query=encoded_query)
                headers['Referer'] = search_engine["referer"]
                continue
                
            elif response.status_code == 403:  # Forbidden - possible IP ban
                logger.warning(f"Access forbidden (403). Possibly banned temporarily.")
                # Try a different search engine with a new proxy
                search_engine = random.choice([se for se in SEARCH_ENGINES if se["name"] != search_engine["name"]])
                url = search_engine["url"].format(query=encoded_query)
                headers['User-Agent'] = random.choice(USER_AGENTS)  # New user agent
                headers['Referer'] = search_engine["referer"]
                time.sleep(min(max_delay, min_delay * (2 ** attempt)) + random.uniform(3, 7))
                continue
                
            elif response.status_code != 200:
                logger.warning(f"HTTP error: {response.status_code} on attempt {attempt+1}/{retries}")
                time.sleep(min_delay * (2 ** attempt) + random.uniform(0, 1))
                continue
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract image URLs
            img_tags = soup.find_all('img')
            image_urls = []
            
            for img in img_tags:
                img_url = img.get('src')
                if img_url and not img_url.startswith('data:'):
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    image_urls.append(img_url)
            
            # Sometimes we can also find URLs in JSON data within script tags
            try:
                for script in soup.find_all('script'):
                    if script.string and '"ou":"http' in script.string:
                        # This looks like a Google Images script with image data
                        # Extract URLs using simple string operations for efficiency
                        script_text = script.string
                        start_idx = 0
                        while True:
                            start_idx = script_text.find('"ou":"http', start_idx)
                            if start_idx == -1:
                                break
                            
                            start_idx += 6  # Skip past '"ou":"'
                            end_idx = script_text.find('"', start_idx)
                            if end_idx != -1:
                                img_url = script_text[start_idx:end_idx]
                                image_urls.append(img_url)
                                start_idx = end_idx
                            else:
                                break
            except Exception as e:
                logger.debug(f"Error extracting additional image URLs from scripts: {str(e)}")
            
            # Remove duplicate URLs
            image_urls = list(dict.fromkeys(image_urls))
            
            # Remove small thumbnail URLs (often contain "thumb" or specific dimensions)
            image_urls = [url for url in image_urls if not ('thumb' in url.lower() or 
                                                           any(dim in url for dim in ['x32', 'x48', 'x64']))]
            
            # Remove the first image if it's likely to be a logo
            if image_urls and ('logo' in image_urls[0].lower() or 'icon' in image_urls[0].lower()):
                image_urls = image_urls[1:]
            
            if image_urls:
                return image_urls
            else:
                logger.warning("No images found in the HTML response.")
                
                # If no images found, try a different search engine
                if attempt < retries - 1:
                    search_engine = random.choice([se for se in SEARCH_ENGINES if se["name"] != search_engine["name"]])
                    url = search_engine["url"].format(query=encoded_query)
                    headers['Referer'] = search_engine["referer"]
                    
        except requests.Timeout:
            logger.warning(f"Request timed out on attempt {attempt+1}/{retries}")
            # Try a different search engine on timeout
            search_engine = random.choice([se for se in SEARCH_ENGINES if se["name"] != search_engine["name"]])
            url = search_engine["url"].format(query=encoded_query)
            headers['Referer'] = search_engine["referer"]
            time.sleep(min_delay * (2 ** attempt) + random.uniform(0, 1))
            
        except (requests.RequestException, socket.error, http.client.HTTPException) as e:
            logger.warning(f"Attempt {attempt+1}/{retries} failed: {str(e)}")
            if attempt < retries - 1:
                # Use exponential backoff with jitter
                sleep_time = min(max_delay, min_delay * (2 ** attempt)) + random.uniform(0, 3)
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                logger.error(f"Failed to search for images after {retries} attempts: {str(e)}")
                return []
    
    return []


def process_product(supabase, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single product and update its image URL."""
    product_id = product.get('id')
    product_code = product.get('code', '')
    product_name = product.get('name', '')
    
    logger.info(f"Processing product: {product_name} ({product_code})")
    
    try:
        # Generate search query
        query = get_search_query(product)
        logger.info(f"Search query: {query}")
        
        # Search for images
        image_urls = search_images(query)
        
        if not image_urls:
            logger.warning(f"No images found for product: {product_name}")
            with open(ERROR_LOG, "a") as f:
                f.write(f"{datetime.now()} - No images found: {product_code} - {product_name}\n")
            return None
        
        # Try each image until finding a valid one
        valid_image = None
        validation_results = []
        
        # Check up to 5 images
        for idx, img_url in enumerate(image_urls[:5]):
            logger.info(f"Validating image {idx+1}/{min(5, len(image_urls))}: {img_url}")
            is_valid, result = validate_image(img_url, product_name)
            
            if is_valid:
                logger.info(f"Valid image found: {img_url}")
                logger.info(f"Validation result: {result}")
                valid_image = img_url
                
                # Store validation info
                validation_info = {
                    "url": img_url,
                    "validation": result
                }
                validation_results.append(validation_info)
                
                # If it has high relevance, use it immediately
                if result.get("relevance_score", 0) > 0.7:
                    break
            else:
                logger.info(f"Invalid image: {result}")
                # Store validation info for failed images too
                validation_results.append({
                    "url": img_url,
                    "validation_error": result
                })
            
            # Small delay between image validations
            time.sleep(random.uniform(0.5, 1.5))
        
        if not valid_image:
            logger.warning(f"No valid images found for product: {product_name}")
            logger.warning(f"Validation results: {validation_results}")
            with open(ERROR_LOG, "a") as f:
                f.write(f"{datetime.now()} - No valid images: {product_code} - {product_name}\n")
            return None
        
        # Update the product in the database
        update_response = supabase.table('products').update({
            'image_url': valid_image,
            'last_updated': datetime.now().isoformat(),
            'image_validation': validation_results
        }).eq('id', product_id).execute()
        
        if not update_response.data:
            logger.error(f"Failed to update product: {product_name}")
            with open(ERROR_LOG, "a") as f:
                f.write(f"{datetime.now()} - Update failed: {product_code} - {product_name}\n")
            return None
        
        logger.info(f"Product updated successfully: {product_name}")
        with open(SUCCESS_LOG, "a") as f:
            f.write(f"{datetime.now()} - Updated: {product_code} - {product_name} - {valid_image}\n")
        
        return {
            'code': product_code,
            'name': product_name,
            'image_url': valid_image
        }
        
    except Exception as e:
        logger.error(f"Error processing product {product_name}: {str(e)}")
        with open(ERROR_LOG, "a") as f:
            f.write(f"{datetime.now()} - Error: {product_code} - {product_name} - {str(e)}\n")
        return None


def get_products_with_missing_images(supabase, batch_size: int, offset: int) -> List[Dict[str, Any]]:
    """Get a batch of products with missing or invalid image URLs."""
    query = supabase.table('products').select('*')
    
    # Filter for products with missing, broken or empty image URLs
    query = query.or_(
        'image_url.is.null,image_url.eq.,image_url.like.%broken%,image_url.like.%unavailable%,image_url.like.%placeholder%'
    )
    
    # Add pagination
    query = query.range(offset, offset + batch_size - 1)
    
    # Execute the query
    response = query.execute()
    return response.data


def process_batch(supabase, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process a batch of products in parallel."""
    updated_products = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=config["max_workers"]) as executor:
        # Create a dictionary mapping futures to their product codes for tracking
        future_to_product = {
            executor.submit(process_product, supabase, product): product.get('code', '')
            for product in products
        }
        
        # Process futures as they complete
        for future in tqdm(concurrent.futures.as_completed(future_to_product), 
                          total=len(future_to_product), 
                          desc="Processing products"):
            product_code = future_to_product[future]
            try:
                result = future.result()
                if result:
                    updated_products.append(result)
            except Exception as e:
                logger.error(f"Exception processing product {product_code}: {str(e)}")
    
    return updated_products


def main():
    """Main function to process products with missing images."""
    parser = argparse.ArgumentParser(description='Fix missing product images in bulk')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help='Batch size for processing')
    parser.add_argument('--max-workers', type=int, default=DEFAULT_MAX_WORKERS, help='Maximum number of worker threads')
    parser.add_argument('--limit', type=int, help='Maximum number of products to process (optional)')
    parser.add_argument('--use-proxies', action='store_true', help='Enable proxy rotation')
    parser.add_argument('--min-width', type=int, default=MIN_IMAGE_WIDTH, help='Minimum image width')
    parser.add_argument('--min-height', type=int, default=MIN_IMAGE_HEIGHT, help='Minimum image height')
    args = parser.parse_args()
    
    supabase_url = args.url or os.getenv("SUPABASE_URL")
    supabase_key = args.key or os.getenv("SUPABASE_KEY")
    batch_size = args.batch_size
    limit = args.limit
    
    # Update global config from arguments
    config["max_workers"] = args.max_workers
    config["use_proxies"] = args.use_proxies
    config["min_image_width"] = args.min_width
    config["min_image_height"] = args.min_height
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be provided")
        sys.exit(1)
    
    # Initialize log files
    with open(SUCCESS_LOG, "w") as f:
        f.write(f"--- Started at {datetime.now()} ---\n")
    
    with open(ERROR_LOG, "w") as f:
        f.write(f"--- Started at {datetime.now()} ---\n")
    
    # Connect to Supabase
    try:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        sys.exit(1)
    
    # Initialize counters and lists
    total_processed = 0
    total_updated = 0
    all_updated_products = []
    offset = 0
    
    try:
        # Process products in batches
        while True:
            logger.info(f"Fetching batch with offset {offset}, batch size {batch_size}")
            
            # Get a batch of products
            products = get_products_with_missing_images(supabase, batch_size, offset)
            
            if not products:
                logger.info("No more products to process")
                break
            
            logger.info(f"Retrieved {len(products)} products to process")
            
            # Process the batch
            updated_products = process_batch(supabase, products)
            
            # Update counters
            total_processed += len(products)
            total_updated += len(updated_products)
            all_updated_products.extend(updated_products)
            
            logger.info(f"Processed {len(products)} products, updated {len(updated_products)}")
            
            # Update offset for next batch
            offset += batch_size
            
            # Check if we've reached the limit
            if limit and total_processed >= limit:
                logger.info(f"Reached processing limit of {limit} products")
                break
            
            # Add a variable delay between batches to avoid rate limiting
            # Longer delay if we had few successful updates (might indicate rate limiting)
            success_ratio = len(updated_products) / len(products) if products else 0
            if success_ratio < 0.3:
                # Low success ratio might indicate rate limiting, use longer delay
                delay = random.uniform(10, 20)
                logger.info(f"Low success ratio ({success_ratio:.2f}), using longer delay: {delay:.2f} seconds")
            else:
                delay = random.uniform(2, 5)
                logger.info(f"Normal delay between batches: {delay:.2f} seconds")
                
            time.sleep(delay)
        
        # Summary
        logger.info(f"Processing complete. Total processed: {total_processed}, Total updated: {total_updated}")
        
        # Final logs
        with open(SUCCESS_LOG, "a") as f:
            f.write(f"--- Completed at {datetime.now()} ---\n")
            f.write(f"Total processed: {total_processed}, Total updated: {total_updated}\n")
        
        with open(ERROR_LOG, "a") as f:
            f.write(f"--- Completed at {datetime.now()} ---\n")
            f.write(f"Total processed: {total_processed}, Total updated: {total_updated}\n")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
    finally:
        logger.info("Process completed")


if __name__ == "__main__":
    main() 