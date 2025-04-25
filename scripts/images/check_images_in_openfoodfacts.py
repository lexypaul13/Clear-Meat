#!/usr/bin/env python
"""
OpenFoodFacts Image URL Checker
-------------------------------
This script analyzes the OpenFoodFacts JSONL file to check for image URLs.
It reports on the availability and formats of image URLs in the dataset.

Usage: python scripts/check_images_in_openfoodfacts.py [file_path] [sample_size]
  where [file_path] is the path to the JSONL file (default: ~/Downloads/openfoodfacts-products.jsonl)
  [sample_size] is the number of products to sample (default: 1000)
"""

import os
import json
import sys
import logging
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImageChecker:
    """Checks for image URLs in OpenFoodFacts data"""
    
    def __init__(self, file_path, sample_size=1000):
        """Initialize the checker"""
        self.file_path = file_path
        self.sample_size = sample_size
        self.processed_count = 0
        self.meat_products_found = 0
        self.products_with_images = 0
        self.image_field_counts = Counter()
        self.available_image_fields = set()
        
        # Example meat keywords for filtering meat products
        self.meat_keywords = {
            'beef': ['beef', 'bœuf', 'steak', 'boeuf'],
            'pork': ['pork', 'porc', 'ham', 'bacon', 'jambon', 'lard'],
            'chicken': ['chicken', 'poulet', 'poultry', 'volaille'],
            'turkey': ['turkey', 'dinde'],
            'lamb': ['lamb', 'agneau', 'mouton', 'sheep'],
            'duck': ['duck', 'canard'],
            'venison': ['venison', 'deer', 'cerf', 'gibier'],
            'bison': ['bison', 'buffalo'],
            'rabbit': ['rabbit', 'lapin'],
            'game': ['game', 'pheasant', 'quail']
        }
    
    def is_meat_product(self, product):
        """Check if the product is a meat product based on categories or ingredients"""
        if not product:
            return False
            
        # Check for categories
        categories = ' '.join(product.get('categories_tags', [])).lower()
        ingredients_text = product.get('ingredients_text', '').lower()
        
        # Look for meat keywords in categories and ingredients
        for meat_type, keywords in self.meat_keywords.items():
            if any(kw in categories for kw in keywords) or any(kw in ingredients_text for kw in keywords):
                return True
                
        return False
    
    def find_image_fields(self, product):
        """Find fields containing 'image' in the key name"""
        image_fields = {}
        for key, value in product.items():
            if 'image' in key.lower() and value:
                image_fields[key] = value
                self.available_image_fields.add(key)
        return image_fields
    
    def check_images(self):
        """Check for image URLs in the JSONL file"""
        try:
            logger.info(f"Starting image analysis from {self.file_path}")
            logger.info(f"Sample size: {self.sample_size}")
            
            file_size = os.path.getsize(self.file_path)
            logger.info(f"File size: {file_size / (1024 * 1024 * 1024):.2f} GB")
            
            meat_products_with_images = []
            meat_products_without_images = []
            
            with open(self.file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    try:
                        self.processed_count += 1
                        
                        # Log progress periodically
                        if self.processed_count % 10000 == 0:
                            logger.info(f"Processed {self.processed_count} lines, found {self.meat_products_found} meat products")
                        
                        # Parse JSON product
                        product = json.loads(line)
                        
                        # Check if it's a meat product
                        if self.is_meat_product(product):
                            self.meat_products_found += 1
                            
                            # Find all image-related fields
                            image_fields = self.find_image_fields(product)
                            
                            # Log the image fields
                            if image_fields:
                                self.products_with_images += 1
                                for field in image_fields:
                                    self.image_field_counts[field] += 1
                                
                                # Store sample products with images
                                if len(meat_products_with_images) < 5:
                                    sample_product = {
                                        'code': product.get('code', 'Unknown'),
                                        'name': product.get('product_name', 'Unknown'),
                                        'image_fields': image_fields
                                    }
                                    meat_products_with_images.append(sample_product)
                            else:
                                # Store sample products without images
                                if len(meat_products_without_images) < 5:
                                    sample_product = {
                                        'code': product.get('code', 'Unknown'),
                                        'name': product.get('product_name', 'Unknown')
                                    }
                                    meat_products_without_images.append(sample_product)
                            
                            # Check if we've reached our sample size
                            if self.meat_products_found >= self.sample_size:
                                logger.info(f"Reached sample size of {self.sample_size} meat products")
                                break
                                
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON at line {self.processed_count}")
                    except Exception as e:
                        logger.error(f"Error processing line {self.processed_count}: {str(e)}")
            
            # Report findings
            self.report_findings(meat_products_with_images, meat_products_without_images)
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
    
    def report_findings(self, with_images, without_images):
        """Report findings on image URLs"""
        logger.info("-" * 50)
        logger.info("IMAGE URL ANALYSIS RESULTS")
        logger.info("-" * 50)
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Meat products found: {self.meat_products_found}")
        logger.info(f"Products with image fields: {self.products_with_images}")
        
        if self.meat_products_found > 0:
            logger.info(f"Percentage of meat products with images: {self.products_with_images / self.meat_products_found:.2%}")
        
        logger.info("\nImage field distribution:")
        total_fields = sum(self.image_field_counts.values())
        for field, count in self.image_field_counts.most_common():
            logger.info(f"  {field}: {count} ({count / total_fields:.2%})")
        
        logger.info("\nAll available image fields:")
        for field in sorted(self.available_image_fields):
            logger.info(f"  {field}")
        
        logger.info("\nSample meat products WITH images:")
        for i, product in enumerate(with_images, 1):
            logger.info(f"\nProduct {i}:")
            logger.info(f"  Code: {product['code']}")
            logger.info(f"  Name: {product['name']}")
            logger.info(f"  Image Fields:")
            for field, url in product['image_fields'].items():
                logger.info(f"    {field}: {url}")
        
        logger.info("\nSample meat products WITHOUT images:")
        for i, product in enumerate(without_images, 1):
            logger.info(f"\nProduct {i}:")
            logger.info(f"  Code: {product['code']}")
            logger.info(f"  Name: {product['name']}")
        
        logger.info("-" * 50)


def main():
    # Get command line arguments
    file_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/openfoodfacts-products.jsonl")
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    # Validate file path
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    # Create checker and run
    checker = ImageChecker(file_path, sample_size)
    checker.check_images()

if __name__ == "__main__":
    main() 