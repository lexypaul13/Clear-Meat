"""Aggressive caching service for Google Search grounded health assessments."""

import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.cache import cache

logger = logging.getLogger(__name__)


class GroundedHealthCache:
    """
    Aggressive caching strategy for Google Search grounded health information.
    Caches at ingredient level to maximize reuse across products.
    """
    
    # Cache TTLs in seconds
    INGREDIENT_TTL = 30 * 24 * 60 * 60  # 30 days for ingredient health info
    PRODUCT_TTL = 7 * 24 * 60 * 60     # 7 days for complete assessments
    GROUNDED_TTL = 14 * 24 * 60 * 60   # 14 days for grounded search results
    
    @staticmethod
    def get_ingredient_cache_key(ingredient: str, risk_level: str = "general") -> str:
        """Generate cache key for ingredient health information."""
        # Normalize ingredient name
        normalized = ingredient.lower().strip()
        return f"grounded:ingredient:{risk_level}:{hashlib.md5(normalized.encode()).hexdigest()}"
    
    @staticmethod
    def get_product_cache_key(product_code: str) -> str:
        """Generate cache key for complete product assessment."""
        return f"grounded:product:{product_code}"
    
    @staticmethod
    def cache_ingredient_analysis(
        ingredient: str, 
        risk_level: str,
        analysis: Dict[str, Any],
        citations: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Cache ingredient analysis with grounded citations.
        
        Args:
            ingredient: Ingredient name
            risk_level: Risk level (high, moderate, low)
            analysis: Analysis data including health effects
            citations: Optional grounded citations from Google Search
            
        Returns:
            Success status
        """
        cache_key = GroundedHealthCache.get_ingredient_cache_key(ingredient, risk_level)
        
        cache_data = {
            "ingredient": ingredient,
            "risk_level": risk_level,
            "analysis": analysis,
            "citations": citations or [],
            "cached_at": datetime.utcnow().isoformat(),
            "source": "google_search_grounded"
        }
        
        success = cache.set(cache_key, cache_data, GroundedHealthCache.INGREDIENT_TTL)
        if success:
            logger.info(f"[Grounded Cache] Cached analysis for {ingredient} ({risk_level}) - 30 day TTL")
        return success
    
    @staticmethod
    def get_ingredient_analysis(ingredient: str, risk_level: str = "general") -> Optional[Dict[str, Any]]:
        """
        Get cached ingredient analysis.
        
        Returns:
            Cached analysis data or None
        """
        cache_key = GroundedHealthCache.get_ingredient_cache_key(ingredient, risk_level)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"[Grounded Cache] HIT for {ingredient} ({risk_level})")
            return cached_data
        
        logger.debug(f"[Grounded Cache] MISS for {ingredient} ({risk_level})")
        return None
    
    @staticmethod
    def cache_grounded_assessment(
        product_code: str,
        assessment: Dict[str, Any],
        ingredients_analyzed: List[str]
    ) -> bool:
        """
        Cache complete grounded assessment.
        
        Args:
            product_code: Product barcode
            assessment: Complete assessment data
            ingredients_analyzed: List of ingredients that were analyzed
            
        Returns:
            Success status
        """
        cache_key = GroundedHealthCache.get_product_cache_key(product_code)
        
        cache_data = {
            "assessment": assessment,
            "ingredients_analyzed": ingredients_analyzed,
            "cached_at": datetime.utcnow().isoformat(),
            "source": "google_search_grounded"
        }
        
        success = cache.set(cache_key, cache_data, GroundedHealthCache.PRODUCT_TTL)
        if success:
            logger.info(f"[Grounded Cache] Cached complete assessment for {product_code} - 7 day TTL")
        return success
    
    @staticmethod
    def get_grounded_assessment(product_code: str) -> Optional[Dict[str, Any]]:
        """Get cached grounded assessment."""
        cache_key = GroundedHealthCache.get_product_cache_key(product_code)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"[Grounded Cache] HIT for product {product_code}")
            return cached_data
        
        logger.debug(f"[Grounded Cache] MISS for product {product_code}")
        return None
    
    @staticmethod
    def build_assessment_from_cached_ingredients(
        ingredients: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to build assessment from cached ingredient analyses.
        
        Args:
            ingredients: Dict of ingredient -> risk_level
            
        Returns:
            Partial assessment if enough cached data available
        """
        cached_analyses = {}
        total_ingredients = len(ingredients)
        cached_count = 0
        
        for ingredient, risk_level in ingredients.items():
            cached_analysis = GroundedHealthCache.get_ingredient_analysis(ingredient, risk_level)
            if cached_analysis:
                cached_analyses[ingredient] = cached_analysis
                cached_count += 1
        
        # If we have at least 70% of ingredients cached, we can build an assessment
        if cached_count >= total_ingredients * 0.7:
            logger.info(f"[Grounded Cache] Building assessment from {cached_count}/{total_ingredients} cached ingredients")
            return {
                "from_cache": True,
                "cached_ingredients": cached_analyses,
                "cache_coverage": cached_count / total_ingredients
            }
        
        return None
    
    @staticmethod
    def clear_ingredient_cache(ingredient: str) -> bool:
        """Clear all cached data for a specific ingredient."""
        pattern = f"grounded:ingredient:*:{hashlib.md5(ingredient.lower().strip().encode()).hexdigest()}"
        cleared = cache.clear_pattern(pattern)
        logger.info(f"[Grounded Cache] Cleared {cleared} cache entries for {ingredient}")
        return cleared > 0
    
    @staticmethod
    def get_cache_stats() -> Dict[str, int]:
        """Get cache statistics."""
        stats = {
            "ingredient_entries": len(cache.redis_client.keys("grounded:ingredient:*")) if cache.redis_client else 0,
            "product_entries": len(cache.redis_client.keys("grounded:product:*")) if cache.redis_client else 0
        }
        return stats


# Global instance
grounded_cache = GroundedHealthCache()