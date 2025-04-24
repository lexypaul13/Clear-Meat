#!/usr/bin/env python
"""
Verify Images Script
-------------------
This script checks the image data for specific products that were successfully updated
and generates an HTML file to view the results.
"""

import asyncpg
import asyncio
import base64
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    exit(1)

# Products that were successfully updated
PRODUCTS_TO_CHECK = [
    ('0017082875662', 'Original Turkey Crinkle-Cut Pepperoni'),
    ('8422947520014', 'Seitán en lonchas'),
    ('0017082878533', 'Tender Cuts Prime Rib Seasoning'),
    ('0017000031064', 'Corned Beef Hash')
]

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Product Image Verification</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .product-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }}
        .product-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .product-card h3 {{ margin-top: 0; color: #333; }}
        .product-card img {{ max-width: 100%; height: auto; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }}
        .product-info {{ font-size: 14px; color: #666; }}
        .timestamp {{ color: #999; font-size: 12px; }}
        .header {{ background: #333; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Product Image Verification</h1>
        <p>Generated on: {timestamp}</p>
    </div>
    <div class="product-grid">
        {product_cards}
    </div>
</body>
</html>
'''

PRODUCT_CARD_TEMPLATE = '''
<div class="product-card">
    <h3>{name}</h3>
    <div class="product-info">
        <p>Code: {code}</p>
        <p>Image Status: {image_status}</p>
        <p>Last Updated: {last_updated}</p>
    </div>
    <img src="{image_url}" alt="{name}">
    <div class="product-info">
        <p>Direct Image URL: <a href="{image_url}" target="_blank">{image_url}</a></p>
    </div>
</div>
'''

async def main():
    # Create connection pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    
    product_cards = []
    try:
        async with pool.acquire() as conn:
            for code, name in PRODUCTS_TO_CHECK:
                result = await conn.fetchrow(
                    """
                    SELECT code, name, image_url, 
                           CASE 
                               WHEN image_data IS NULL THEN 'No image data'
                               ELSE 'Has image data (' || length(image_data) || ' chars)'
                           END as image_status,
                           last_updated
                    FROM products 
                    WHERE code = $1
                    """,
                    code
                )
                
                if result:
                    # Create product card HTML
                    card_html = PRODUCT_CARD_TEMPLATE.format(
                        name=result['name'],
                        code=result['code'],
                        image_status=result['image_status'],
                        last_updated=result['last_updated'],
                        image_url=result['image_url']
                    )
                    product_cards.append(card_html)
                    
                    # Also print to console
                    print(f"\nProduct: {result['name']} (Code: {result['code']})")
                    print(f"Image URL: {result['image_url']}")
                    print(f"Image Status: {result['image_status']}")
                    print(f"Last Updated: {result['last_updated']}")
                else:
                    print(f"\nProduct not found: {name} (Code: {code})")
    finally:
        await pool.close()
    
    # Generate the complete HTML
    html_content = HTML_TEMPLATE.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        product_cards="\n".join(product_cards)
    )
    
    # Write to file
    with open("product_images.html", "w") as f:
        f.write(html_content)
    
    print("\nHTML file generated: product_images.html")

if __name__ == "__main__":
    asyncio.run(main()) 