#!/usr/bin/env python3
"""
Cache warming script for health assessments.
Pre-generates assessments for popular products to avoid timeouts.
"""

import asyncio
import logging
from typing import List, Dict, Any
from app.db.supabase_client import get_supabase_service
from app.services.health_assessment_mcp_service import HealthAssessmentMCPService
from app.utils import helpers
from app.core.cache import cache, CacheService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def warm_cache_for_product(code: str, supabase_service, mcp_service) -> bool:
    """Pre-generate and cache health assessment for a single product."""
    try:
        logger.info(f"Warming cache for product {code}")
        
        # Check if already cached
        cache_key = CacheService.generate_key(code, prefix="health_assessment_mcp_v27_working_citations")
        if cache.get(cache_key):
            logger.info(f"Product {code} already cached, skipping")
            return True
        
        # Fetch product data
        product_data = supabase_service.get_product_by_code(code)
        if not product_data:
            logger.warning(f"Product {code} not found")
            return False
        
        # Structure product data
        structured_product = helpers.structure_product_data(product_data)
        if not structured_product:
            logger.warning(f"Failed to structure product {code}")
            return False
        
        # Generate assessment with 60 second timeout
        existing_risk_rating = product_data.get('risk_rating')
        try:
            assessment = await asyncio.wait_for(
                mcp_service.generate_health_assessment_with_real_evidence(
                    structured_product,
                    existing_risk_rating=existing_risk_rating
                ),
                timeout=60
            )
            
            if assessment:
                logger.info(f"✅ Successfully cached assessment for {code}")
                return True
            else:
                logger.warning(f"Failed to generate assessment for {code}")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout generating assessment for {code}")
            # Create and cache fallback assessment
            fallback = mcp_service.create_minimal_fallback_assessment(
                structured_product, existing_risk_rating or "Yellow"
            )
            cache.set(cache_key, fallback, ttl=86400)  # Cache fallback for 24 hours
            logger.info(f"Cached fallback assessment for {code}")
            return True
            
    except Exception as e:
        logger.error(f"Error warming cache for {code}: {e}")
        return False


async def get_popular_products(supabase_service, limit: int = 50) -> List[str]:
    """Get list of popular product codes to warm cache for."""
    try:
        # Get products ordered by some popularity metric
        # For now, just get a variety of products from different categories
        response = supabase_service.client.table('products').select('code, meat_type').limit(limit).execute()
        
        if response.data:
            # Get a mix of meat types
            products_by_type = {}
            for product in response.data:
                meat_type = product.get('meat_type', 'unknown')
                if meat_type not in products_by_type:
                    products_by_type[meat_type] = []
                products_by_type[meat_type].append(product['code'])
            
            # Select products evenly across meat types
            selected = []
            max_per_type = limit // len(products_by_type) if products_by_type else limit
            
            for meat_type, codes in products_by_type.items():
                selected.extend(codes[:max_per_type])
            
            return selected[:limit]
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting popular products: {e}")
        return []


async def warm_health_assessment_cache(product_codes: List[str] = None, limit: int = 20):
    """
    Warm the health assessment cache for popular products.
    
    Args:
        product_codes: Specific product codes to warm, or None to auto-select
        limit: Maximum number of products to warm
    """
    logger.info("Starting health assessment cache warming")
    
    # Initialize services
    supabase_service = get_supabase_service()
    mcp_service = HealthAssessmentMCPService()
    
    # Get product codes
    if not product_codes:
        product_codes = await get_popular_products(supabase_service, limit)
    
    if not product_codes:
        logger.warning("No products found to warm cache for")
        return
    
    logger.info(f"Warming cache for {len(product_codes)} products")
    
    # Process in batches to avoid overwhelming the API
    batch_size = 5
    success_count = 0
    
    for i in range(0, len(product_codes), batch_size):
        batch = product_codes[i:i+batch_size]
        
        # Process batch in parallel
        tasks = [
            warm_cache_for_product(code, supabase_service, mcp_service)
            for code in batch
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        for result in results:
            if result is True:
                success_count += 1
        
        # Small delay between batches
        if i + batch_size < len(product_codes):
            await asyncio.sleep(2)
    
    logger.info(f"Cache warming complete: {success_count}/{len(product_codes)} successful")


if __name__ == "__main__":
    # Example: warm cache for specific products or auto-select popular ones
    import sys
    
    if len(sys.argv) > 1:
        # Warm specific product codes from command line
        codes = sys.argv[1:]
        asyncio.run(warm_health_assessment_cache(product_codes=codes))
    else:
        # Auto-select popular products
        asyncio.run(warm_health_assessment_cache(limit=20))