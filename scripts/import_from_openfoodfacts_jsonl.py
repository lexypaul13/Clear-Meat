#!/usr/bin/env python
"""
Bulk OpenFoodFacts JSONL Importer
---------------------------------
This script imports meat products from the OpenFoodFacts bulk JSONL file.
It processes the file incrementally to avoid memory issues with the large dataset.

Usage: python scripts/import_from_openfoodfacts_jsonl.py [file_path] [limit] [skip_lines]
  where [file_path] is the path to the JSONL file (default: ~/Downloads/openfoodfacts-products.jsonl)
  [limit] is the maximum number of products to import (default: 2000)
  [skip_lines] is the number of lines to skip before processing (default: 0)
"""

import os
import asyncio
import asyncpg
import logging
import json
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import random
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class MeatType(str, Enum):
    BEEF = "beef"
    PORK = "pork"
    CHICKEN = "chicken"
    TURKEY = "turkey"
    LAMB = "lamb"
    DUCK = "duck"
    VENISON = "venison"
    BISON = "bison"
    RABBIT = "rabbit"
    GAME = "game"
    UNKNOWN = "unknown"

class ProcessingMethod(str, Enum):
    RAW = "raw"
    SMOKED = "smoked"
    CURED = "cured"
    DRIED = "dried"
    COOKED = "cooked"
    FERMENTED = "fermented"
    UNKNOWN = "unknown"

