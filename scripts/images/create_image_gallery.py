#!/usr/bin/env python
"""
Create Image Gallery
-------------------
This script creates an HTML gallery to display the updated product images.

Usage: python scripts/create_image_gallery.py --url SUPABASE_URL --key SUPABASE_KEY
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import logging
from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meat Products Image Gallery</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        .product {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 15px;
            transition: transform 0.3s ease;
        }
        .product:hover {
            transform: translateY(-5px);
        }
        .product img {
            width: 100%;
            height: 200px;
            object-fit: contain;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .product h3 {
            margin: 0;
            color: #333;
        }
        .product p {
            color: #666;
            margin: 5px 0;
        }
        .meat-type {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .beef { background-color: #ffcdd2; }
        .pork { background-color: #f8bbd0; }
        .chicken { background-color: #c8e6c9; }
        .turkey { background-color: #bbdefb; }
        .lamb { background-color: #d1c4e9; }
        .mixed { background-color: #ffe0b2; }
        .other { background-color: #e0e0e0; }
    </style>
</head>
<body>
    <h1>Meat Products Image Gallery</h1>
    <p style="text-align: center;">Updated products as of {current_time}</p>
    
    <div class="gallery">
        {products_html}
    </div>
</body>
</html>"""

PRODUCT_TEMPLATE = """<div class="product">
    <img src="{image_url}" alt="{name}" onerror="this.src='https://via.placeholder.com/300x200?text=Image+Not+Found'">
    <h3>{name}</h3>
    <p>Code: {code}</p>
    <p>Type: <span class="meat-type {meat_type_lower}">{meat_type}</span></p>
    <p>Updated: {last_updated}</p>
</div>"""

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Create an HTML gallery of product images')
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
        
        # Build HTML for products
        products = response.data
        logger.info(f"Found {len(products)} recently updated products.")
        
        products_html = ""
        for product in products:
            # Clean up meat_type for CSS class
            meat_type = product.get('meat_type', 'other') or 'other'
            meat_type_lower = meat_type.lower()
            
            # Format last_updated to be more readable
            last_updated = product.get('last_updated', '')
            if last_updated:
                try:
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    last_updated = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            # Add product to HTML
            products_html += PRODUCT_TEMPLATE.format(
                image_url=product.get('image_url', ''),
                name=product.get('name', 'Unknown'),
                code=product.get('code', ''),
                meat_type=meat_type,
                meat_type_lower=meat_type_lower,
                last_updated=last_updated
            )
        
        # Create the final HTML
        html = HTML_TEMPLATE.format(
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            products_html=products_html
        )
        
        # Write to file
        output_file = 'meat_products_gallery.html'
        with open(output_file, 'w') as f:
            f.write(html)
        
        logger.info(f"Gallery created as '{output_file}'")
        logger.info(f"Open it in your browser to view the images.")
        
    except Exception as e:
        logger.error(f"Error creating gallery: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 