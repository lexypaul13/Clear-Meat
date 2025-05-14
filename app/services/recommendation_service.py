"""Recommendation service for personalized product recommendations.

This service provides functions to generate personalized product recommendations
based on user preferences, using a sophisticated weighted scoring algorithm.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from functools import lru_cache
import time

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

def get_personalized_recommendations(
    db: Session, 
    user_preferences: Dict[str, Any],
    limit: int = 30
) -> List[db_models.Product]:
    """
    Generate personalized product recommendations based on user preferences.
    
    Args:
        db: Database session
        user_preferences: User preferences dictionary from profile
        limit: Maximum number of products to return
        
    Returns:
        List of product objects that best match the user preferences
    """
    try:
        start_time = time.time()
        logger.info(f"Generating personalized recommendations (using local DB: {is_using_local_db()})")
        
        # Get available products from database
        products = _get_products_from_db(db)
        if not products:
            logger.warning("No products found in database")
            return []
            
        # Filter by meat type preferences if specified
        filtered_products = _filter_by_meat_types(products, user_preferences)
        logger.debug(f"Filtered to {len(filtered_products)} products by meat type")
        
        # Calculate maximum values for normalization
        max_values = _get_max_nutritional_values(db, filtered_products)
        
        # Score products based on user preferences
        scored_products = []
        for product in filtered_products:
            score = _calculate_product_score(product, user_preferences, max_values)
            scored_products.append((product, score))
            
        # Sort by score (highest first)
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Apply diversity factor to ensure representation of different meat types
        preferred_types = _get_preferred_meat_types(user_preferences)
        diverse_products = _apply_diversity_factor(scored_products, limit, preferred_types)
        
        # Log performance
        duration = time.time() - start_time
        logger.info(f"Generated {len(diverse_products)} recommendations in {duration:.2f}s")
        
        return diverse_products
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {str(e)}")
        return []
        
def analyze_product_match(
    product: db_models.Product, 
    user_preferences: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Analyze why a product matches or doesn't match user preferences.
    
    Args:
        product: Product object
        user_preferences: User preferences dictionary
        
    Returns:
        Tuple of (matches, concerns) lists with explanations
    """
    matches = []
    concerns = []
    
    # Create search text from product attributes
    search_text = (
        f"{product.name or ''} {product.brand or ''} "
        f"{product.description or ''} {product.ingredients_text or ''}"
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
    if nutrition_focus == "salt" and hasattr(product, 'salt') and product.salt is not None:
        try:
            salt = float(product.salt)
            if salt < 0.5:  # Threshold for "low sodium"
                matches.append(f"Low sodium: {salt}g per 100g")
            else:
                concerns.append(f"Higher sodium: {salt}g per 100g")
        except (ValueError, TypeError):
            pass
    
    # Check for preferred meat type
    meat_types = _get_preferred_meat_types(user_preferences)
    if meat_types and product.meat_type in meat_types:
        matches.append(f"Preferred meat type: {product.meat_type}")
    
    return matches, concerns

def _get_products_from_db(db: Session) -> List[db_models.Product]:
    """
    Get products from database with error handling and fallback strategies.
    
    Args:
        db: Database session
        
    Returns:
        List of product objects
    """
    try:
        # Primary query method
        products = db.query(db_models.Product).all()
        logger.debug(f"Retrieved {len(products)} products from database")
        return products
    except Exception as e:
        logger.warning(f"Primary product query failed: {str(e)}")
        
        try:
            # Fallback: Try simpler query
            products = db.query(db_models.Product).limit(1000).all()
            logger.debug(f"Retrieved {len(products)} products using fallback query")
            return products
        except Exception as e2:
            logger.error(f"All product query methods failed: {str(e2)}")
            return []

def _filter_by_meat_types(
    products: List[db_models.Product], 
    preferences: Dict[str, Any]
) -> List[db_models.Product]:
    """
    Filter products by preferred meat types.
    
    Args:
        products: List of product objects
        preferences: User preferences dictionary
        
    Returns:
        Filtered list of products
    """
    preferred_types = _get_preferred_meat_types(preferences)
    if not preferred_types:
        return products
        
    return [p for p in products if p.meat_type in preferred_types]

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

def _get_max_nutritional_values(
    db: Session, 
    products: List[db_models.Product]
) -> Dict[str, float]:
    """
    Get maximum nutritional values for normalization, with caching.
    
    Args:
        db: Database session
        products: List of product objects (fallback if DB query fails)
        
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
        # Try to get max values from the database directly
        if is_using_local_db():
            # For local DB, we use SQLAlchemy
            max_protein = db.query(db_models.Product.protein).order_by(
                db_models.Product.protein.desc()).first()
            max_fat = db.query(db_models.Product.fat).order_by(
                db_models.Product.fat.desc()).first()
            max_salt = db.query(db_models.Product.salt).order_by(
                db_models.Product.salt.desc()).first()
            
            max_values = {
                "max_protein": float(max_protein[0] or 100) if max_protein else 100,
                "max_fat": float(max_fat[0] or 100) if max_fat else 100,
                "max_salt": float(max_salt[0] or 5) if max_salt else 5,
                "timestamp": now
            }
        else:
            # For remote DB, we use a single query
            result = db.execute(text("""
                SELECT 
                    MAX(protein) as max_protein,
                    MAX(fat) as max_fat,
                    MAX(salt) as max_salt
                FROM products
                WHERE protein IS NOT NULL AND fat IS NOT NULL AND salt IS NOT NULL
            """))
            row = result.fetchone()
            
            if row:
                max_values = {
                    "max_protein": float(row.max_protein or 100),
                    "max_fat": float(row.max_fat or 100),
                    "max_salt": float(row.max_salt or 5),
                    "timestamp": now
                }
            else:
                raise ValueError("No valid nutritional values found")
                
        # Cache the values
        _max_values_cache = max_values
        logger.debug(f"Updated max nutritional values cache: {max_values}")
        
        return max_values
            
    except Exception as e:
        logger.warning(f"Failed to get max values from DB: {str(e)}")
        
        # Fallback: Calculate from the provided products
        try:
            max_values = {
                "max_protein": max((getattr(p, 'protein', 0) or 0) for p in products if hasattr(p, 'protein')),
                "max_fat": max((getattr(p, 'fat', 0) or 0) for p in products if hasattr(p, 'fat')),
                "max_salt": max((getattr(p, 'salt', 0) or 0) for p in products if hasattr(p, 'salt')),
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
        except Exception as e2:
            logger.error(f"All max value methods failed: {str(e2)}")
            
            # Last resort: Use hardcoded defaults
            return {
                "max_protein": 100,
                "max_fat": 100,
                "max_salt": 5,
                "timestamp": now
            }

def _calculate_product_score(
    product: db_models.Product,
    preferences: Dict[str, Any],
    max_values: Dict[str, float]
) -> float:
    """
    Calculate a score for a product based on user preferences.
    
    Args:
        product: Product object
        preferences: User preferences dictionary
        max_values: Maximum nutritional values for normalization
        
    Returns:
        Numerical score representing match quality
    """
    search_text = (
        f"{product.name or ''} {product.brand or ''} "
        f"{product.description or ''} {product.ingredients_text or ''}"
    ).lower()
    
    score = 0
    
    # Normalize nutritional values
    protein = 0
    fat = 0
    sodium = 0
    
    try:
        if hasattr(product, 'protein') and product.protein is not None:
            protein = float(product.protein) / max_values["max_protein"]
        if hasattr(product, 'fat') and product.fat is not None:
            fat = float(product.fat) / max_values["max_fat"]
        if hasattr(product, 'salt') and product.salt is not None:
            sodium = float(product.salt) / max_values["max_salt"]
    except (ValueError, TypeError):
        logger.debug(f"Error normalizing nutritional values for product {product.code}")
    
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
    if preferred_types and product.meat_type in preferred_types:
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
    scored_products: List[Tuple[db_models.Product, float]], 
    limit: int, 
    preferred_types: Set[str]
) -> List[db_models.Product]:
    """
    Apply a diversity factor to ensure representation of different meat types.
    
    Args:
        scored_products: List of (product, score) tuples
        limit: Maximum number of products to return
        preferred_types: Set of preferred meat types
        
    Returns:
        List of products with diversity factor applied
    """
    if not scored_products:
        return []
    
    # If no preferred types, use all available types from scored products
    if not preferred_types:
        preferred_types = set(p.meat_type for p, _ in scored_products if p.meat_type)
    
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
        meat_type = product.meat_type
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