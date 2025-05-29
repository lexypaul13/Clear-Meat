"""Natural language search service for meat products."""

import json
import logging
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple

import google.generativeai as genai
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.core.config import settings
from app.db import models as db_models

logger = logging.getLogger(__name__)

# Simple in-memory cache for parsed queries
# Structure: {query_hash: {"intent": parsed_intent, "expires_at": timestamp}}
_query_cache = {}

# Configure Gemini if API key is available
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    logger.info("Gemini AI configured for natural language search")
else:
    logger.warning("Gemini API key not configured - using rule-based parsing only")

class SearchIntent:
    """Structured representation of search intent."""
    
    def __init__(self):
        self.meat_types: List[str] = []
        self.nutritional_constraints: Dict[str, Any] = {}
        self.health_preferences: List[str] = []
        self.product_types: List[str] = []
        self.keywords: List[str] = []
        self.exclude_ingredients: List[str] = []
        self.risk_preference: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "meat_types": self.meat_types,
            "nutritional_constraints": self.nutritional_constraints,
            "health_preferences": self.health_preferences,
            "product_types": self.product_types,
            "keywords": self.keywords,
            "exclude_ingredients": self.exclude_ingredients,
            "risk_preference": self.risk_preference
        }

def parse_with_gemini(query: str) -> Optional[SearchIntent]:
    """Use Gemini AI to parse complex natural language queries."""
    
    if not settings.GEMINI_API_KEY:
        return None
        
    prompt = f"""Parse this natural language search query for meat products into structured search criteria.

Query: "{query}"

Extract the following information if present:
1. Meat types (beef, chicken, turkey, pork, lamb, etc.)
2. Nutritional constraints with specific values:
   - Low sodium/salt: max_salt = 1.0g
   - High protein: min_protein = 20.0g  
   - Low fat: max_fat = 10.0g
   - No sugar/sugar-free: max_carbohydrates = 5.0g
3. Health preferences: organic, grass-fed, antibiotic-free, hormone-free, preservative-free, nitrite-free
4. Product types: jerky, snacks, breast, patties, bacon, nuggets, sausage, ground, sliced
5. Ingredients to exclude: nitrites, preservatives, MSG, sugar, phosphates
6. Risk preference: if user wants "healthy", "safe", or mentions "green", set to "Green"
7. Any other relevant keywords

Respond with JSON only in this exact format:
{{
  "meat_types": ["chicken"],
  "nutritional_constraints": {{
    "max_salt": 1.0,
    "min_protein": 20.0
  }},
  "health_preferences": ["organic", "antibiotic_free"],
  "product_types": ["snacks"],
  "exclude_ingredients": ["sugar", "preservatives"],
  "risk_preference": "Green",
  "keywords": ["healthy", "natural"]
}}"""

    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL or 'gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Parse JSON response
        text = response.text.strip()
        if text.startswith("```json") and text.endswith("```"):
            json_content = text[7:-3].strip()
        else:
            json_content = text
            
        parsed_data = json.loads(json_content)
        
        # Convert to SearchIntent
        intent = SearchIntent()
        intent.meat_types = parsed_data.get('meat_types', [])
        intent.nutritional_constraints = parsed_data.get('nutritional_constraints', {})
        intent.health_preferences = parsed_data.get('health_preferences', [])
        intent.product_types = parsed_data.get('product_types', [])
        intent.keywords = parsed_data.get('keywords', [])
        intent.exclude_ingredients = parsed_data.get('exclude_ingredients', [])
        intent.risk_preference = parsed_data.get('risk_preference')
        
        logger.info(f"Gemini parsed query '{query}' successfully")
        return intent
        
    except Exception as e:
        logger.warning(f"Failed to parse query with Gemini: {e}")
        return None

