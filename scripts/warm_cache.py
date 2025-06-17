#!/usr/bin/env python3
"""
Cache warming script to preload common ingredient assessments.
This improves response time for frequently assessed products.
"""

import sys
import os
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.cache import cache
from app.services.async_citation_search import search_citations_for_health_assessment
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common high-risk ingredients to pre-cache
COMMON_HIGH_RISK_INGREDIENTS = [
    "Sodium Nitrite",
    "Sodium Nitrate", 
    "BHA",
    "BHT",
    "MSG",
    "Monosodium Glutamate",
    "Sodium Benzoate",
    "Potassium Sorbate",
    "Sodium Phosphate",
    "Caramel Color",
    "TBHQ",
    "Natural Flavors",
    "Artificial Colors",
    "Red 40",
    "Yellow 6",
    "Carrageenan"
]

async def warm_citation_cache():
    """Pre-load citations for common ingredients."""
    logger.info("🔥 Warming citation cache for common ingredients...")
    
    try:
        # Warm cache for common ingredients
        citations_dict = await search_citations_for_health_assessment(COMMON_HIGH_RISK_INGREDIENTS)
        
        cached_count = 0
        for ingredient, citations in citations_dict.items():
            if citations:
                cached_count += 1
                logger.info(f"✅ Cached {len(citations)} citations for {ingredient}")
            else:
                logger.warning(f"⚠️  No citations found for {ingredient}")
        
        logger.info(f"🎉 Cache warming complete! Cached citations for {cached_count}/{len(COMMON_HIGH_RISK_INGREDIENTS)} ingredients")
        
    except Exception as e:
        logger.error(f"❌ Error warming citation cache: {e}")

def warm_assessment_patterns():
    """Pre-cache common assessment patterns."""
    logger.info("🔥 Warming assessment pattern cache...")
    
    common_patterns = [
        "processed_meat_high_sodium",
        "organic_low_additive", 
        "smoked_meat_moderate_risk",
        "preservative_free_low_risk"
    ]
    
    # Pre-populate common pattern hashes
    for pattern in common_patterns:
        cache_key = f"assessment_pattern:{pattern}"
        # Set a placeholder that indicates the pattern is known
        cache.set(cache_key, {"pattern": pattern, "cached_at": "startup"}, ttl=86400)
        logger.info(f"✅ Cached assessment pattern: {pattern}")

async def main():
    """Main cache warming function."""
    logger.info("🚀 Starting cache warming process...")
    
    # Warm citation cache
    await warm_citation_cache()
    
    # Warm assessment patterns
    warm_assessment_patterns()
    
    # Pre-warm ingredient hash cache for memory optimization
    logger.info("🔥 Pre-warming ingredient hash cache...")
    common_ingredient_texts = [
        "pork, salt, sodium nitrite, spices",
        "beef, water, salt, natural flavors", 
        "chicken, sodium phosphate, seasoning",
        "turkey, celery powder, sea salt"
    ]
    
    from app.services.health_assessment_service import _hash_ingredients
    for ingredients_text in common_ingredient_texts:
        hash_key = _hash_ingredients(ingredients_text)
        cache_key = f"ingredient_hash:{hash_key}"
        cache.set(cache_key, ingredients_text, ttl=86400)
        logger.info(f"✅ Cached ingredient hash for: {ingredients_text[:50]}...")
    
    logger.info("🎉 Cache warming complete! API responses should be significantly faster.")

if __name__ == "__main__":
    asyncio.run(main())