"""Recommendation service for personalized product recommendations.

This service provides functions to generate personalized product recommendations
based on user preferences, using a sophisticated weighted scoring algorithm.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from functools import lru_cache
import time
import hashlib
import json

from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.db import models as db_models
from app.db.connection import is_using_local_db

logger = logging.getLogger(__name__)

# Cache to store normalized max values for faster repeat calculations
# Structure: {"timestamp": time_of_calculation, "max_protein": value, ...}
_max_values_cache = {}
# Cache TTL in seconds (30 minutes)
_MAX_VALUES_CACHE_TTL = 1800

# Recommendations cache to store recent results
# Structure: {"cache_key": {"recommendations": [...], "timestamp": time}}
_recommendations_cache = {}
# Cache TTL for recommendations (1 minute for fresher content)
_RECOMMENDATIONS_CACHE_TTL = 60

def get_personalized_recommendations(
    supabase_service, 
    user_preferences: Dict[str, Any],
    limit: int = 10,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Generate personalized product recommendations with pagination support.
    
    Args:
        supabase_service: Supabase service instance
        user_preferences: User preferences dictionary from profile
        limit: Number of products per page (default 10)
        skip: Number of products to skip for pagination (default 0)
        
    Returns:
        List of product dictionaries that best match the user preferences
    """
    try:
        start_time = time.time()
        
        # Check cache first
        cache_key = _generate_cache_key(user_preferences, limit, skip)
        cached_result = _get_cached_recommendations(cache_key)
        if cached_result:
            logger.info(f"Returning cached recommendations in {(time.time() - start_time):.3f}s")
            return cached_result
        
        logger.info(f"Generating personalized recommendations using optimized query")
        
        # Get optimized recommendations using SQL-based filtering and scoring
        recommendations = _get_optimized_recommendations(supabase_service, user_preferences, limit, skip)
        
        # Cache the results
        _cache_recommendations(cache_key, recommendations)
        
        # Log performance
        duration = time.time() - start_time
        logger.info(f"Generated {len(recommendations)} recommendations in {duration:.2f}s")
        
        return recommendations
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {str(e)}")
        # Fallback to original method if optimized method fails
        logger.info("Falling back to original recommendation method")
        return _get_personalized_recommendations_fallback(supabase_service, user_preferences, limit, skip)
        
