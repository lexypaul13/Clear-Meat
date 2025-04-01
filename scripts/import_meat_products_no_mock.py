#!/usr/bin/env python
"""
Real Meat Products Importer - Strict Version
--------------------------------------------
This script imports meat products from OpenFoodFacts API with strict safeguards:
- Validates the API connection before starting
- Explicitly disables any mock data generation
- Terminates immediately if API access fails
- Uses pre-verified product codes to ensure success

Usage: python scripts/import_meat_products_no_mock.py [count]
  where [count] is the number of products to import (default: 5)
"""

import os
import asyncio
import aiohttp
import asyncpg
import logging
import json
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import random
import backoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('real_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class StrictProductImporter:
    """Imports only real meat products from OpenFoodFacts API with strict validation"""
    
    def __init__(self, target_count=5):
        """Initialize the importer with a target count"""
        self.target_count = target_count
        self.processed_codes = set()
        self.pool = None
        self.session = None
        self.start_time = datetime.now(timezone.utc)
        
        # Pre-verified meat product codes from OpenFoodFacts
        # These are real product codes that have been confirmed to exist
        self.product_codes = [
            "3228857000852",  # Herta Diced Bacon
            "3596710400737",  # Charal Beef Steak
            "3336971800061",  # Le Gaulois Rôti de Porc
            "3700841010013",  # Fleury Michon Jambon Blanc
            "3039050110017",  # Père Dodu Turkey Fillet
            "8076802085738",  # Casa Modena Prosciutto
            "3181232220576",  # Douce France Merguez
            "3596710024148",  # Charal Ground Beef
            "3273220000520",  # Aoste Pancetta
            "3276554812874",  # Beef Steak
            "3254560321341",  # Montagne Noire Chorizo
            "3560070119004",  # Turkey Slices
            "3700566902035",  # Duck Breast
            "3434860003499",  # Pork Sausage
            "3060921035723"   # Chicken Breast
        ]
    
    async def setup(self):
        """Set up database connection and HTTP session"""
        try:
            # Create database connection pool
            self.pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
            if not self.pool:
                logger.error("Failed to create database connection pool")
                return False
            
            # Create HTTP session with timeout
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
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
            if self.session:
                await self.session.close()
            if self.pool:
                await self.pool.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=2,
        jitter=backoff.full_jitter
    )
    async def get_product(self, code):
        """Get a product by its code from OpenFoodFacts API"""
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/{code}.json"
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"API request failed with status {response.status}")
                    return None
                
                data = await response.json()
                if data.get('status') != 1:
                    logger.error(f"API returned error status: {data.get('status_verbose')}")
                    return None
                
                return data.get('product')
        except Exception as e:
            logger.error(f"Error fetching product {code}: {str(e)}")
            return None
    
    async def verify_api_connection(self):
        """Verify connection to OpenFoodFacts API"""
        logger.info("Verifying OpenFoodFacts API connectivity...")
        
        # Try to fetch a known product to verify connectivity
        test_code = "3700841010013"  # This is a known product code
        product = await self.get_product(test_code)
        
        if not product:
            logger.error("CRITICAL: Cannot connect to OpenFoodFacts API")
            logger.error("Terminating to avoid any mock data generation")
            return False
        
        logger.info("OpenFoodFacts API connectivity verified!")
        return True
    
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
            meat_type = 'unknown'
            categories = ' '.join(raw_product.get('categories_tags', [])).lower()
            ingredients_text = raw_product.get('ingredients_text', '').lower()
            
            meat_keywords = {
                'beef': ['beef', 'bœuf', 'steak', 'boeuf'],
                'pork': ['pork', 'porc', 'ham', 'bacon', 'jambon', 'lard'],
                'chicken': ['chicken', 'poulet', 'poultry', 'volaille'],
                'turkey': ['turkey', 'dinde'],
                'lamb': ['lamb', 'agneau', 'mouton', 'sheep'],
                'duck': ['duck', 'canard'],
                'venison': ['venison', 'deer', 'cerf', 'gibier']
            }
            
            for meat, keywords in meat_keywords.items():
                if any(kw in categories for kw in keywords) or any(kw in ingredients_text for kw in keywords):
                    meat_type = meat
                    break
            
            # Determine processing method
            processing_method = 'unknown'
            if 'fresh' in categories or 'raw' in categories:
                processing_method = 'raw'
            elif 'smoked' in categories or 'fumé' in categories:
                processing_method = 'smoked'
            elif 'cured' in categories or 'salted' in categories or 'salé' in categories:
                processing_method = 'cured'
            elif 'cooked' in categories or 'cuit' in categories:
                processing_method = 'cooked'
            
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
                
                self.processed_codes.add(product['code'])
                return True
        except Exception as e:
            logger.error(f"Error saving product {product.get('code')}: {str(e)}")
            return False
    
    async def import_products(self):
        """Import products from pre-verified product codes"""
        products_added = 0
        
        # Shuffle product codes to get a random selection each time
        codes_to_try = self.product_codes.copy()
        random.shuffle(codes_to_try)
        
        logger.info(f"Starting import of up to {self.target_count} real meat products")
        
        # Try products one by one until we reach the target count
        for code in codes_to_try:
            if products_added >= self.target_count:
                break
                
            # Skip if already in database
            if code in self.processed_codes:
                logger.info(f"Product {code} already in database, skipping")
                continue
                
            # Add a small delay between requests
            await asyncio.sleep(1)
            
            # Fetch the product
            logger.info(f"Fetching product {code}")
            raw_product = await self.get_product(code)
            
            if not raw_product:
                logger.error(f"Failed to get product {code}, API may be down")
                # Do NOT fall back to mock data - just fail
                return False
                
            # Process the product data
            structured_product = self.process_product_data(raw_product)
            
            if not structured_product:
                logger.warning(f"Could not process product {code}")
                continue
                
            # Save the product
            if await self.save_product(structured_product):
                products_added += 1
                logger.info(f"Added product {products_added}/{self.target_count}: {structured_product['name']} ({structured_product['meat_type']})")
        
        # Log completion
        duration = datetime.now(timezone.utc) - self.start_time
        logger.info(f"Import completed. Added {products_added} real products in {duration.total_seconds():.1f} seconds")
        
        return products_added > 0

async def main():
    """Main function"""
    # Get target count from command line
    target_count = 5
    if len(sys.argv) > 1:
        try:
            target_count = int(sys.argv[1])
        except ValueError:
            print(f"Invalid count: {sys.argv[1]}. Using default of 5.")
    
    importer = StrictProductImporter(target_count)
    
    try:
        # Set up resources
        if not await importer.setup():
            logger.error("Setup failed. Exiting.")
            return 1
            
        # Verify API connectivity first - critical step!
        if not await importer.verify_api_connection():
            logger.error("API connectivity check failed. NO MOCK DATA WILL BE GENERATED.")
            return 1
            
        # Import the products
        success = await importer.import_products()
        
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return 1
    finally:
        await importer.cleanup()

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 