def parse_natural_language_query(query: str) -> SearchIntent:
    """Parse natural language query into structured search intent."""
    
    # Create cache key
    cache_key = hashlib.md5(query.lower().encode()).hexdigest()
    current_time = time.time()
    
    # Check cache first
    if cache_key in _query_cache:
        cached_entry = _query_cache[cache_key]
        if cached_entry["expires_at"] > current_time:
            logger.debug(f"Using cached intent for query: {query}")
            intent = SearchIntent()
            for key, value in cached_entry["intent"].items():
                setattr(intent, key, value)
            return intent
    
    # Try Gemini AI first for complex queries
    gemini_intent = parse_with_gemini(query)
    if gemini_intent:
        # Cache the result (expires in 1 hour)
        _query_cache[cache_key] = {
            "intent": gemini_intent.to_dict(),
            "expires_at": current_time + 3600
        }
        return gemini_intent
    
    # Fallback to rule-based parsing
    intent = SearchIntent()
    query_lower = query.lower()
    
    # Extract meat types
    meat_types = []
    if "chicken" in query_lower:
        meat_types.append("chicken")
    if "beef" in query_lower:
        meat_types.append("beef")
    if "pork" in query_lower:
        meat_types.append("pork")
    if "turkey" in query_lower:
        meat_types.append("turkey")
    if "lamb" in query_lower:
        meat_types.append("lamb")
    
    intent.meat_types = meat_types
    
    # Extract nutritional constraints
    nutritional_constraints = {}
    if "low sodium" in query_lower or "low salt" in query_lower:
        nutritional_constraints["max_salt"] = 1.0
    if "high protein" in query_lower:
        nutritional_constraints["min_protein"] = 20.0
    if "low fat" in query_lower:
        nutritional_constraints["max_fat"] = 10.0
    if "no sugar" in query_lower or "sugar-free" in query_lower:
        nutritional_constraints["max_carbohydrates"] = 5.0
    
    intent.nutritional_constraints = nutritional_constraints
    
    # Extract health preferences
    health_preferences = []
    if "organic" in query_lower:
        health_preferences.append("organic")
    if "grass-fed" in query_lower or "grass fed" in query_lower:
        health_preferences.append("grass_fed")
    if "antibiotic" in query_lower and "free" in query_lower:
        health_preferences.append("antibiotic_free")
    if "preservative" in query_lower and "free" in query_lower:
        health_preferences.append("preservative_free")
    if "nitrite" in query_lower and "free" in query_lower:
        health_preferences.append("nitrite_free")
    if "hormone" in query_lower and "free" in query_lower:
        health_preferences.append("hormone_free")
    
    intent.health_preferences = health_preferences
    
    # Extract product types
    product_types = []
    if "jerky" in query_lower:
        product_types.append("jerky")
    if "snack" in query_lower:
        product_types.append("snack")
    if "breast" in query_lower:
        product_types.append("breast")
    if "patties" in query_lower or "patty" in query_lower:
        product_types.append("patties")
    if "bacon" in query_lower:
        product_types.append("bacon")
    if "nugget" in query_lower:
        product_types.append("nuggets")
    if "sausage" in query_lower:
        product_types.append("sausage")
    if "ground" in query_lower:
        product_types.append("ground")
    if "sliced" in query_lower:
        product_types.append("sliced")
    
    intent.product_types = product_types
    
    # Extract exclude ingredients
    exclude_ingredients = []
    if "no preservative" in query_lower:
        exclude_ingredients.append("preservatives")
    if "no nitrite" in query_lower:
        exclude_ingredients.append("nitrites")
    if "no msg" in query_lower:
        exclude_ingredients.append("MSG")
    if "no sugar" in query_lower:
        exclude_ingredients.append("sugar")
    
    intent.exclude_ingredients = exclude_ingredients
    
    # Extract risk preference
    if any(term in query_lower for term in ["healthy", "safe", "green"]):
        intent.risk_preference = "Green"
    
    # Extract general keywords
    keywords = query_lower.split()
    intent.keywords = [k for k in keywords if len(k) > 2]
    
    # Cache the result (expires in 1 hour)
    _query_cache[cache_key] = {
        "intent": intent.to_dict(),
        "expires_at": current_time + 3600
    }
    
    logger.info(f"Rule-based parsed query '{query}' -> Intent: {intent.to_dict()}")
    return intent

