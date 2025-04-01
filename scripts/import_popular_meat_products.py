#!/usr/bin/env python
"""
Popular Meat Products Importer
-----------------------------
This script imports 2000 more meat products, prioritizing popular and frequently scanned items.
It builds on the existing product collector but with specific focus on popularity metrics.
"""

import os
import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timezone
from dotenv import load_dotenv
import asyncpg
from dataclasses import dataclass
from ratelimit import limits, sleep_and_retry
import sys
import uuid
import re
import random
import backoff
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("meat_product_import.log"),
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

class ProcessingMethod(str, Enum):
    RAW = "raw"
    SMOKED = "smoked"
    CURED = "cured"
    DRIED = "dried"
    COOKED = "cooked"
    FERMENTED = "fermented"

@dataclass
class SearchStrategy:
    query: str
    category: str
    sort_by: str = "popularity_key"
    country: str = "en:united-states"
    store: str = None
    brand: str = None

class PopularMeatProductImporter:
    def __init__(self, target_count: int = 2000):
        self.target_count = target_count
        self.processed_codes = set()
        self.pending_ingredients = set()
        self.start_time = None
        self.session = None
        self.pool = None
        self.strategies = [
            SearchStrategy("pork", "fresh-pork"),
            SearchStrategy("beef", "fresh-beef"),
            SearchStrategy("chicken", "fresh-chicken"),
            SearchStrategy("turkey", "fresh-turkey"),
            SearchStrategy("lamb", "fresh-lamb"),
            SearchStrategy("duck", "fresh-duck"),
            SearchStrategy("venison", "fresh-venison"),
            SearchStrategy("bacon", "bacon"),
            SearchStrategy("ham", "ham"),
            SearchStrategy("sausage", "meat-sausages"),
            SearchStrategy("meat", "meat")
        ]
        self.exhausted_strategies = set()

    async def setup(self):
        """Set up database connection and HTTP session"""
        try:
            # Set up database connection pool
            self.pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
            logger.info("Database connection pool created")

            # Set up HTTP session with timeout
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("HTTP session created")

            # Initialize start time
            self.start_time = datetime.now(timezone.utc)
            logger.info("Setup completed successfully")
        except Exception as e:
            logger.error(f"Error during setup: {str(e)}")
            raise

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.close()
            if self.pool:
                await self.pool.close()
            logger.info("Resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        jitter=backoff.full_jitter,
        max_time=30
    )
    async def get_products(self, strategy: SearchStrategy, page: int = 1) -> List[Dict]:
        """Fetch products from Open Food Facts API with retry logic"""
        try:
            logger.info(f"Fetching products for strategy: {strategy.query} - {strategy.category}, page {page}")
            logger.info(f"DEBUG: Using parameters: country={strategy.country}, sort_by={strategy.sort_by}")
            
            # Add delay between requests (2-4 seconds)
            await asyncio.sleep(random.uniform(2, 4))
            
            params = {
                'action': 'process',
                'json': 1,
                'page': page,
                'page_size': 25,  # Reduced page size to be more conservative
                'tagtype_0': 'categories',
                'tag_contains_0': 'contains',
                'tag_0': strategy.category,
                'sort_by': strategy.sort_by
            }
            
            if strategy.query:
                params['search_terms'] = strategy.query
            if strategy.country:
                params['tagtype_1'] = 'countries'
                params['tag_contains_1'] = 'contains'
                params['tag_1'] = strategy.country
            if strategy.store:
                params['tagtype_2'] = 'stores'
                params['tag_contains_2'] = 'contains'
                params['tag_2'] = strategy.store
            if strategy.brand:
                params['tagtype_3'] = 'brands'
                params['tag_contains_3'] = 'contains'
                params['tag_3'] = strategy.brand

            url = "https://world.openfoodfacts.org/cgi/search.pl"
            logger.info(f"DEBUG: Full URL parameters: {params}")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    products = data.get('products', [])
                    count = data.get('count', 0)
                    page_count = data.get('page_count', 0)
                    logger.info(f"Found {len(products)} products (total: {count}, pages: {page_count}) for strategy: {strategy.query} - {strategy.category}, page {page}")
                    
                    # Log first product details to verify real data
                    if products and len(products) > 0:
                        sample_product = products[0]
                        logger.info(f"DEBUG: Sample product: code={sample_product.get('code')}, name={sample_product.get('product_name')}, source=OpenFoodFacts")
                    
                    return products
                elif response.status == 429:  # Rate limit
                    logger.warning(f"Rate limited. Waiting 60 seconds before retry.")
                    await asyncio.sleep(60)  # Wait 60 seconds on rate limit
                    return []
                else:
                    logger.warning(f"API request failed with status {response.status}: {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []

    def _process_product_data(self, product: Dict) -> Optional[Dict]:
        """Process raw product data into structured format"""
        try:
            code = product.get('code')
            if not code or code in self.processed_codes:
                return None

            # Skip products with no ingredients
            if not product.get('ingredients_text'):
                return None

            # Skip products with no name
            if not product.get('product_name'):
                return None

            # Extract meat type
            categories = product.get('categories_tags', [])
            ingredients = product.get('ingredients_text', '').lower()
            
            meat_type = 'unknown'
            meat_types = {
                'beef': ['beef', 'cow', 'steak', 'brisket', 'chuck', 'sirloin'],
                'pork': ['pork', 'pig', 'ham', 'bacon', 'sausage', 'loin'],
                'chicken': ['chicken', 'poultry', 'hen', 'broiler'],
                'turkey': ['turkey'],
                'lamb': ['lamb', 'sheep', 'mutton'],
                'duck': ['duck'],
                'venison': ['venison', 'deer'],
                'bison': ['bison', 'buffalo'],
                'rabbit': ['rabbit'],
                'game': ['game', 'pheasant', 'quail']
            }
            
            # First check categories
            for category in categories:
                for meat, keywords in meat_types.items():
                    if any(kw in category for kw in keywords):
                        meat_type = meat
                        break
                if meat_type != 'unknown':
                    break
            
            # If still unknown, check ingredients
            if meat_type == 'unknown':
                for meat, keywords in meat_types.items():
                    if any(kw in ingredients for kw in keywords):
                        meat_type = meat
                        break

            # Determine processing method
            processing_method = 'unknown'
            processing_methods = {
                'raw': ['raw', 'fresh', 'uncooked'],
                'smoked': ['smoked', 'smoking'],
                'cured': ['cured', 'curing', 'salted', 'brined'],
                'dried': ['dried', 'dehydrated', 'jerky'],
                'cooked': ['cooked', 'roasted', 'grilled', 'baked'],
                'fermented': ['fermented', 'aged', 'cultured']
            }
            
            # Check categories and keywords for processing method
            for process, keywords in processing_methods.items():
                if any(kw in str(categories).lower() for kw in keywords) or any(kw in ingredients for kw in keywords):
                    processing_method = process
                    break
            
            # If still unknown but includes certain keywords, mark as processed
            if processing_method == 'unknown' and any(kw in ingredients for kw in ['preservative', 'nitrate', 'nitrite']):
                processing_method = 'processed'

            # Calculate risk rating
            risk_rating = self._calculate_risk_rating(product, processing_method)

            # Extract additional details
            animal_welfare = self._extract_animal_welfare(product)
            health_implications = self._extract_health_implications(product)

            # Prepare structured data
            structured_data = {
                'code': code,
                'name': product.get('product_name', ''),
                'brand': product.get('brands', ''),
                'description': product.get('generic_name', '') or product.get('product_name', ''),
                'meat_type': meat_type,
                'processing_method': processing_method,
                'ingredients_text': product.get('ingredients_text', ''),
                'risk_rating': risk_rating,
                'serving_size': product.get('serving_size', ''),
                'packaging': product.get('packaging', ''),
                'stores': product.get('stores', ''),
                'countries': product.get('countries', ''),
                'image_url': product.get('image_url', ''),
                'protein_per_100g': self._extract_nutrient(product, 'proteins_100g'),
                'fat_per_100g': self._extract_nutrient(product, 'fat_100g'),
                'carbs_per_100g': self._extract_nutrient(product, 'carbohydrates_100g'),
                'energy_per_100g': self._extract_nutrient(product, 'energy-kcal_100g'),
                'salt_per_100g': self._extract_nutrient(product, 'salt_100g'),
                'animal_welfare': json.dumps(animal_welfare),
                'health_implications': json.dumps(health_implications)
            }
            
            return structured_data
        except Exception as e:
            logger.error(f"Error processing product data: {str(e)}")
            return None

    def _calculate_risk_rating(self, product: Dict, processing_method: str) -> str:
        """Calculate risk rating based on product attributes"""
        try:
            # Initialize risk factors
            proc_risk = 1  # Base processing risk
            nutr_risk = 1  # Base nutritional risk
            additional_risk = 0  # Additional risk factors
            
            # Processing method risk
            if processing_method in ['cured', 'smoked', 'processed']:
                proc_risk = 3
            elif processing_method == 'raw':
                proc_risk = 1
            else:
                proc_risk = 2
                
            # Nutritional risk based on nutriments
            nutrients = product.get('nutriments', {})
            
            # Check protein content
            protein = nutrients.get('proteins_100g', 0)
            if isinstance(protein, (int, float)):
                if protein < 10:
                    nutr_risk += 1
                elif protein > 30:
                    nutr_risk += 0.5
                    
            # Check fat content
            fat = nutrients.get('fat_100g', 0)
            if isinstance(fat, (int, float)):
                if fat > 25:
                    additional_risk += 1
                elif fat > 15:
                    additional_risk += 0.5
                    
            # Check sodium content
            sodium = nutrients.get('sodium_100g', 0)
            if isinstance(sodium, (int, float)):
                if sodium > 1:
                    additional_risk += 1
                elif sodium > 0.5:
                    additional_risk += 0.5
            
            # Calculate final risk with additional factors
            avg_risk = (proc_risk + nutr_risk + additional_risk) / 3
            
            # Map to database acceptable values (Green, Yellow, Red)
            if avg_risk <= 1.5:
                return "Green"
            elif avg_risk <= 2.5:
                return "Yellow"
            else:
                return "Red"
        except Exception as e:
            logger.error(f"Error calculating risk rating: {str(e)}")
            return "Yellow"  # Default to Yellow as a fallback

    def _extract_nutrient(self, product: Dict, nutrient: str) -> Optional[float]:
        """Extract nutrient value from product data"""
        try:
            value = product.get('nutriments', {}).get(nutrient)
            if value is not None:
                return float(value)
            return None
        except (ValueError, TypeError):
            return None

    def _extract_animal_welfare(self, product: Dict) -> Dict:
        """Extract animal welfare information"""
        welfare_info = {
            'organic': False,
            'free_range': False,
            'grass_fed': False,
            'hormone_free': False,
            'antibiotic_free': False
        }
        
        # Check labels and categories
        labels = product.get('labels_tags', [])
        categories = product.get('categories_tags', [])
        
        welfare_keywords = {
            'organic': ['organic', 'bio', 'organic-certified'],
            'free_range': ['free-range', 'free range', 'pasture-raised'],
            'grass_fed': ['grass-fed', 'grass fed', 'pasture-fed'],
            'hormone_free': ['hormone-free', 'no-hormones', 'hormone free'],
            'antibiotic_free': ['antibiotic-free', 'no-antibiotics', 'antibiotic free']
        }
        
        for welfare_type, keywords in welfare_keywords.items():
            if any(kw in str(labels).lower() for kw in keywords) or any(kw in str(categories).lower() for kw in keywords):
                welfare_info[welfare_type] = True
                
        return welfare_info

    def _extract_health_implications(self, product: Dict) -> Dict:
        """Extract health implications information"""
        health_info = {
            'contains_nitrates': False,
            'contains_nitrites': False,
            'contains_additives': False,
            'high_sodium': False,
            'high_fat': False
        }
        
        # Check ingredients
        ingredients = product.get('ingredients_text', '').lower()
        
        # Check for nitrates/nitrites
        if any(n in ingredients for n in ['nitrate', 'nitrite']):
            health_info['contains_nitrates'] = True
            health_info['contains_nitrites'] = True
            
        # Check for additives
        if any(a in ingredients for a in ['preservative', 'additive', 'artificial']):
            health_info['contains_additives'] = True
            
        # Check nutritional values
        nutrients = product.get('nutriments', {})
        
        # Check sodium
        sodium = nutrients.get('sodium_100g', 0)
        if isinstance(sodium, (int, float)) and sodium > 0.5:
            health_info['high_sodium'] = True
            
        # Check fat
        fat = nutrients.get('fat_100g', 0)
        if isinstance(fat, (int, float)) and fat > 15:
            health_info['high_fat'] = True
            
        return health_info

    def _calculate_risk_score(self, product: Dict) -> float:
        """Calculate risk score based on product attributes"""
        try:
            # Base risk score
            risk_score = 0.0
            
            # Processing method risk
            processing_risk = {
                'raw': 0.2,
                'cooked': 0.4,
                'smoked': 0.6,
                'cured': 0.7,
                'dried': 0.5,
                'fermented': 0.3,
                'processed': 0.8,
                'unknown': 0.5
            }
            risk_score += processing_risk.get(product.get('processing_method', 'unknown'), 0.5)
            
            # Nutritional risk
            if product.get('fat_per_100g', 0) > 15:
                risk_score += 0.2
            if product.get('salt_per_100g', 0) > 0.5:
                risk_score += 0.2
                
            # Additive risk
            health_implications = json.loads(product.get('health_implications', '{}'))
            if health_implications.get('contains_nitrates'):
                risk_score += 0.3
            if health_implications.get('contains_additives'):
                risk_score += 0.2
                
            return min(risk_score, 1.0)  # Cap at 1.0
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 0.5  # Default to medium risk

    async def save_product(self, product: Dict) -> bool:
        """Save product to database"""
        try:
            # Map risk rating to database acceptable values
            risk_rating_map = {
                'Green': 'Green',
                'Yellow': 'Yellow',
                'Red': 'Red'
            }
            risk_rating = risk_rating_map.get(product['risk_rating'], 'Yellow')  # Default to Yellow if unknown

            # Map the values to match the actual database schema
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO products (
                        code, name, brand, description, ingredients_text, 
                        meat_type, protein, fat, carbohydrates, salt,
                        risk_rating, risk_score, image_url, source, last_updated,
                        created_at, contains_nitrites, contains_phosphates, 
                        contains_preservatives, antibiotic_free, hormone_free, 
                        pasture_raised
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, 
                             $14, $15, $16, $17, $18, $19, $20, $21, $22)
                    ON CONFLICT (code) DO NOTHING
                """, 
                product['code'], 
                product['name'], 
                product['brand'],
                product['description'], 
                product['ingredients_text'],
                product['meat_type'],
                product['protein_per_100g'],
                product['fat_per_100g'],
                product['carbs_per_100g'],
                product['salt_per_100g'],
                risk_rating,  # Using mapped risk rating value
                self._calculate_risk_score(product),
                product['image_url'],
                'OpenFoodFacts',
                datetime.now(timezone.utc),
                datetime.now(timezone.utc),
                self._extract_health_implication(product, 'contains_nitrates'),
                False,  # contains_phosphates - default to false
                self._extract_health_implication(product, 'contains_additives'),
                self._extract_welfare_attribute(product, 'no_antibiotics'),
                self._extract_welfare_attribute(product, 'no_hormones'),
                self._extract_welfare_attribute(product, 'grass_fed')
                )
                
                self.processed_codes.add(product['code'])
                
                # Add to pending ingredients for later processing
                if product['ingredients_text']:
                    self.pending_ingredients.add(product['code'])
                
                return True
        except Exception as e:
            logger.error(f"Error saving product {product.get('code')}: {str(e)}")
            return False

    def _extract_health_implication(self, product: Dict, implication: str) -> bool:
        """Extract specific health implication"""
        try:
            health_implications = json.loads(product.get('health_implications', '{}'))
            return health_implications.get(implication, False)
        except:
            return False

    def _extract_welfare_attribute(self, product: Dict, attribute: str) -> bool:
        """Extract specific welfare attribute"""
        try:
            welfare_info = json.loads(product.get('animal_welfare', '{}'))
            return welfare_info.get(attribute, False)
        except:
            return False

    async def process_ingredients(self):
        """Process ingredients for pending products"""
        try:
            if not self.pending_ingredients:
                return

            logger.info(f"Processing ingredients for {len(self.pending_ingredients)} products")
            
            async with self.pool.acquire() as conn:
                for code in self.pending_ingredients:
                    # Get product ingredients
                    product = await conn.fetchrow(
                        "SELECT ingredients_text FROM products WHERE code = $1",
                        code
                    )
                    
                    if not product or not product['ingredients_text']:
                        continue
                        
                    # Process ingredients
                    ingredients = self._parse_ingredients(product['ingredients_text'])
                    
                    # Save ingredients and relationships
                    for ingredient in ingredients:
                        # Insert ingredient
                        ingredient_id = await conn.fetchval("""
                            INSERT INTO ingredients (name)
                            VALUES ($1)
                            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                            RETURNING id
                        """, ingredient)
                        
                        # Insert relationship
                        await conn.execute("""
                            INSERT INTO product_ingredients (product_code, ingredient_id)
                            VALUES ($1, $2)
                            ON CONFLICT DO NOTHING
                        """, code, ingredient_id)
            
            logger.info("Finished processing ingredients batch")
            self.pending_ingredients.clear()
            
        except Exception as e:
            logger.error(f"Error processing ingredients: {str(e)}")

    def _parse_ingredients(self, ingredients_text: str) -> List[str]:
        """Parse ingredients text into list of ingredients"""
        try:
            # Split by common separators
            ingredients = []
            for part in ingredients_text.split(','):
                # Clean up each ingredient
                ingredient = part.strip()
                if ingredient:
                    # Remove common prefixes and suffixes
                    ingredient = re.sub(r'^(en:|fr:|es:|de:|it:)?', '', ingredient)
                    ingredient = re.sub(r'\([^)]*\)', '', ingredient)  # Remove parenthetical notes
                    ingredient = ingredient.strip()
                    if ingredient:
                        ingredients.append(ingredient)
            return ingredients
        except Exception as e:
            logger.error(f"Error parsing ingredients: {str(e)}")
            return []

    async def collect_products(self):
        """Collect products from all strategies"""
        products_added = 0
        strategy_index = 0
        page_number = 1
        retries = 0
        
        logger.info(f"Starting collection of {self.target_count} popular meat products")
        logger.info(f"Using {len(self.strategies)} search strategies")
        
        # Add periodic status updates
        last_status_time = time.time()
        status_interval = 60  # Log status every minute
        
        while products_added < self.target_count and len(self.exhausted_strategies) < len(self.strategies):
            # Get current strategy based on round-robin with popularity weighting
            strategy = self.strategies[strategy_index]
            strategy_index = (strategy_index + 1) % len(self.strategies)
            
            # Skip exhausted strategies
            if strategy in self.exhausted_strategies:
                continue
                
            # Add delay between strategies (5-10 seconds)
            await asyncio.sleep(random.uniform(5, 10))
            
            # Log status update periodically
            current_time = time.time()
            if current_time - last_status_time >= status_interval:
                elapsed = current_time - self.start_time
                logger.info(f"STATUS: Progress {products_added}/{self.target_count} products ({products_added/self.target_count*100:.1f}%)")
                logger.info(f"STATUS: Elapsed time: {self.format_elapsed_time(elapsed)}")
                logger.info(f"STATUS: Active strategies: {len(self.strategies) - len(self.exhausted_strategies)}/{len(self.strategies)}")
                logger.info(f"STATUS: Current strategy: {strategy.query} - {strategy.category}")
                if products_added > 0:
                    rate = products_added / elapsed if elapsed > 0 else 0
                    eta = (self.target_count - products_added) / rate if rate > 0 else "unknown"
                    logger.info(f"STATUS: Rate: {rate:.2f} products/sec, ETA: {self.format_elapsed_time(eta) if isinstance(eta, (int, float)) else eta}")
                last_status_time = current_time
            
            # Fetch products for current strategy
            products = await self.get_products(strategy, page_number)
            
            if not products:
                logger.warning(f"No products found for strategy: {strategy.query} - {strategy.category}, page {page_number}")
                self.exhausted_strategies.add(strategy)
                continue
            
            # Process products
            for product in products:
                if products_added >= self.target_count:
                    break
                    
                processed_product = self._process_product_data(product)
                if processed_product:
                    if await self.save_product(processed_product):
                        products_added += 1
                        logger.info(f"Added product: {processed_product['code']} - {processed_product['name']} ({processed_product['meat_type']}, {processed_product['processing_method']})")
                        
                        # Process ingredients periodically
                        if len(self.pending_ingredients) >= 60:
                            await self.process_ingredients()
            
            # Move to next page
            page_number += 1
            
            # If we've tried too many pages without success, mark strategy as exhausted
            if page_number > 100:  # Limit to 100 pages per strategy
                logger.warning(f"Strategy exhausted after {page_number} pages: {strategy.query} - {strategy.category}")
                self.exhausted_strategies.add(strategy)
                page_number = 1
        
        logger.info(f"Collection completed. Added {products_added} products out of target {self.target_count}")
        
        # Process any remaining ingredients
        if self.pending_ingredients:
            await self.process_ingredients()
        
        # Log final statistics
        await self.log_statistics()

    def format_elapsed_time(self, seconds: float) -> str:
        """Format elapsed time in a human-readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours}h {minutes}m {seconds}s"

    async def log_statistics(self):
        """Log final statistics"""
        try:
            async with self.pool.acquire() as conn:
                # Get total counts
                total_products = await conn.fetchval("SELECT COUNT(*) FROM products")
                total_ingredients = await conn.fetchval("SELECT COUNT(*) FROM ingredients")
                total_relationships = await conn.fetchval("SELECT COUNT(*) FROM product_ingredients")
                
                # Get meat type distribution
                meat_distribution = await conn.fetch("""
                    SELECT meat_type, COUNT(*) as count
                    FROM products
                    GROUP BY meat_type
                    ORDER BY count DESC
                """)
                
                # Calculate duration
                duration = datetime.now(timezone.utc) - self.start_time
                
                # Log statistics
                logger.info("Import statistics:")
                logger.info(f"import_duration: {self.format_elapsed_time(duration.total_seconds())}")
                logger.info(f"products_added: {self.target_count}")
                logger.info(f"total_products: {total_products}")
                logger.info(f"total_ingredients: {total_ingredients}")
                logger.info(f"total_ingredient_relationships: {total_relationships}")
                
                logger.info("Meat type distribution:")
                for meat in meat_distribution:
                    logger.info(f"  - {meat['meat_type']}: {meat['count']}")
                
        except Exception as e:
            logger.error(f"Error logging statistics: {str(e)}")

async def main():
    """Main function"""
    importer = PopularMeatProductImporter()
    try:
        await importer.setup()
        
        # Verify connectivity to OpenFoodFacts API
        logger.info("Checking OpenFoodFacts API connectivity...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://world.openfoodfacts.org/api/v0/product/737628064502.json") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data.get('status') == 1:
                            logger.info("OpenFoodFacts API connectivity verified!")
                        else:
                            logger.error(f"OpenFoodFacts API returned unexpected response: {data}")
                    else:
                        logger.error(f"OpenFoodFacts API connectivity check failed with status {response.status}")
        except Exception as e:
            logger.error(f"OpenFoodFacts API connectivity check failed: {str(e)}")
        
        await importer.collect_products()
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
    finally:
        await importer.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 