"""
Product Collector Script
-----------------------
This script handles the collection of meat product data from the Open Food Facts API.
It includes functionality for initial collection and supplementary collection with
various search strategies.
"""

import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv
import asyncpg
from dataclasses import dataclass
from ratelimit import limits, sleep_and_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class SearchStrategy:
    """Configuration for a search strategy"""
    query: str
    category: str
    country: Optional[str] = None
    store: Optional[str] = None
    brand: Optional[str] = None
    sort_by: str = 'popularity'

class ProductCollector:
    def __init__(self):
        load_dotenv()
        self.db_url = os.getenv('DATABASE_URL')
        self.pool = None
        self.session = None
        self.processed_codes = set()
        self.target_count = 1000
        
        # Search strategies
        self.strategies = [
            # Basic meat categories
            SearchStrategy(query="meat", category="fresh-meat"),
            SearchStrategy(query="beef", category="fresh-beef"),
            SearchStrategy(query="pork", category="fresh-pork"),
            SearchStrategy(query="chicken", category="fresh-poultry"),
            
            # Country-specific searches
            SearchStrategy(query="meat", category="meat", country="United States"),
            SearchStrategy(query="meat", category="meat", country="United Kingdom"),
            SearchStrategy(query="meat", category="meat", country="Australia"),
            
            # Store-specific searches
            SearchStrategy(query="meat", category="meat", store="Walmart"),
            SearchStrategy(query="meat", category="meat", store="Kroger"),
            SearchStrategy(query="meat", category="meat", store="Whole Foods"),
            
            # Brand-specific searches
            SearchStrategy(query="meat", category="meat", brand="Tyson"),
            SearchStrategy(query="meat", category="meat", brand="Perdue"),
            SearchStrategy(query="meat", category="meat", brand="Smithfield"),
            
            # Processed meats
            SearchStrategy(query="sausage", category="meat-sausages"),
            SearchStrategy(query="ham", category="ham"),
            SearchStrategy(query="bacon", category="bacon"),
            
            # Specialty meats
            SearchStrategy(query="organic meat", category="meat"),
            SearchStrategy(query="grass-fed", category="meat"),
            SearchStrategy(query="free-range", category="meat")
        ]
        
        self.exhausted_strategies = set()

    async def setup(self):
        """Initialize database pool and HTTP session"""
        self.pool = await asyncpg.create_pool(self.db_url)
        self.session = aiohttp.ClientSession()
        
        # Load existing product codes
        async with self.pool.acquire() as conn:
            codes = await conn.fetch("SELECT code FROM products")
            self.processed_codes = {record['code'] for record in codes}

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.pool:
            await self.pool.close()

    @sleep_and_retry
    @limits(calls=100, period=60)
    async def get_products(self, strategy: SearchStrategy, page: int = 1) -> List[Dict]:
        """Fetch products from Open Food Facts API"""
        try:
            params = {
                'action': 'process',
                'json': 1,
                'page': page,
                'page_size': 50,
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
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('products', [])
                return []
        except Exception as e:
            logging.error(f"Error fetching products: {str(e)}")
            return []

    def _process_product_data(self, product: Dict) -> Optional[Dict]:
        """Process raw product data into structured format"""
        try:
            code = product.get('code')
            if not code or code in self.processed_codes:
                return None

            # Extract meat type
            categories = product.get('categories_tags', [])
            meat_type = 'unknown'
            for category in categories:
                if any(meat in category for meat in ['beef', 'pork', 'chicken', 'turkey', 'lamb', 'duck']):
                    meat_type = category.split(':')[-1]
                    break

            # Determine processing method
            processing_method = 'unknown'
            if any(tag in categories for tag in ['processed', 'cured', 'smoked']):
                processing_method = next(tag for tag in ['processed', 'cured', 'smoked'] 
                                      if tag in str(categories))
            elif 'fresh' in str(categories):
                processing_method = 'fresh'

            # Calculate risk rating
            risk_rating = self._calculate_risk_rating(product, processing_method)

            return {
                'code': code,
                'name': product.get('product_name', ''),
                'brand': product.get('brands', ''),
                'meat_type': meat_type,
                'processing_method': processing_method,
                'ingredients': product.get('ingredients_text', ''),
                'nutrition_grade': product.get('nutrition_grade_fr', 'unknown'),
                'risk_rating': risk_rating,
                'serving_size': product.get('serving_size', ''),
                'packaging': product.get('packaging', ''),
                'stores': product.get('stores', ''),
                'countries': product.get('countries', '')
            }
        except Exception as e:
            logging.error(f"Error processing product data: {str(e)}")
            return None

    def _calculate_risk_rating(self, product: Dict, processing_method: str) -> str:
        """Calculate risk rating based on product attributes"""
        try:
            # Base risk factors
            risk_factors = {
                'processing_method': {
                    'fresh': 1,
                    'smoked': 2,
                    'cured': 3,
                    'processed': 3,
                    'unknown': 2
                },
                'nutrition_grade': {
                    'a': 1,
                    'b': 1,
                    'c': 2,
                    'd': 2,
                    'e': 3,
                    'unknown': 2
                }
            }
            
            # Calculate base risk
            proc_risk = risk_factors['processing_method'].get(processing_method, 2)
            nutr_risk = risk_factors['nutrition_grade'].get(
                product.get('nutrition_grade_fr', 'unknown').lower(), 2
            )
            
            # Additional risk factors
            additives = len(product.get('additives_tags', []))
            if additives > 5:
                proc_risk += 1
                
            # Calculate final risk
            avg_risk = (proc_risk + nutr_risk) / 2
            
            if avg_risk <= 1.5:
                return 'low'
            elif avg_risk <= 2.5:
                return 'medium'
            else:
                return 'high'
        except Exception as e:
            logging.error(f"Error calculating risk rating: {str(e)}")
            return 'unknown'

    async def save_product(self, product: Dict) -> bool:
        """Save product to database"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO products (
                        code, name, brand, meat_type, processing_method,
                        ingredients, nutrition_grade, risk_rating,
                        serving_size, packaging, stores, countries
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (code) DO NOTHING
                """, 
                product['code'], product['name'], product['brand'],
                product['meat_type'], product['processing_method'],
                product['ingredients'], product['nutrition_grade'],
                product['risk_rating'], product['serving_size'],
                product['packaging'], product['stores'], product['countries']
                )
                self.processed_codes.add(product['code'])
                return True
        except Exception as e:
            logging.error(f"Error saving product: {str(e)}")
            return False

    async def collect_products(self):
        """Main collection method"""
        try:
            await self.setup()
            
            while len(self.processed_codes) < self.target_count and \
                  len(self.exhausted_strategies) < len(self.strategies):
                
                for strategy in self.strategies:
                    if strategy in self.exhausted_strategies:
                        continue
                        
                    empty_pages = 0
                    page = 1
                    new_products = 0
                    
                    while empty_pages < 3 and len(self.processed_codes) < self.target_count:
                        products = await self.get_products(strategy, page)
                        
                        if not products:
                            empty_pages += 1
                            continue
                            
                        for product in products:
                            if len(self.processed_codes) >= self.target_count:
                                break
                                
                            processed_product = self._process_product_data(product)
                            if processed_product and await self.save_product(processed_product):
                                new_products += 1
                                logging.info(f"Saved product {processed_product['code']} "
                                           f"({len(self.processed_codes)}/{self.target_count})")
                        
                        if new_products == 0:
                            empty_pages += 1
                        else:
                            empty_pages = 0
                            
                        page += 1
                        
                    if empty_pages >= 3:
                        self.exhausted_strategies.add(strategy)
                        logging.info(f"Strategy exhausted: {strategy.query} - {strategy.category}")
                        
            logging.info(f"Collection completed. Total products: {len(self.processed_codes)}")
            
        except Exception as e:
            logging.error(f"Error in collection process: {str(e)}")
        finally:
            await self.cleanup()

async def main():
    collector = ProductCollector()
    await collector.collect_products()

if __name__ == "__main__":
    asyncio.run(main()) 