def build_search_filters(intent: SearchIntent, db: Session) -> Tuple[List, Dict[str, Any]]:
    """Build SQLAlchemy filters from search intent."""
    
    filters = []
    ranking_factors = {}
    
    # Meat type filter
    if intent.meat_types:
        filters.append(db_models.Product.meat_type.in_(intent.meat_types))
        ranking_factors["meat_type_match"] = True
    
    # Nutritional constraints - only use fields that exist in the model
    if intent.nutritional_constraints:
        for constraint, value in intent.nutritional_constraints.items():
            if constraint == "max_salt" and hasattr(db_models.Product, 'salt'):
                filters.append(db_models.Product.salt <= value)
                ranking_factors["low_sodium"] = True
            elif constraint == "min_protein" and hasattr(db_models.Product, 'protein'):
                filters.append(db_models.Product.protein >= value)
                ranking_factors["high_protein"] = True
            elif constraint == "max_fat" and hasattr(db_models.Product, 'fat'):
                filters.append(db_models.Product.fat <= value)
                ranking_factors["low_fat"] = True
            elif constraint == "max_carbohydrates" and hasattr(db_models.Product, 'carbohydrates'):
                filters.append(db_models.Product.carbohydrates <= value)
                ranking_factors["low_carbs"] = True
    
    # Health preferences - search in description and ingredients
    if intent.health_preferences:
        health_conditions = []
        for pref in intent.health_preferences:
            if pref == "organic":
                health_conditions.append(db_models.Product.name.ilike('%organic%'))
                health_conditions.append(db_models.Product.description.ilike('%organic%'))
                ranking_factors["organic"] = True
            elif pref == "grass_fed":
                health_conditions.append(db_models.Product.name.ilike('%grass-fed%'))
                health_conditions.append(db_models.Product.description.ilike('%grass-fed%'))
                health_conditions.append(db_models.Product.ingredients_text.ilike('%grass-fed%'))
                ranking_factors["grass_fed"] = True
            elif pref == "preservative_free":
                health_conditions.append(db_models.Product.description.ilike('%no preservative%'))
                health_conditions.append(~db_models.Product.ingredients_text.ilike('%preservative%'))
                ranking_factors["preservative_free"] = True
            elif pref == "antibiotic_free":
                health_conditions.append(db_models.Product.description.ilike('%antibiotic%'))
                ranking_factors["antibiotic_free"] = True
            elif pref == "hormone_free":
                health_conditions.append(db_models.Product.description.ilike('%hormone%'))
                ranking_factors["hormone_free"] = True
            elif pref == "nitrite_free":
                health_conditions.append(~db_models.Product.ingredients_text.ilike('%nitrite%'))
                ranking_factors["nitrite_free"] = True
        
        if health_conditions:
            filters.append(or_(*health_conditions))
    
    # Exclude ingredients
    if intent.exclude_ingredients:
        exclude_conditions = []
        for ingredient in intent.exclude_ingredients:
            if ingredient.lower() == "preservatives":
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%preservative%'))
            elif ingredient.lower() == "nitrites":
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%nitrite%'))
            elif ingredient.lower() == "msg":
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%msg%'))
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%monosodium glutamate%'))
            elif ingredient.lower() == "sugar":
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%sugar%'))
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%corn syrup%'))
            elif ingredient.lower() == "phosphates":
                exclude_conditions.append(~db_models.Product.ingredients_text.ilike('%phosphate%'))
        
        if exclude_conditions:
            filters.extend(exclude_conditions)
            ranking_factors["exclude_ingredients"] = True
    
    # Risk preference filter
    if intent.risk_preference:
        filters.append(db_models.Product.risk_rating == intent.risk_preference)
        ranking_factors["risk_preference_match"] = True
    
    # Product type filters
    if intent.product_types:
        product_conditions = []
        for product_type in intent.product_types:
            product_conditions.append(db_models.Product.name.ilike(f'%{product_type}%'))
        
        if product_conditions:
            filters.append(or_(*product_conditions))
            ranking_factors["product_type_match"] = True
    
    # Keywords search in name, description, and ingredients
    if intent.keywords:
        keyword_conditions = []
        for keyword in intent.keywords:
            if len(keyword) > 2:  # Skip very short words
                keyword_conditions.extend([
                    db_models.Product.name.ilike(f'%{keyword}%'),
                    db_models.Product.description.ilike(f'%{keyword}%'),
                    db_models.Product.ingredients_text.ilike(f'%{keyword}%')
                ])
        
        if keyword_conditions:
            filters.append(or_(*keyword_conditions))
            ranking_factors["keyword_match"] = True
    
    return filters, ranking_factors

