"""Optimized search operations with batching and parallel processing."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select
from sqlalchemy.sql import text

from app.db import models as db_models
from app.services.search_service import SearchIntent, calculate_match_score
from app.core.cache import cache

logger = logging.getLogger(__name__)

# Thread pool for parallel score calculations
executor = ThreadPoolExecutor(max_workers=4)


class SearchOptimizer:
    """Optimized search operations using batching and caching."""
    
    def __init__(self, db: Session):
        self.db = db
        
    def batch_search_products(
        self, 
        intents: List[SearchIntent],
        limit_per_query: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch multiple search queries for efficiency.
        
        Args:
            intents: List of search intents to process
            limit_per_query: Max results per query
            
        Returns:
            Dict mapping query hash to results
        """
        results = {}
        
        # Group similar intents to reduce database queries
        grouped_intents = self._group_similar_intents(intents)
        
        for group_key, group_intents in grouped_intents.items():
            # Check cache for the group
            cache_key = cache.generate_key(group_key, prefix="search_batch")
            cached_results = cache.get(cache_key)
            
            if cached_results:
                # Distribute cached results to individual queries
                for intent in group_intents:
                    intent_key = self._get_intent_key(intent)
                    results[intent_key] = cached_results[:limit_per_query]
                continue
            
            # Execute optimized query for the group
            products = self._execute_optimized_query(group_intents[0], limit_per_query * 3)
            
            # Calculate scores in parallel
            scored_products = self._parallel_score_calculation(products, group_intents[0])
            
            # Cache the results
            cache.set(cache_key, scored_products, ttl=3600)
            
            # Distribute results to individual queries
            for intent in group_intents:
                intent_key = self._get_intent_key(intent)
                results[intent_key] = scored_products[:limit_per_query]
        
        return results
    
    def _group_similar_intents(self, intents: List[SearchIntent]) -> Dict[str, List[SearchIntent]]:
        """Group similar search intents to reduce database queries."""
        groups = {}
        
        for intent in intents:
            # Create a group key based on main search criteria
            group_key = f"{'-'.join(sorted(intent.meat_types))}:{intent.risk_preference or 'any'}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(intent)
        
        return groups
    
    def _get_intent_key(self, intent: SearchIntent) -> str:
        """Generate a unique key for an intent."""
        return cache.generate_key(intent.to_dict(), prefix="intent")
    
    def _execute_optimized_query(self, intent: SearchIntent, limit: int) -> List[db_models.Product]:
        """Execute an optimized database query using proper indexes."""
        query = self.db.query(db_models.Product)
        
        # Use indexed columns first
        if intent.meat_types:
            query = query.filter(db_models.Product.meat_type.in_(intent.meat_types))
        
        if intent.risk_preference:
            query = query.filter(db_models.Product.risk_rating == intent.risk_preference)
        
        # Nutritional constraints using indexed columns
        if intent.nutritional_constraints:
            if "min_protein" in intent.nutritional_constraints:
                query = query.filter(
                    db_models.Product.protein >= intent.nutritional_constraints["min_protein"]
                )
            if "max_salt" in intent.nutritional_constraints:
                query = query.filter(
                    db_models.Product.salt <= intent.nutritional_constraints["max_salt"]
                )
            if "max_fat" in intent.nutritional_constraints:
                query = query.filter(
                    db_models.Product.fat <= intent.nutritional_constraints["max_fat"]
                )
        
        # Use full-text search for ingredient exclusions if available
        if intent.exclude_ingredients:
            for ingredient in intent.exclude_ingredients:
                query = query.filter(
                    ~func.lower(db_models.Product.ingredients_text).contains(ingredient.lower())
                )
        
        # Limit and execute
        return query.limit(limit).all()
    
    def _parallel_score_calculation(
        self, 
        products: List[db_models.Product], 
        intent: SearchIntent
    ) -> List[Dict[str, Any]]:
        """Calculate match scores in parallel for better performance."""
        # Use thread pool for CPU-bound score calculations
        futures = []
        
        for product in products:
            future = executor.submit(self._score_and_format_product, product, intent)
            futures.append(future)
        
        # Collect results
        scored_products = []
        for future in futures:
            result = future.result()
            if result:
                scored_products.append(result)
        
        # Sort by score
        scored_products.sort(key=lambda x: x['match_score'], reverse=True)
        
        return scored_products
    
    def _score_and_format_product(
        self, 
        product: db_models.Product, 
        intent: SearchIntent
    ) -> Optional[Dict[str, Any]]:
        """Score and format a single product."""
        try:
            score, matched_terms = calculate_match_score(product, intent)
            
            if score > 0:
                return {
                    "code": product.code,
                    "name": product.name,
                    "brand": product.brand,
                    "description": product.description,
                    "meat_type": product.meat_type,
                    "risk_rating": product.risk_rating,
                    "image_url": product.image_url,
                    "match_score": score,
                    "matched_terms": matched_terms,
                    "nutrition": {
                        "calories": product.calories,
                        "protein": product.protein,
                        "fat": product.fat,
                        "carbohydrates": product.carbohydrates,
                        "salt": product.salt
                    } if any([product.calories, product.protein, product.fat]) else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error scoring product {product.code}: {e}")
            return None


def get_search_optimizer(db: Session) -> SearchOptimizer:
    """Factory function to create a search optimizer instance."""
    return SearchOptimizer(db) 