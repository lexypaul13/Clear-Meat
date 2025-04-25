"""
Data Enrichment Script
---------------------
This script handles the collection and management of enriched data for meat products,
including nutrition information, environmental impact, price history, and supply chain data.
It also includes functionality for data cleanup and validation.
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
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DataEnricher:
    def __init__(self):
        load_dotenv()
        self.db_url = os.getenv('DATABASE_URL')
        self.pool = None
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Validation mappings
        self.valid_meat_types = {'beef', 'pork', 'chicken', 'turkey', 'lamb', 'duck', 'unknown'}
        self.valid_processing_methods = {'processed', 'cured', 'smoked', 'fresh', 'unknown'}
        self.valid_stores = {'Walmart', 'Kroger', 'Whole Foods', 'Target'}
        self.valid_regions = {'Northeast', 'Southeast', 'Midwest', 'West'}
        
        # Track inconsistencies
        self.inconsistencies = {
            'missing_records': set(),
            'invalid_meat_types': set(),
            'invalid_processing_methods': set(),
            'invalid_nutrition': set(),
            'invalid_environmental': set()
        }

    async def setup(self):
        """Initialize database pool and HTTP session"""
        self.pool = await asyncpg.create_pool(self.db_url)
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.pool:
            await self.pool.close()
        self.executor.shutdown()

    @sleep_and_retry
    @limits(calls=100, period=60)
    async def fetch_nutrition_data(self, product_code: str) -> Optional[Dict]:
        """Fetch detailed nutrition data from Open Food Facts"""
        try:
            url = f"https://world.openfoodfacts.org/api/v2/product/{product_code}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 1:
                        product = data.get('product', {})
                        return {
                            'serving_size': product.get('serving_size'),
                            'serving_unit': product.get('serving_quantity_unit'),
                            'vitamins': json.dumps({
                                k.replace('vitamin-', ''): v 
                                for k, v in product.get('nutriments', {}).items() 
                                if 'vitamin' in k
                            }),
                            'minerals': json.dumps({
                                k: v 
                                for k, v in product.get('nutriments', {}).items() 
                                if any(mineral in k for mineral in ['iron', 'calcium', 'zinc', 'magnesium'])
                            }),
                            'allergens': product.get('allergens_tags', [])
                        }
                return None
        except Exception as e:
            logging.error(f"Error fetching nutrition data for {product_code}: {str(e)}")
            return None

    def calculate_environmental_impact(self, meat_type: str, processing_method: str) -> Dict:
        """Calculate environmental impact based on product data"""
        try:
            meat_type = (meat_type or 'unknown').lower()
            processing_method = (processing_method or 'unknown').lower()
            
            impact_data = {
                'beef': {'carbon': 60, 'water': 15400, 'land': 164},
                'pork': {'carbon': 7, 'water': 6000, 'land': 15},
                'chicken': {'carbon': 6, 'water': 4300, 'land': 12},
                'turkey': {'carbon': 10, 'water': 4300, 'land': 12},
                'lamb': {'carbon': 24, 'water': 10400, 'land': 185},
                'duck': {'carbon': 8, 'water': 4900, 'land': 14},
                'unknown': {'carbon': 20, 'water': 8000, 'land': 50}
            }
            
            base_impact = impact_data.get(meat_type, impact_data['unknown'])
            processing_factor = 1.2 if processing_method in ['processed', 'cured', 'smoked'] else 1.0
            
            return {
                'carbon_footprint_per_kg': base_impact['carbon'] * processing_factor,
                'water_usage_liters_per_kg': base_impact['water'] * processing_factor,
                'land_use_sqm_per_kg': base_impact['land'],
                'packaging_recyclable': True,  # Default assumption
                'source': 'calculated',
                'calculation_method': f'base_impact_{meat_type}_with_{processing_method}_factor'
            }
        except Exception as e:
            logging.error(f"Error calculating environmental impact: {str(e)}")
            return self.calculate_environmental_impact('unknown', 'unknown')

    async def determine_supply_chain(self, product: Dict) -> Dict:
        """Determine supply chain information based on product data"""
        meat_type = product.get('meat_type', '').lower()
        
        origin_mapping = {
            'beef': ['United States', 'Canada', 'Australia'],
            'pork': ['United States', 'Canada', 'Denmark'],
            'chicken': ['United States', 'Brazil', 'Thailand'],
            'turkey': ['United States', 'Canada'],
            'lamb': ['New Zealand', 'Australia'],
            'duck': ['United States', 'France', 'China']
        }
        
        origins = origin_mapping.get(meat_type, ['United States'])
        
        return {
            'origin_country': 'Unknown',
            'processing_location': product.get('manufacturing_places', 'Unknown'),
            'distribution_method': 'refrigerated_transport',
            'storage_requirements': 'refrigerated',
            'shelf_life_days': 14 if product.get('processing_method') == 'fresh' else 30,
            'certifications': product.get('labels_tags', [])
        }

    async def check_data_consistency(self):
        """Check for data inconsistencies across all tables"""
        async with self.pool.acquire() as conn:
            # Get all product codes
            products = await conn.fetch("SELECT code, meat_type, processing_method FROM products")
            product_codes = {record['code'] for record in products}
            
            # Check for invalid meat types and processing methods
            for record in products:
                if record['meat_type'] and record['meat_type'].lower() not in self.valid_meat_types:
                    self.inconsistencies['invalid_meat_types'].add(record['code'])
                if record['processing_method'] and record['processing_method'].lower() not in self.valid_processing_methods:
                    self.inconsistencies['invalid_processing_methods'].add(record['code'])

            # Check nutrition data
            nutrition_records = await conn.fetch("""
                SELECT product_code, serving_size, serving_unit, vitamins, minerals
                FROM product_nutrition
            """)
            for record in nutrition_records:
                if not self._validate_nutrition_data(record):
                    self.inconsistencies['invalid_nutrition'].add(record['product_code'])

            # Check environmental impact data
            env_records = await conn.fetch("""
                SELECT product_code, carbon_footprint_per_kg, water_usage_liters_per_kg, land_use_sqm_per_kg
                FROM environmental_impact
            """)
            for record in env_records:
                if not self._validate_environmental_data(record):
                    self.inconsistencies['invalid_environmental'].add(record['product_code'])

            # Check price history
            price_records = await conn.fetch("""
                SELECT product_code, store, region, COUNT(*) as count
                FROM price_history
                GROUP BY product_code, store, region
                HAVING COUNT(*) > 1
            """)
            for record in price_records:
                self.inconsistencies['duplicate_prices'].add(record['product_code'])

            # Check for missing records across tables
            tables = ['product_nutrition', 'environmental_impact', 'supply_chain']
            for table in tables:
                table_records = await conn.fetch(f"SELECT product_code FROM {table}")
                table_codes = {record['product_code'] for record in table_records}
                missing = product_codes - table_codes
                if missing:
                    self.inconsistencies['missing_records'].update(missing)

            return self.inconsistencies

    def _validate_nutrition_data(self, record: Dict) -> bool:
        """Validate nutrition data"""
        try:
            if not record['serving_size'] or not record['serving_unit']:
                return False

            vitamins = json.loads(record['vitamins'])
            if not isinstance(vitamins, dict):
                return False

            minerals = json.loads(record['minerals'])
            if not isinstance(minerals, dict):
                return False

            return True
        except (json.JSONDecodeError, TypeError):
            return False

    def _validate_environmental_data(self, record: Dict) -> bool:
        """Validate environmental impact data"""
        try:
            if any(record[field] < 0 for field in ['carbon_footprint_per_kg', 'water_usage_liters_per_kg', 'land_use_sqm_per_kg']):
                return False

            if record['carbon_footprint_per_kg'] > 1000 or \
               record['water_usage_liters_per_kg'] > 50000 or \
               record['land_use_sqm_per_kg'] > 1000:
                return False

            return True
        except (TypeError, KeyError):
            return False

    async def fix_inconsistencies(self):
        """Fix identified data inconsistencies"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Fix invalid meat types and processing methods
                for code in self.inconsistencies['invalid_meat_types']:
                    await conn.execute("""
                        UPDATE products 
                        SET meat_type = 'unknown'
                        WHERE code = $1
                    """, code)

                for code in self.inconsistencies['invalid_processing_methods']:
                    await conn.execute("""
                        UPDATE products 
                        SET processing_method = 'unknown'
                        WHERE code = $1
                    """, code)

                # Fix invalid nutrition data
                for code in self.inconsistencies['invalid_nutrition']:
                    await conn.execute("""
                        UPDATE product_nutrition
                        SET vitamins = '{}', minerals = '{}'
                        WHERE product_code = $1
                    """, code)

                # Fix invalid environmental data
                for code in self.inconsistencies['invalid_environmental']:
                    await conn.execute("""
                        UPDATE environmental_impact
                        SET carbon_footprint_per_kg = 20,
                            water_usage_liters_per_kg = 8000,
                            land_use_sqm_per_kg = 50
                        WHERE product_code = $1
                    """, code)

    async def process_product(self, product_code: str):
        """Process enriched data for a single product"""
        try:
            # Fetch all data concurrently
            nutrition_task = self.fetch_nutrition_data(product_code)
            
            # Get base product data from database
            async with self.pool.acquire() as conn:
                product = await conn.fetchrow(
                    "SELECT * FROM products WHERE code = $1",
                    product_code
                )
                
                if not product:
                    logging.warning(f"Product {product_code} not found in database.")
                    return
                
                # Convert to dict for easier handling
                product = dict(product)
                
                # Wait for async tasks
                nutrition_data = await nutrition_task
                
                # Calculate environmental impact
                env_impact = self.calculate_environmental_impact(
                    product.get('meat_type'),
                    product.get('processing_method')
                )
                
                # Get supply chain data
                supply_chain = await self.determine_supply_chain(product)
                
                # Save all data in a single transaction
                await self.save_enriched_data(
                    conn,
                    product_code,
                    nutrition_data,
                    env_impact,
                    supply_chain
                )
                
        except Exception as e:
            logging.error(f"Error processing product {product_code}: {str(e)}")

    async def save_enriched_data(
        self,
        conn: asyncpg.Connection,
        product_code: str,
        nutrition_data: Optional[Dict],
        env_impact: Dict,
        supply_chain: Dict
    ):
        """Save all enriched data to database"""
        try:
            async with conn.transaction():
                # Save nutrition data
                if nutrition_data:
                    await conn.execute("""
                        INSERT INTO product_nutrition (
                            product_code, serving_size, serving_unit,
                            vitamins, minerals, allergens
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (product_code) DO UPDATE SET
                            serving_size = EXCLUDED.serving_size,
                            serving_unit = EXCLUDED.serving_unit,
                            vitamins = EXCLUDED.vitamins,
                            minerals = EXCLUDED.minerals,
                            allergens = EXCLUDED.allergens
                    """,
                    product_code,
                    nutrition_data['serving_size'],
                    nutrition_data['serving_unit'],
                    nutrition_data['vitamins'],
                    nutrition_data['minerals'],
                    nutrition_data['allergens']
                    )
                
                # Save environmental impact
                await conn.execute("""
                    INSERT INTO environmental_impact (
                        product_code, carbon_footprint_per_kg,
                        water_usage_liters_per_kg, land_use_sqm_per_kg,
                        packaging_recyclable, source, calculation_method
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (product_code) DO UPDATE SET
                        carbon_footprint_per_kg = EXCLUDED.carbon_footprint_per_kg,
                        water_usage_liters_per_kg = EXCLUDED.water_usage_liters_per_kg,
                        land_use_sqm_per_kg = EXCLUDED.land_use_sqm_per_kg,
                        packaging_recyclable = EXCLUDED.packaging_recyclable,
                        source = EXCLUDED.source,
                        calculation_method = EXCLUDED.calculation_method
                """,
                product_code,
                env_impact['carbon_footprint_per_kg'],
                env_impact['water_usage_liters_per_kg'],
                env_impact['land_use_sqm_per_kg'],
                env_impact['packaging_recyclable'],
                env_impact['source'],
                env_impact['calculation_method']
                )
                
                # Save supply chain data
                await conn.execute("""
                    INSERT INTO supply_chain (
                        product_code, origin_country, processing_location,
                        distribution_method, storage_requirements,
                        shelf_life_days, certifications
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (product_code) DO UPDATE SET
                        origin_country = EXCLUDED.origin_country,
                        processing_location = EXCLUDED.processing_location,
                        distribution_method = EXCLUDED.distribution_method,
                        storage_requirements = EXCLUDED.storage_requirements,
                        shelf_life_days = EXCLUDED.shelf_life_days,
                        certifications = EXCLUDED.certifications
                """,
                product_code,
                supply_chain['origin_country'],
                supply_chain['processing_location'],
                supply_chain['distribution_method'],
                supply_chain['storage_requirements'],
                supply_chain['shelf_life_days'],
                supply_chain['certifications']
                )
                
        except Exception as e:
            logging.error(f"Error saving enriched data for {product_code}: {str(e)}")
            raise

    async def enrich_all_products(self):
        """Main method to enrich all products with additional data"""
        try:
            await self.setup()
            
            # Get all product codes
            async with self.pool.acquire() as conn:
                products = await conn.fetch("SELECT code FROM products")
            
            # Process products in batches
            batch_size = 10
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                tasks = [self.process_product(record['code']) for record in batch]
                await asyncio.gather(*tasks)
                logging.info(f"Processed {i + len(batch)}/{len(products)} products")
            
            # Check and fix data consistency
            logging.info("Checking data consistency...")
            await self.check_data_consistency()
            
            if any(self.inconsistencies.values()):
                logging.info("Fixing inconsistencies...")
                await self.fix_inconsistencies()
            
            logging.info("Data enrichment completed successfully")
            
        except Exception as e:
            logging.error(f"Error in enrichment process: {str(e)}")
        finally:
            await self.cleanup()

async def main():
    enricher = DataEnricher()
    await enricher.enrich_all_products()

if __name__ == "__main__":
    asyncio.run(main()) 