def calculate_match_score(product: db_models.Product, intent: SearchIntent, ranking_factors: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Calculate match score and identify matched terms."""
    
    score = 0
    matched_terms = []
    
    # Meat type match (high priority)
    if intent.meat_types and product.meat_type in intent.meat_types:
        score += 20
        matched_terms.append(f"meat_type:{product.meat_type}")
    
    # Nutritional constraints
    if intent.nutritional_constraints:
        for constraint, value in intent.nutritional_constraints.items():
            if constraint == "max_salt" and product.salt and product.salt <= value:
                score += 15
                matched_terms.append("nutrition:low_sodium")
            elif constraint == "min_protein" and product.protein and product.protein >= value:
                score += 15
                matched_terms.append("nutrition:high_protein")
            elif constraint == "max_fat" and product.fat and product.fat <= value:
                score += 10
                matched_terms.append("nutrition:low_fat")
            elif constraint == "max_carbohydrates" and product.carbohydrates and product.carbohydrates <= value:
                score += 10
                matched_terms.append("nutrition:low_carbs")
    
    # Product name keywords
    if intent.keywords:
        product_name_lower = (product.name or "").lower()
        for keyword in intent.keywords:
            if len(keyword) > 2 and keyword in product_name_lower:
                score += 10
                matched_terms.append(f"name:{keyword}")
    
    # Health preferences in description
    if intent.health_preferences:
        description_lower = (product.description or "").lower()
        for pref in intent.health_preferences:
            if pref == "organic" and "organic" in description_lower:
                score += 15
                matched_terms.append("health:organic")
            elif pref == "grass_fed" and "grass-fed" in description_lower:
                score += 15
                matched_terms.append("health:grass_fed")
    
    # Risk rating bonus (Green is better)
    if product.risk_rating == "Green":
        score += 5
        matched_terms.append("risk:green")
    elif product.risk_rating == "Yellow":
        score += 2
    
    return score, matched_terms

def search_products(query: str, db: Session, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Main search function that combines natural language processing with database queries.
    
    Args:
        query: Natural language search query
        db: Database session
        limit: Maximum number of results to return
        skip: Number of results to skip for pagination
        
    Returns:
        List of products with match scores and matched terms
    """
    
    logger.info(f"Searching for: '{query}' (limit: {limit}, skip: {skip})")
    
    try:
        # Parse the natural language query
        intent = parse_natural_language_query(query)
        
        # Build database filters
        filters, ranking_factors = build_search_filters(intent, db)
        
        # Execute search query
        query_builder = db.query(db_models.Product)
        
        if filters:
            query_builder = query_builder.filter(and_(*filters))
        
        # Get results
        products = query_builder.offset(skip).limit(limit * 2).all()  # Get more than needed for ranking
        
        # Calculate match scores and rank results
        scored_products = []
        for product in products:
            score, matched_terms = calculate_match_score(product, intent, ranking_factors)
            
            # Convert to dict and add score info
            product_dict = {
                "code": product.code,
                "name": product.name,
                "brand": product.brand,
                "description": product.description,
                "ingredients_text": product.ingredients_text,
                "calories": product.calories,
                "protein": product.protein,
                "fat": product.fat,
                "carbohydrates": product.carbohydrates,
                "salt": product.salt,
                "meat_type": product.meat_type,
                "risk_rating": product.risk_rating,
                "image_url": product.image_url,
                "last_updated": product.last_updated,
                "created_at": product.created_at,
                # Note: Only include fields that exist in the SQLAlchemy model
                "antibiotic_free": getattr(product, 'antibiotic_free', None),
                "hormone_free": getattr(product, 'hormone_free', None),
                "pasture_raised": getattr(product, 'pasture_raised', None),
                "contains_preservatives": getattr(product, 'contains_preservatives', None),
                "match_score": score,
                "matched_terms": matched_terms
            }
            
            scored_products.append(product_dict)
        
        # Sort by score (highest first) and return top results
        scored_products.sort(key=lambda x: x["match_score"], reverse=True)
        final_results = scored_products[:limit]
        
        logger.info(f"Found {len(final_results)} products for query: '{query}'")
        return final_results
        
    except Exception as e:
        logger.error(f"Error in search_products: {str(e)}")
        raise 