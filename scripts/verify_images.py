#!/usr/bin/env python
"""
Verify Updated Images
-------------------
This script verifies that product images have been updated in Supabase.

Usage: python scripts/verify_images.py --url SUPABASE_URL --key SUPABASE_KEY
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import logging
from supabase import create_client
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Verify updated product images')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    return parser.parse_args()

def main():
    """Main function"""
    # Parse arguments
    args = parse_args()
    
    # Get Supabase credentials
    supabase_url = args.url or os.getenv("SUPABASE_URL")
    supabase_key = args.key or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be provided (via args or env vars)")
        sys.exit(1)
    
    # Connect to Supabase
    try:
        logger.info(f"Connecting to Supabase at {supabase_url[:30]}...")
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}")
        sys.exit(1)
    
    # Get recently updated products (in the last 2 hours)
    two_hours_ago = (datetime.now() - timedelta(hours=2)).isoformat()
    
    try:
        response = supabase.table('products') \
            .select('code, name, image_url, last_updated, meat_type') \
            .gt('last_updated', two_hours_ago) \
            .order('last_updated', desc=True) \
            .execute()
        
        if not hasattr(response, 'data') or not response.data:
            logger.info("No products updated in the last 2 hours.")
            return
        
        # Display updated products
        products = response.data
        logger.info(f"Found {len(products)} recently updated products.")
        
        # Display in a table
        table_data = []
        for i, product in enumerate(products[:10]):  # Show first 10
            table_data.append([
                i+1,
                product.get('code'),
                product.get('name'),
                product.get('meat_type'),
                product.get('image_url')[:60] + '...' if product.get('image_url') and len(product.get('image_url')) > 60 else product.get('image_url'),
                product.get('last_updated')
            ])
        
        headers = ["#", "Code", "Name", "Meat Type", "Image URL", "Last Updated"]
        print("\n=== RECENTLY UPDATED PRODUCTS ===\n")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Provide instructions for checking the images
        print("\nTo check an image, copy the URL and open it in your browser.")
        print("Or you can run a URL in the terminal with: open \"[image_url]\"")
        
    except Exception as e:
        logger.error(f"Error querying Supabase: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 