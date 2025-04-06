#!/usr/bin/env python
"""
Check Image Access
-----------------
This script checks if 10 random product images are accessible.

Usage: python scripts/check_image_access.py
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from app.db.session import SessionLocal
from sqlalchemy import text

def check_url(url):
    """Check if URL is accessible and returns an image"""
    try:
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/'):
                return True, f"✅ OK ({content_type})"
            else:
                return False, f"❌ Not an image ({content_type})"
        else:
            return False, f"❌ Status code {response.status_code}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def main():
    # Connect to database
    db = SessionLocal()
    
    # Get 10 random products with image URLs
    products = db.execute(text("""
        SELECT code, name, image_url 
        FROM products 
        WHERE image_url != '' AND image_url IS NOT NULL 
        ORDER BY RANDOM() 
        LIMIT 10
    """)).fetchall()
    
    if not products:
        print("No products with images found!")
        return
    
    # Check each product's image URL
    successful = 0
    for i, product in enumerate(products, 1):
        code = product[0]
        name = product[1]
        url = product[2]
        
        print(f"\n{i}. {name} ({code})")
        print(f"   URL: {url}")
        
        success, message = check_url(url)
        print(f"   Result: {message}")
        
        if success:
            successful += 1
    
    print(f"\nSummary: {successful}/10 image URLs are accessible ({successful*10}%)")

if __name__ == "__main__":
    main() 