def analyze_product_match(
    product: Dict[str, Any], 
    user_preferences: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Analyze why a product matches or doesn't match user preferences.
    
    Args:
        product: Product dictionary
        user_preferences: User preferences dictionary
        
    Returns:
        Tuple of (matches, concerns) lists with explanations
    """
    matches = []
    concerns = []
    
    # Create search text from product attributes
    search_text = (
        f"{product.get('name', '') or ''} {product.get('brand', '') or ''} "
        f"{product.get('description', '') or ''} {product.get('ingredients_text', '') or ''}"
    ).lower()
    
    # Check for preservatives
    if user_preferences.get('avoid_preservatives'):
        preservative_keywords = _get_preservative_keywords()
        found = [kw for kw in preservative_keywords if kw in search_text]
        if found:
            concerns.append(f"Contains preservatives: {', '.join(found)}")
        else:
            matches.append("No preservatives detected")
    
    # Check for antibiotic-free
    if user_preferences.get('prefer_antibiotic_free'):
        antibiotic_keywords = ['antibiotic-free', 'no antibiotics', 'raised without antibiotics']
        found = [kw for kw in antibiotic_keywords if kw in search_text]
        if found:
            matches.append(f"Antibiotic-free: {', '.join(found)}")
        else:
            concerns.append("No antibiotic-free claim found")
    
    # Check for organic or grass-fed/pasture-raised
    if user_preferences.get('prefer_organic_or_grass_fed'):
        organic_keywords = ['organic', 'grass-fed', 'pasture-raised', 'free-range']
        found = [kw for kw in organic_keywords if kw in search_text]
        if found:
            matches.append(f"Organic/Grass-fed: {', '.join(found)}")
        else:
            concerns.append("No organic or grass-fed claim found")
    
    # Check for added sugars
    sugar_keywords = ['sugar', 'syrup', 'dextrose', 'fructose', 'sucrose', 'maltodextrin']
    found = [kw for kw in sugar_keywords if kw in search_text]
    if found:
        concerns.append(f"Contains sugars: {', '.join(found)}")
    else:
        matches.append("No added sugars detected")
    
    # Check for flavor enhancers
    enhancer_keywords = ['monosodium glutamate', 'msg', 'hydrolyzed', 'autolyzed yeast extract']
    found = [kw for kw in enhancer_keywords if kw in search_text]
    if found:
        concerns.append(f"Contains flavor enhancers: {', '.join(found)}")
    else:
        matches.append("No flavor enhancers detected")
    
    # Check for sodium content (if available)
    nutrition_focus = user_preferences.get('nutrition_focus')
    if nutrition_focus == "salt" and product.get('salt') is not None:
        try:
            salt = float(product.get('salt'))
            if salt < 0.5:  # Threshold for "low sodium"
                matches.append(f"Low sodium: {salt}g per 100g")
            else:
                concerns.append(f"Higher sodium: {salt}g per 100g")
        except (ValueError, TypeError):
            pass
    
    # Check for preferred meat type
    meat_types = _get_preferred_meat_types(user_preferences)
    if meat_types and product.get('meat_type') in meat_types:
        matches.append(f"Preferred meat type: {product.get('meat_type')}")
    
    return matches, concerns

def _get_optimized_recommendations(
    supabase_service,
    user_preferences: Dict[str, Any],
    limit: int = 10,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Get personalized recommendations using optimized SQL queries.
    
    This method uses database-level filtering and scoring to dramatically
    improve performance by reducing data transfer and processing time.
    
    Args:
        supabase_service: Supabase service instance
        user_preferences: User preferences dictionary
        limit: Maximum number of recommendations to return
        skip: Number of products to skip for pagination
        
    Returns:
        List of recommended product dictionaries
    """
    try:
        # Build optimized query based on user preferences
        preferred_types = _get_preferred_meat_types(user_preferences)
        nutrition_focus = user_preferences.get("nutrition_focus", "protein")
        
        # Start with base query
        query = supabase_service.client.table('products').select('*')
        
        # Apply meat type filter at database level
        if preferred_types:
            meat_types_list = list(preferred_types)
            query = query.in_('meat_type', meat_types_list)
        
        # Apply nutritional filters based on preferences
        if nutrition_focus == "salt" and user_preferences.get("avoid_high_sodium"):
            # Filter for products with salt < 1.5g per 100g
            query = query.lt('salt', 1.5)
        elif nutrition_focus == "protein":
            # Prefer high protein products (>15g per 100g)
            query = query.gte('protein', 15)
        elif nutrition_focus == "fat":
            # Prefer lower fat products (<20g per 100g)
            query = query.lt('fat', 20)
        
        # Apply risk rating preference
        if user_preferences.get("prefer_low_risk", True):
            # Prefer Green and Yellow over Red
            query = query.in_('risk_rating', ['Green', 'Yellow'])
        
        # Order by multiple factors for better recommendations
        if nutrition_focus == "protein":
            query = query.order('protein', desc=True).order('salt', desc=False)
        elif nutrition_focus == "salt":
            query = query.order('salt', desc=False).order('protein', desc=True)
        elif nutrition_focus == "fat":
            query = query.order('fat', desc=False).order('protein', desc=True)
        else:
            # Default ordering: prefer green rating, then high protein, then low sodium
            query = query.order('risk_rating', desc=False).order('protein', desc=True).order('salt', desc=False)
        
        # Calculate fetch parameters for pagination with randomization
        # Fetch more items to enable randomization and diversity
        fetch_limit = min((limit + skip) * 2, 300)  # Allow for wider selection
        
        # Add offset for pagination
        query = query.range(skip, skip + fetch_limit - 1)
        
        # Execute the optimized query
        response = query.execute()
        products = response.data or []
        
        logger.debug(f"Optimized query returned {len(products)} products")
        
        # Apply final diversity and ranking if we have results
        if products:
            return _apply_final_selection_with_randomization(products, user_preferences, limit, skip)
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error in optimized recommendations query: {str(e)}")
        raise


def _apply_final_selection(
    products: List[Dict[str, Any]],
    user_preferences: Dict[str, Any], 
    limit: int
) -> List[Dict[str, Any]]:
    """
    Apply final selection logic to ensure diversity and quality.
    
    Args:
        products: Pre-filtered products from database
        user_preferences: User preferences
        limit: Target number of recommendations
        
    Returns:
        Final list of recommended products
    """
    preferred_types = _get_preferred_meat_types(user_preferences)
    
    if not preferred_types or len(preferred_types) == 1:
        # Single meat type or no preference - just return top products
        return products[:limit]
    
    # Apply diversity algorithm for multiple meat types
    type_products = {}
    for product in products:
        meat_type = product.get('meat_type')
        if meat_type in preferred_types:
            if meat_type not in type_products:
                type_products[meat_type] = []
            type_products[meat_type].append(product)
    
    # Distribute slots across meat types
    selected = []
    slots_per_type = max(1, limit // len(preferred_types))
    
    # First pass: ensure each type gets representation
    for meat_type in preferred_types:
        if meat_type in type_products:
            count = min(slots_per_type, len(type_products[meat_type]))
            selected.extend(type_products[meat_type][:count])
            type_products[meat_type] = type_products[meat_type][count:]
    
    # Second pass: fill remaining slots with best remaining products
    remaining_slots = limit - len(selected)
    if remaining_slots > 0:
        remaining_products = []
        for meat_type in preferred_types:
            if meat_type in type_products:
                remaining_products.extend(type_products[meat_type])
        
        selected.extend(remaining_products[:remaining_slots])
    
    return selected[:limit]


def _apply_final_selection_with_randomization(
    products: List[Dict[str, Any]],
    user_preferences: Dict[str, Any], 
    limit: int,
    skip: int
) -> List[Dict[str, Any]]:
    """
    Apply final selection logic with randomization to prevent static recommendations.
    
    Args:
        products: Pre-filtered products from database
        user_preferences: User preferences
        limit: Target number of recommendations
        skip: Number of products to skip for pagination
        
    Returns:
        Final list of recommended products with randomization
    """
    import random
    
    if not products:
        return []
    
    preferred_types = _get_preferred_meat_types(user_preferences)
    
    # If we have multiple meat types, apply diversity
    if preferred_types and len(preferred_types) > 1:
        return _apply_diversity_with_randomization(products, user_preferences, limit, preferred_types)
    
    # For single meat type or no preference, add some randomization
    # Take top products but add some variety
    if len(products) <= limit:
        return products
    
    # Use weighted random selection - give higher probability to earlier (better) products
    # but still allow some randomization to prevent static results
    weights = [1.0 / (i + 1) for i in range(len(products))]  # Decreasing weights
    
    try:
        # Select with weighted randomization
        selected_indices = set()
        selected = []
        
        # Ensure we get the top few products (maintain quality)
        guaranteed_top = min(limit // 2, len(products))
        selected.extend(products[:guaranteed_top])
        selected_indices.update(range(guaranteed_top))
        
        # Fill remaining slots with weighted random selection
        remaining_slots = limit - len(selected)
        if remaining_slots > 0:
            available_indices = [i for i in range(guaranteed_top, len(products)) if i not in selected_indices]
            if available_indices:
                available_weights = [weights[i] for i in available_indices]
                
                # Select remaining items with weighted randomization
                num_to_select = min(remaining_slots, len(available_indices))
                if num_to_select > 0:
                    selected_random_indices = random.choices(
                        available_indices, 
                        weights=available_weights, 
                        k=num_to_select
                    )
                    for idx in selected_random_indices:
                        if idx not in selected_indices:
                            selected.append(products[idx])
                            selected_indices.add(idx)
        
        return selected[:limit]
        
    except Exception as e:
        logger.warning(f"Error in randomization, falling back to simple selection: {e}")
        return products[:limit]


def _apply_diversity_with_randomization(
    products: List[Dict[str, Any]],
    user_preferences: Dict[str, Any],
    limit: int,
    preferred_types: Set[str]
) -> List[Dict[str, Any]]:
    """
    Apply diversity algorithm with randomization for multiple meat types.
    
    Args:
        products: Pre-filtered products from database
        user_preferences: User preferences
        limit: Target number of recommendations
        preferred_types: Set of preferred meat types
        
    Returns:
        Diversified and randomized list of products
    """
    import random
    
    # Group products by meat type
    type_products = {}
    for product in products:
        meat_type = product.get('meat_type')
        if meat_type in preferred_types:
            if meat_type not in type_products:
                type_products[meat_type] = []
            type_products[meat_type].append(product)
    
    # Calculate slots per type
    available_types = len(type_products)
    if available_types == 0:
        return products[:limit]
    
    slots_per_type = max(1, limit // available_types)
    
    selected = []
    
    # First pass: get guaranteed slots per type with some randomization
    for meat_type in preferred_types:
        if meat_type in type_products and type_products[meat_type]:
            type_list = type_products[meat_type]
            
            # Take top products but add some randomization
            guaranteed = min(slots_per_type // 2, len(type_list))
            selected.extend(type_list[:guaranteed])
            
            # Add some randomized selection from remaining
            remaining_slots = slots_per_type - guaranteed
            if remaining_slots > 0 and len(type_list) > guaranteed:
                remaining_products = type_list[guaranteed:]
                random_count = min(remaining_slots, len(remaining_products))
                if random_count > 0:
                    selected.extend(random.sample(remaining_products, random_count))
    
    # Fill any remaining slots with best remaining products
    if len(selected) < limit:
        used_products = set(p.get('code') for p in selected if p.get('code'))
        remaining_products = [p for p in products if p.get('code') not in used_products]
        
        additional_needed = limit - len(selected)
        if remaining_products and additional_needed > 0:
            selected.extend(remaining_products[:additional_needed])
    
    return selected[:limit]


def _generate_cache_key(user_preferences: Dict[str, Any], limit: int, skip: int) -> str:
    """
    Generate a cache key based on user preferences, limit, and skip.
    
    Args:
        user_preferences: User preferences dictionary
        limit: Number of recommendations requested
        skip: Number of recommendations to skip
        
    Returns:
        String cache key
    """
    # Create a stable representation of preferences for caching
    cache_data = {
        "nutrition_focus": user_preferences.get("nutrition_focus", "protein"),
        "meat_preferences": sorted(list(_get_preferred_meat_types(user_preferences))),
        "avoid_preservatives": user_preferences.get("avoid_preservatives", False),
        "prefer_antibiotic_free": user_preferences.get("prefer_antibiotic_free", False),
        "prefer_organic_or_grass_fed": user_preferences.get("prefer_organic_or_grass_fed", False),
        "avoid_high_sodium": user_preferences.get("avoid_high_sodium", False),
        "prefer_low_risk": user_preferences.get("prefer_low_risk", True),
        "limit": limit,
        "skip": skip
    }
    
    # Create hash of the cache data
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()


def _get_cached_recommendations(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached recommendations if available and not expired.
    
    Args:
        cache_key: Cache key to look up
        
    Returns:
        Cached recommendations or None if not found/expired
    """
    global _recommendations_cache
    
    if cache_key not in _recommendations_cache:
        return None
    
    cached_data = _recommendations_cache[cache_key]
    cache_time = cached_data.get("timestamp", 0)
    
    # Check if cache is expired
    if time.time() - cache_time > _RECOMMENDATIONS_CACHE_TTL:
        # Remove expired cache entry
        del _recommendations_cache[cache_key]
        return None
    
    return cached_data.get("recommendations", [])


def _cache_recommendations(cache_key: str, recommendations: List[Dict[str, Any]]) -> None:
    """
    Cache recommendations with timestamp.
    
    Args:
        cache_key: Cache key to store under
        recommendations: Recommendations to cache
    """
    global _recommendations_cache
    
    # Clean up expired entries periodically (every 10 cache operations)
    if len(_recommendations_cache) % 10 == 0:
        _cleanup_expired_cache()
    
    _recommendations_cache[cache_key] = {
        "recommendations": recommendations,
        "timestamp": time.time()
    }
    
    logger.debug(f"Cached {len(recommendations)} recommendations with key {cache_key}")


def _cleanup_expired_cache() -> None:
    """
    Remove expired entries from the recommendations cache.
    """
    global _recommendations_cache
    
    current_time = time.time()
    expired_keys = [
        key for key, data in _recommendations_cache.items()
        if current_time - data.get("timestamp", 0) > _RECOMMENDATIONS_CACHE_TTL
    ]
    
    for key in expired_keys:
        del _recommendations_cache[key]
    
    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


def _get_personalized_recommendations_fallback(
    supabase_service, 
    user_preferences: Dict[str, Any],
    limit: int = 10,
    skip: int = 0
) -> List[Dict[str, Any]]:
    """
    Fallback method using the original algorithm but with optimizations.
    
    Args:
        supabase_service: Supabase service instance
        user_preferences: User preferences dictionary from profile
        limit: Maximum number of products to return
        skip: Number of products to skip for pagination
        
    Returns:
        List of product dictionaries that best match the user preferences
    """
    try:
        start_time = time.time()
        logger.info(f"Using fallback recommendation method")
        
        # Get products with reduced limit for fallback
        products = _get_products_from_supabase_limited(supabase_service, limit * 10)
        if not products:
            logger.warning("No products found in database")
            return []
            
        # Filter by meat type preferences if specified
        filtered_products = _filter_by_meat_types(products, user_preferences)
        logger.debug(f"Filtered to {len(filtered_products)} products by meat type")
        
        # Calculate maximum values for normalization
        max_values = _get_max_nutritional_values_from_products(filtered_products)
        
        # Score products based on user preferences
        scored_products = []
        for product in filtered_products:
            score = _calculate_product_score(product, user_preferences, max_values)
            scored_products.append((product, score))
            
        # Sort by score (highest first)
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Apply diversity factor to ensure representation of different meat types
        preferred_types = _get_preferred_meat_types(user_preferences)
        diverse_products = _apply_diversity_factor(scored_products, limit + skip, preferred_types)
        
        # Apply pagination to the results
        paginated_products = diverse_products[skip:skip + limit]
        
        # Log performance
        duration = time.time() - start_time
        logger.info(f"Generated {len(paginated_products)} recommendations (fallback) in {duration:.2f}s")
        
        return paginated_products
    except Exception as e:
        logger.error(f"Error in fallback recommendation method: {str(e)}")
        return []


def _get_products_from_supabase_limited(supabase_service, limit: int = 300) -> List[Dict[str, Any]]:
    """
    Get products from Supabase with limited fetch size for better performance.
    
    Args:
        supabase_service: Supabase service instance
        limit: Maximum number of products to fetch
        
    Returns:
        List of product dictionaries
    """
    try:
        # Reduced limit for better performance
        products = supabase_service.get_products(limit=limit, offset=0)
        logger.debug(f"Retrieved {len(products)} products from Supabase (limited)")
        return products
    except Exception as e:
        logger.error(f"Failed to get products from Supabase: {str(e)}")
        return []


def _get_products_from_supabase(supabase_service) -> List[Dict[str, Any]]:
    """
    Get products from Supabase with error handling and fallback strategies.
    
    Args:
        supabase_service: Supabase service instance
        
    Returns:
        List of product dictionaries
    """
    # Redirect to limited version for performance
    return _get_products_from_supabase_limited(supabase_service, 300)

def _filter_by_meat_types(
    products: List[Dict[str, Any]], 
    preferences: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Filter products by preferred meat types.
    
    Args:
        products: List of product dictionaries
        preferences: User preferences dictionary
        
    Returns:
        Filtered list of products
    """
    preferred_types = _get_preferred_meat_types(preferences)
    if not preferred_types:
        return products
        
    return [p for p in products if p.get('meat_type') in preferred_types]

def _get_preferred_meat_types(preferences: Dict[str, Any]) -> Set[str]:
    """
    Extract preferred meat types from user preferences.
    
    Args:
        preferences: User preferences dictionary
        
    Returns:
        Set of preferred meat types
    """
    # Try new preferences model first
    meat_preferences = preferences.get("meat_preferences", [])
    
    # If empty, try legacy preferences
    if not meat_preferences and "preferred_meat_types" in preferences:
        meat_preferences = preferences["preferred_meat_types"]
        
    # Ensure we have a set (for efficient lookups)
    return set(meat_preferences) if meat_preferences else set()

@lru_cache(maxsize=32)
def _get_preservative_keywords() -> List[str]:
    """
    Get list of common preservative keywords.
    
    Returns:
        List of preservative keywords
    """
    return [
        'sorbate', 'benzoate', 'nitrite', 'nitrate', 'sulfite', 
        'bha', 'bht', 'sodium erythorbate', 'sodium nitrite'
    ]

def _get_max_nutritional_values_from_products(
    products: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Get maximum nutritional values for normalization from product dictionaries.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        Dictionary of maximum values
    """
    global _max_values_cache
    
    # Check if we have valid cached values
    now = time.time()
    if (_max_values_cache and 
        _max_values_cache.get("timestamp", 0) > now - _MAX_VALUES_CACHE_TTL):
        logger.debug("Using cached max nutritional values")
        return _max_values_cache
        
    try:
        # Calculate from the provided products
        protein_values = [p.get('protein', 0) or 0 for p in products if p.get('protein') is not None]
        fat_values = [p.get('fat', 0) or 0 for p in products if p.get('fat') is not None]
        salt_values = [p.get('salt', 0) or 0 for p in products if p.get('salt') is not None]
        
        max_values = {
            "max_protein": max(protein_values) if protein_values else 100,
            "max_fat": max(fat_values) if fat_values else 100,
            "max_salt": max(salt_values) if salt_values else 5,
            "timestamp": now
        }
        
        # Ensure we have reasonable values (avoid division by zero)
        max_values = {
            k: v if v > 0 else (100 if k != "max_salt" else 5) 
            for k, v in max_values.items() if k != "timestamp"
        }
        max_values["timestamp"] = now
        
        # Cache the values
        _max_values_cache = max_values
        logger.debug(f"Updated max nutritional values from products: {max_values}")
        
        return max_values
    except Exception as e:
        logger.error(f"Failed to calculate max values: {str(e)}")
        
        # Last resort: Use hardcoded defaults
        return {
            "max_protein": 100,
            "max_fat": 100,
            "max_salt": 5,
            "timestamp": now
        }

def _calculate_product_score(
    product: Dict[str, Any],
    preferences: Dict[str, Any],
    max_values: Dict[str, float]
) -> float:
    """
    Calculate a score for a product based on user preferences.
    
    Args:
        product: Product dictionary
        preferences: User preferences dictionary
        max_values: Maximum nutritional values for normalization
        
    Returns:
        Numerical score representing match quality
    """
    search_text = (
        f"{product.get('name', '') or ''} {product.get('brand', '') or ''} "
        f"{product.get('description', '') or ''} {product.get('ingredients_text', '') or ''}"
    ).lower()
    
    score = 0
    
    # Normalize nutritional values
    protein = 0
    fat = 0
    sodium = 0
    
    try:
        if product.get('protein') is not None:
            protein = float(product.get('protein')) / max_values["max_protein"]
        if product.get('fat') is not None:
            fat = float(product.get('fat')) / max_values["max_fat"]
        if product.get('salt') is not None:
            sodium = float(product.get('salt')) / max_values["max_salt"]
    except (ValueError, TypeError):
        logger.debug(f"Error normalizing nutritional values for product {product.get('code', 'unknown')}")
    
    # Default weights - balanced approach
    w_protein = 0.15
    w_fat = 0.15 
    w_sodium = 0.15
    w_antibiotic = 0.15
    w_organic_grass_fed = 0.2
    w_preservatives = 0.2
    
    # Adjust weights based on user preferences
    nutrition_focus = preferences.get("nutrition_focus")
    if nutrition_focus == "protein":
        w_protein = 0.4
        w_fat = 0.1
        w_sodium = 0.1
    elif nutrition_focus == "fat":
        w_protein = 0.1
        w_fat = 0.4
        w_sodium = 0.1
    elif nutrition_focus == "salt":
        w_protein = 0.1
        w_fat = 0.1
        w_sodium = 0.4
    
    # Adjust weights for other preferences
    if preferences.get("prefer_antibiotic_free"):
        w_antibiotic = 0.25
        
    if preferences.get("prefer_organic_or_grass_fed"):
        w_organic_grass_fed = 0.25
        
    if preferences.get("avoid_preservatives"):
        w_preservatives = 0.25
    
    # Check for preservatives (negative factor)
    preservative_free = 1.0
    if preferences.get('avoid_preservatives'):
        preservative_keywords = _get_preservative_keywords()
        if any(kw in search_text for kw in preservative_keywords):
            preservative_free = 0.0
    
    # Check for antibiotic-free (positive factor)
    antibiotic_free = 0.0
    if preferences.get('prefer_antibiotic_free'):
        antibiotic_keywords = ['antibiotic-free', 'no antibiotics', 'raised without antibiotics']
        if any(kw in search_text for kw in antibiotic_keywords):
            antibiotic_free = 1.0
    
    # Check for organic or grass-fed/pasture-raised (positive factor)
    organic_grass_fed = 0.0
    if preferences.get('prefer_organic_or_grass_fed'):
        organic_keywords = ['organic', 'grass-fed', 'pasture-raised', 'free-range']
        if any(kw in search_text for kw in organic_keywords):
            organic_grass_fed = 1.0
    
    # Check for meat type match
    meat_type_match = 0.0
    preferred_types = _get_preferred_meat_types(preferences)
    if preferred_types and product.get('meat_type') in preferred_types:
        meat_type_match = 1.0
    
    # Calculate final score using normalized values and weights
    score = (
        (w_protein * protein) +
        (w_fat * (1 - fat)) +  # Lower fat is better
        (w_sodium * (1 - sodium)) +  # Lower sodium is better
        (w_antibiotic * antibiotic_free) +
        (w_organic_grass_fed * organic_grass_fed) +
        (w_preservatives * preservative_free) +
        (0.2 * meat_type_match)  # Small boost for preferred meat type
    )
    
    return score

def _apply_diversity_factor(
    scored_products: List[Tuple[Dict[str, Any], float]], 
    limit: int, 
    preferred_types: Set[str]
) -> List[Dict[str, Any]]:
    """
    Apply a diversity factor to ensure representation of different meat types.
    
    Args:
        scored_products: List of (product dict, score) tuples
        limit: Maximum number of products to return
        preferred_types: Set of preferred meat types
        
    Returns:
        List of product dictionaries with diversity factor applied
    """
    if not scored_products:
        return []
    
    # If no preferred types, use all available types from scored products
    if not preferred_types:
        preferred_types = set(p.get('meat_type') for p, _ in scored_products if p.get('meat_type'))
    
    # If still no meat types, just return the top scoring products
    if not preferred_types:
        return [product for product, _ in scored_products[:limit]]
    
    # Calculate target distribution based on available types
    num_types = len(preferred_types)
    slots_per_type = max(1, limit // num_types)  # Ensure at least 1 slot per type
    
    selected_products = []
    type_counts = {meat_type: 0 for meat_type in preferred_types}
    type_products = {meat_type: [] for meat_type in preferred_types}
    
    # Group products by meat type
    for product, score in scored_products:
        meat_type = product.get('meat_type')
        if meat_type in type_products:
            type_products[meat_type].append((product, score))
    
    # Distribute slots fairly across meat types
    remaining_slots = limit
    while remaining_slots > 0 and any(type_products[mt] for mt in preferred_types):
        for meat_type in preferred_types:
            if remaining_slots <= 0:
                break
            if type_counts[meat_type] < slots_per_type and type_products[meat_type]:
                product, _ = type_products[meat_type].pop(0)
                selected_products.append(product)
                type_counts[meat_type] += 1
                remaining_slots -= 1
    
    # Fill remaining slots with best remaining products
    if remaining_slots > 0:
        remaining_products = []
        for meat_type in preferred_types:
            remaining_products.extend(type_products[meat_type])
        remaining_products.sort(key=lambda x: x[1], reverse=True)  # Sort by score
        for product, _ in remaining_products[:remaining_slots]:
            selected_products.append(product)
    
    return selected_products[:limit] 