class JSONLProductImporter:
    """Imports meat products from OpenFoodFacts JSONL file"""
    
    def __init__(self, file_path, target_count=2000, batch_size=100, skip_lines=0):
        """Initialize the importer with a target count and batch size"""
        self.file_path = file_path
        self.target_count = target_count
        self.batch_size = batch_size
        self.skip_lines = skip_lines
        self.processed_codes = set()
        self.imported_count = 0
        self.processed_count = 0
        self.meat_products_found = 0
        self.start_time = datetime.now(timezone.utc)
        self.pool = None
        
        # Meat keywords for product filtering
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
    
    async def setup(self):
        """Set up database connection"""
        try:
            # Create database connection pool
            self.pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
            if not self.pool:
                logger.error("Failed to create database connection pool")
                return False
            
            # Get existing product codes
            async with self.pool.acquire() as conn:
                existing_codes = await conn.fetch("SELECT code FROM products")
                self.processed_codes = set(record['code'] for record in existing_codes)
                logger.info(f"Found {len(self.processed_codes)} existing products in database")
                
            return True
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.pool:
                await self.pool.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
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
    
    def process_product_data(self, raw_product):
        """Process raw product data into structured format"""
        try:
            code = raw_product.get('code')
            if not code or code in self.processed_codes:
                return None
            
            # Skip products with no name or ingredients
            if not raw_product.get('product_name') or not raw_product.get('ingredients_text'):
                return None
            
            # Extract meat type
            meat_type = MeatType.UNKNOWN
            categories = ' '.join(raw_product.get('categories_tags', [])).lower()
            ingredients_text = raw_product.get('ingredients_text', '').lower()
            
            for meat, keywords in self.meat_keywords.items():
                if any(kw in categories for kw in keywords) or any(kw in ingredients_text for kw in keywords):
                    meat_type = meat
                    break
            
            # Determine processing method
            processing_method = ProcessingMethod.UNKNOWN
            
            processing_methods = {
                'raw': ['raw', 'fresh', 'uncooked', 'frais', 'cru'],
                'smoked': ['smoked', 'smoking', 'fumé'],
                'cured': ['cured', 'curing', 'salted', 'brined', 'salé', 'saumure'],
                'dried': ['dried', 'dehydrated', 'jerky', 'séché'],
                'cooked': ['cooked', 'roasted', 'boiled', 'grilled', 'cuit', 'rôti', 'bouilli', 'grillé'],
                'fermented': ['fermented', 'fermenting', 'fermentation', 'fermenté']
            }
            
            for method, keywords in processing_methods.items():
                if any(kw in categories for kw in keywords) or any(kw in ingredients_text for kw in keywords):
                    processing_method = method
                    break
            
            # Calculate risk rating
            risk_rating = "Yellow"  # Default medium risk
            if processing_method in ['cured', 'smoked']:
                risk_rating = "Red"  
            elif processing_method == 'raw':
                risk_rating = "Green"
            
            # Extract nutrients
            nutrients = raw_product.get('nutriments', {})
            
            # Create structured product data
            structured_data = {
                'code': code,
                'name': raw_product.get('product_name', ''),
                'brand': raw_product.get('brands', ''),
                'description': raw_product.get('generic_name', '') or raw_product.get('product_name', ''),
                'meat_type': meat_type,
                'processing_method': processing_method,
                'ingredients_text': raw_product.get('ingredients_text', ''),
                'risk_rating': risk_rating,
                'protein': nutrients.get('proteins_100g'),
                'fat': nutrients.get('fat_100g'),
                'carbohydrates': nutrients.get('carbohydrates_100g'),
                'salt': nutrients.get('salt_100g'),
                'image_url': raw_product.get('image_url', ''),
                'source': 'OpenFoodFacts',
            }
            
            return structured_data
        except Exception as e:
            logger.error(f"Error processing product data: {str(e)}")
            return None
    
    async def save_product(self, product):
        """Save product to database"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO products (
                        code, name, brand, description, ingredients_text, 
                        meat_type, protein, fat, carbohydrates, salt,
                        risk_rating, image_url, source, last_updated, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (code) DO NOTHING
                """, 
                product['code'], 
                product['name'], 
                product['brand'],
                product['description'], 
                product['ingredients_text'],
                product['meat_type'],
                product['protein'],
                product['fat'],
                product['carbohydrates'],
                product['salt'],
                product['risk_rating'],
                product['image_url'],
                product['source'],
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
                )
                
                self.imported_count += 1
                if self.imported_count % 10 == 0:
                    logger.info(f"Imported {self.imported_count} products so far")
                
                return True
        except Exception as e:
            logger.error(f"Error saving product {product.get('code')}: {str(e)}")
            return False
    
    async def process_batch(self, batch):
        """Process a batch of products"""
        tasks = []
        for raw_product in batch:
            product_data = self.process_product_data(raw_product)
            if product_data:
                tasks.append(self.save_product(product_data))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def import_products(self):
        """Import products from the JSONL file"""
        try:
            logger.info(f"Starting import from {self.file_path}")
            logger.info(f"Target count: {self.target_count}")
            logger.info(f"Skipping first {self.skip_lines} lines")
            
            file_size = os.path.getsize(self.file_path)
            logger.info(f"File size: {file_size / (1024 * 1024 * 1024):.2f} GB")
            
            batch = []
            with open(self.file_path, 'r', encoding='utf-8') as file:
                # Skip lines if specified
                if self.skip_lines > 0:
                    logger.info(f"Skipping {self.skip_lines} lines...")
                    for _ in range(self.skip_lines):
                        next(file, None)
                    logger.info(f"Skipped {self.skip_lines} lines. Starting processing.")
                
                for line_number, line in enumerate(file, 1 + self.skip_lines):
                    try:
                        self.processed_count += 1
                        
                        # Log progress periodically
                        if self.processed_count % 10000 == 0:
                            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                            logger.info(f"Processed {self.processed_count} lines, found {self.meat_products_found} meat products, imported {self.imported_count} products. Elapsed time: {elapsed:.2f}s")
                        
                        # Parse JSON product
                        product = json.loads(line)
                        
                        # Check if it's a meat product
                        if self.is_meat_product(product):
                            self.meat_products_found += 1
                            batch.append(product)
                            
                            # Process in batches
                            if len(batch) >= self.batch_size:
                                await self.process_batch(batch)
                                batch = []
                                
                                # Check if we've reached our target
                                if self.imported_count >= self.target_count:
                                    logger.info(f"Reached target count of {self.target_count} imported products")
                                    break
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON at line {line_number}")
                    except Exception as e:
                        logger.error(f"Error processing line {line_number}: {str(e)}")
            
            # Process remaining products
            if batch:
                await self.process_batch(batch)
                
            elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            logger.info(f"Import completed. Processed {self.processed_count} products, found {self.meat_products_found} meat products, imported {self.imported_count}. Elapsed time: {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
    
    def format_elapsed_time(self, seconds):
        """Format elapsed time in a human-readable way"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    async def log_statistics(self):
        """Log import statistics"""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        formatted_time = self.format_elapsed_time(elapsed)
        
        logger.info("-" * 50)
        logger.info("IMPORT STATISTICS")
        logger.info("-" * 50)
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Meat products found: {self.meat_products_found}")
        logger.info(f"Products imported: {self.imported_count}")
        logger.info(f"Elapsed time: {formatted_time}")
        if self.processed_count > 0:
            logger.info(f"Meat product ratio: {self.meat_products_found / self.processed_count:.2%}")
        if elapsed > 0:
            logger.info(f"Processing rate: {self.processed_count / elapsed:.2f} products/second")
            logger.info(f"Import rate: {self.imported_count / elapsed:.2f} products/second")
        logger.info("-" * 50)

async def main():
    # Get command line arguments
    file_path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/openfoodfacts-products.jsonl")
    target_count = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    skip_lines = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    # Validate file path
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    # Create importer and run
    importer = JSONLProductImporter(file_path, target_count, 100, skip_lines)
    
    try:
        if not await importer.setup():
            logger.error("Setup failed. Exiting.")
            return
            
        await importer.import_products()
        await importer.log_statistics()
    finally:
        await importer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
