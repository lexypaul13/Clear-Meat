#!/usr/bin/env python
"""
Display Product Images
-------------------
This script displays updated product images from Supabase.

Usage: python scripts/display_images.py --url SUPABASE_URL --key SUPABASE_KEY
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import logging
from supabase import create_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_html(products):
    html = """<!DOCTYPE html>
<html>
<head>
<title>Meat Products Gallery</title>
<style>
    body { font-family: Arial; margin: 20px; }
    .product { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
    img { max-width: 300px; max-height: 300px; }
</style>
</head>
<body>
<h1>Updated Meat Products</h1>
"""
    
    for product in products:
        name = product.get('name', 'Unknown')
        code = product.get('code', '')
        image_url = product.get('image_url', '')
        meat_type = product.get('meat_type', 'Unknown')
        
        html += f"""
<div class="product">
    <h2>{name} ({code})</h2>
    <p>Type: {meat_type}</p>
    <p><img src="{image_url}" alt="{name}" onerror="this.onerror=null; this.src='https://via.placeholder.com/300x200?text=No+Image'"></p>
    <p>Image URL: <a href="{image_url}" target="_blank">{image_url}</a></p>
</div>
"""
    
    html += """
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description='Display product images')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    args = parser.parse_args()
    
    supabase_url = args.url or os.getenv("SUPABASE_URL")
    supabase_key = args.key or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be provided")
        sys.exit(1)
    
    try:
        # Connect to Supabase
        supabase = create_client(supabase_url, supabase_key)
        
        # Get products updated in the last 2 hours
        two_hours_ago = (datetime.now() - timedelta(hours=2)).isoformat()
        
        response = supabase.table('products') \
            .select('code, name, image_url, meat_type, last_updated') \
            .gt('last_updated', two_hours_ago) \
            .order('last_updated', desc=True) \
            .execute()
        
        products = response.data
        
        if not products:
            logger.info("No products found with recent updates")
            return
        
        logger.info(f"Found {len(products)} recently updated products")
        
        # Generate HTML
        html = generate_html(products)
        
        # Write to file
        output_file = 'product_images.html'
        with open(output_file, 'w') as f:
            f.write(html)
        
        logger.info(f"Generated {output_file} - open this file in a browser to view images")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 