"""Natural language search service for meat products."""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple

import google.generativeai as genai
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.core.config import settings
from app.core.cache import cache  # Use unified cache
from app.db import models as db_models

logger = logging.getLogger(__name__)

# Common brand names for product name search detection
COMMON_BRANDS = [
    "kroger", "tyson", "oscar mayer", "hillshire", "applegate", "hormel", 
    "jennie-o", "butterball", "foster farms", "perdue", "smithfield",
    "johnsonville", "hebrew national", "boar's head", "armour", "spam",
    "simple truth", "organic prairie", "trader joe's", "whole foods",
    "great value", "kirkland", "member's mark", "umeya"
]

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
    
    # Create cache key for this query
    cache_key = cache.generate_key(query.lower(), prefix="search_intent")
    
    # Check cache first
    cached_intent = cache.get(cache_key)
    if cached_intent:
        logger.debug(f"Using cached intent for query: {query}")
        intent = SearchIntent()
        for key, value in cached_intent.items():
            setattr(intent, key, value)
        return intent
    
    # Try Gemini AI first for complex queries
    gemini_intent = parse_with_gemini(query)
    if gemini_intent:
        # Cache the result with longer TTL for AI results (2 hours)
        cache.set(cache_key, gemini_intent.to_dict(), ttl=7200)
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
    
    # Cache the result (1 hour for rule-based)
    cache.set(cache_key, intent.to_dict(), ttl=3600)
    
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

def calculate_name_match_score(query: str, product) -> int:
    """Simple scoring for name matches."""
    query_lower = query.lower()
    name_lower = (product.name or "").lower()
    brand_lower = (product.brand or "").lower()
    description_lower = (product.description or "").lower()
    
    score = 0
    
    # Exact name match = high score
    if query_lower in name_lower:
        score += 50
    
    # Brand match = medium score  
    if any(word in brand_lower for word in query_lower.split()):
        score += 30
        
    # Count matching keywords
    query_words = set(word for word in query_lower.split() if len(word) > 2)  # Ignore short words
    name_words = set(word for word in name_lower.split() if len(word) > 2)
    brand_words = set(word for word in brand_lower.split() if len(word) > 2)
    desc_words = set(word for word in description_lower.split() if len(word) > 2)
    
    # Score based on matching words
    name_matches = query_words.intersection(name_words)
    brand_matches = query_words.intersection(brand_words)
    desc_matches = query_words.intersection(desc_words)
    
    score += len(name_matches) * 10     # Name matches worth more
    score += len(brand_matches) * 8     # Brand matches worth medium
    score += len(desc_matches) * 3      # Description matches worth less
    
    # Bonus for consecutive word matches
    if len(name_matches) > 1:
        score += 15
    
    return score

def search_by_product_name(query: str, db: Session, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
    """Simple text search across product name, brand, and description."""
    
    logger.info(f"Performing direct product name search for: '{query}'")
    
    # Split query into keywords (ignore very short words)
    keywords = [word.strip() for word in query.lower().split() if len(word.strip()) > 2]
    
    if not keywords:
        return []
    
    # Build ILIKE filters for each keyword - use OR logic for more results
    keyword_conditions = []
    for keyword in keywords:
        keyword_conditions.extend([
            func.lower(db_models.Product.name).like(f'%{keyword}%'),
            func.lower(db_models.Product.brand).like(f'%{keyword}%'),
            func.lower(db_models.Product.description).like(f'%{keyword}%')
        ])
    
    # Execute query with OR logic for keywords
    products = (
        db.query(db_models.Product)
        .filter(or_(*keyword_conditions))  # Changed from AND to OR
        .limit(limit * 3)  # Get more results to score and filter
        .all()
    )
    
    logger.info(f"Found {len(products)} products before scoring")
    
    # Score and format results
    results = []
    for product in products:
        score = calculate_name_match_score(query, product)
        
        # Only include results with reasonable scores
        if score > 5:
            # Convert product to dict safely
            product_dict = {
                'code': product.code,
                'name': product.name,
                'brand': product.brand,
                'description': product.description,
                'ingredients_text': product.ingredients_text,
                'calories': product.calories,
                'protein': product.protein,
                'fat': product.fat,
                'carbohydrates': product.carbohydrates,
                'salt': product.salt,
                'meat_type': product.meat_type,
                'risk_rating': product.risk_rating,
                'image_url': product.image_url,
                'last_updated': product.last_updated.isoformat() if product.last_updated else None,
                'created_at': product.created_at.isoformat() if product.created_at else None,
                'antibiotic_free': getattr(product, 'antibiotic_free', None),
                'hormone_free': getattr(product, 'hormone_free', None),
                'pasture_raised': getattr(product, 'pasture_raised', None),
                'contains_preservatives': getattr(product, 'contains_preservatives', None),
                'match_score': score,
                'matched_terms': ["direct_name_search"]
            }
            results.append(product_dict)
    
    # Sort by score descending and apply pagination
    results.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Apply pagination
    paginated_results = results[skip:skip + limit]
    
    logger.info(f"Returning {len(paginated_results)} products after scoring and pagination")
    
    return paginated_results

def search_by_intent(query: str, db: Session, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
    """AI-enhanced intent search (existing functionality)."""
    
    logger.info(f"Performing AI-enhanced intent search for: '{query}'")
    
    # Use existing search logic
    intent = parse_natural_language_query(query)
    logger.info(f"Parsed intent: {intent.to_dict()}")
    
    # Build base query
    query_obj = db.query(db_models.Product)
    initial_query = query_obj
    
    # Apply filters based on intent
    query_obj = build_database_filters(intent, query_obj)
    
    # First attempt with all filters
    products = query_obj.offset(skip).limit(limit * 2).all()
    logger.info(f"Found {len(products)} products with all filters")
    
    # If no results with all filters, progressively relax them
    if len(products) == 0 and (intent.meat_types or intent.risk_preference):
        logger.info("No results with all filters, trying relaxed search...")
        
        # Try without risk preference first
        if intent.risk_preference:
            original_risk_pref = intent.risk_preference
            intent.risk_preference = None
            query_obj = initial_query
            query_obj = build_database_filters(intent, query_obj)
            products = query_obj.offset(skip).limit(limit * 2).all()
            logger.info(f"Found {len(products)} products without risk preference filter")
            intent.risk_preference = original_risk_pref  # Restore for scoring
        
        # If still no results and we have meat type, try keyword search
        if len(products) == 0:
            logger.info("Still no results, falling back to simple keyword search")
            keyword_conditions = []
            
            # Add meat type as keyword if specified
            if intent.meat_types:
                for meat_type in intent.meat_types:
                    keyword_conditions.extend([
                        func.lower(db_models.Product.name).like(f'%{meat_type}%'),
                        func.lower(db_models.Product.description).like(f'%{meat_type}%'),
                        func.lower(db_models.Product.meat_type).like(f'%{meat_type}%')
                    ])
            
            # Add other keywords
            for keyword in query.lower().split():
                if len(keyword) > 2:
                    keyword_conditions.extend([
                        func.lower(db_models.Product.name).like(f'%{keyword}%'),
                        func.lower(db_models.Product.description).like(f'%{keyword}%')
                    ])
            
            if keyword_conditions:
                query_obj = initial_query.filter(or_(*keyword_conditions))
                products = query_obj.offset(skip).limit(limit * 2).all()
                logger.info(f"Found {len(products)} products with keyword fallback")
    
    # If no filters were applied originally, use keyword search
    elif not any([intent.meat_types, intent.nutritional_constraints, intent.health_preferences, 
                intent.risk_preference, intent.product_types, intent.exclude_ingredients]):
        # Use simple keyword search as fallback
        keyword_conditions = []
        for keyword in query.lower().split():
            if len(keyword) > 2:
                keyword_conditions.extend([
                    func.lower(db_models.Product.name).like(f'%{keyword}%'),
                    func.lower(db_models.Product.description).like(f'%{keyword}%'),
                    func.lower(db_models.Product.meat_type).like(f'%{keyword}%')
                ])
        
        if keyword_conditions:
            query_obj = query_obj.filter(or_(*keyword_conditions))
            products = query_obj.offset(skip).limit(limit * 2).all()
    
    logger.info(f"Final result: Found {len(products)} products from database query")
    
    # Score and format results
    results = []
    for product in products:
        score, matched_terms = calculate_match_score(product, intent)
        
        # If no specific match score, but keywords match, give base score
        if score == 0 and any(keyword.lower() in (product.name or "").lower() or 
                             keyword.lower() in (product.description or "").lower() 
                             for keyword in query.lower().split() if len(keyword) > 2):
            score = 10
            matched_terms.append("keyword_match")
        
        if score > 0:  # Only include products with some relevance
            # Convert product to dict safely
            product_dict = {
                'code': product.code,
                'name': product.name,
                'brand': product.brand,
                'description': product.description,
                'ingredients_text': product.ingredients_text,
                'calories': product.calories,
                'protein': product.protein,
                'fat': product.fat,
                'carbohydrates': product.carbohydrates,
                'salt': product.salt,
                'meat_type': product.meat_type,
                'risk_rating': product.risk_rating,
                'image_url': product.image_url,
                'last_updated': product.last_updated.isoformat() if product.last_updated else None,
                'created_at': product.created_at.isoformat() if product.created_at else None,
                'antibiotic_free': getattr(product, 'antibiotic_free', None),
                'hormone_free': getattr(product, 'hormone_free', None),
                'pasture_raised': getattr(product, 'pasture_raised', None),
                'contains_preservatives': getattr(product, 'contains_preservatives', None),
                'match_score': score,
                'matched_terms': matched_terms
            }
            results.append(product_dict)
    
    # Sort by score and apply final limit
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:limit]

def search_products(query: str, db: Session, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
    """Route to appropriate search method based on query type."""
    
    if is_product_name_search(query):
        logger.info(f"Using direct product name search for: '{query}'")
        return search_by_product_name(query, db, limit, skip)
    else:
        logger.info(f"Using AI-enhanced intent search for: '{query}'")
        return search_by_intent(query, db, limit, skip)

def build_database_filters(intent: SearchIntent, query_obj):
    """Apply search filters to the database query based on intent."""
    
    # Meat type filter
    if intent.meat_types:
        meat_filters = [db_models.Product.meat_type == meat_type for meat_type in intent.meat_types]
        query_obj = query_obj.filter(or_(*meat_filters))
    
    # Nutritional constraints
    for constraint, value in intent.nutritional_constraints.items():
        if constraint == "max_salt" and hasattr(db_models.Product, 'salt'):
            query_obj = query_obj.filter(and_(
                db_models.Product.salt.isnot(None),
                db_models.Product.salt <= value
            ))
        elif constraint == "min_protein" and hasattr(db_models.Product, 'protein'):
            query_obj = query_obj.filter(and_(
                db_models.Product.protein.isnot(None),
                db_models.Product.protein >= value
            ))
        elif constraint == "max_fat" and hasattr(db_models.Product, 'fat'):
            query_obj = query_obj.filter(and_(
                db_models.Product.fat.isnot(None),
                db_models.Product.fat <= value
            ))
        elif constraint == "max_carbohydrates" and hasattr(db_models.Product, 'carbohydrates'):
            query_obj = query_obj.filter(and_(
                db_models.Product.carbohydrates.isnot(None),
                db_models.Product.carbohydrates <= value
            ))
    
    # Health preferences
    if intent.health_preferences:
        health_conditions = []
        for pref in intent.health_preferences:
            if pref == "organic":
                health_conditions.extend([
                    func.lower(db_models.Product.name).like('%organic%'),
                    func.lower(db_models.Product.description).like('%organic%'),
                    func.lower(db_models.Product.brand).like('%organic%')
                ])
            elif pref == "grass_fed":
                health_conditions.extend([
                    func.lower(db_models.Product.name).like('%grass-fed%'),
                    func.lower(db_models.Product.description).like('%grass-fed%'),
                    func.lower(db_models.Product.ingredients_text).like('%grass-fed%')
                ])
            elif pref == "antibiotic_free":
                health_conditions.extend([
                    func.lower(db_models.Product.name).like('%antibiotic%'),
                    func.lower(db_models.Product.description).like('%antibiotic%')
                ])
            elif pref == "hormone_free":
                health_conditions.extend([
                    func.lower(db_models.Product.name).like('%hormone%'),
                    func.lower(db_models.Product.description).like('%hormone%')
                ])
            elif pref == "preservative_free":
                health_conditions.extend([
                    func.lower(db_models.Product.name).like('%preservative-free%'),
                    func.lower(db_models.Product.description).like('%no preservative%')
                ])
            elif pref == "nitrite_free":
                health_conditions.extend([
                    func.lower(db_models.Product.name).like('%nitrite-free%'),
                    func.lower(db_models.Product.description).like('%no nitrite%')
                ])
        
        if health_conditions:
            query_obj = query_obj.filter(or_(*health_conditions))
    
    # Exclude ingredients
    if intent.exclude_ingredients:
        for ingredient in intent.exclude_ingredients:
            if ingredient.lower() == "preservatives":
                query_obj = query_obj.filter(
                    ~func.lower(db_models.Product.ingredients_text).like('%preservative%')
                )
            elif ingredient.lower() == "nitrites":
                query_obj = query_obj.filter(
                    ~func.lower(db_models.Product.ingredients_text).like('%nitrite%')
                )
            elif ingredient.lower() == "msg":
                query_obj = query_obj.filter(and_(
                    ~func.lower(db_models.Product.ingredients_text).like('%msg%'),
                    ~func.lower(db_models.Product.ingredients_text).like('%monosodium glutamate%')
                ))
            elif ingredient.lower() == "sugar":
                query_obj = query_obj.filter(and_(
                    ~func.lower(db_models.Product.ingredients_text).like('%sugar%'),
                    ~func.lower(db_models.Product.ingredients_text).like('%corn syrup%')
                ))
            elif ingredient.lower() == "phosphates":
                query_obj = query_obj.filter(
                    ~func.lower(db_models.Product.ingredients_text).like('%phosphate%')
                )
    
    # Risk preference
    if intent.risk_preference:
        query_obj = query_obj.filter(db_models.Product.risk_rating == intent.risk_preference)
    
    # Product type filters
    if intent.product_types:
        product_conditions = []
        for product_type in intent.product_types:
            product_conditions.extend([
                func.lower(db_models.Product.name).like(f'%{product_type}%'),
                func.lower(db_models.Product.description).like(f'%{product_type}%')
            ])
        
        if product_conditions:
            query_obj = query_obj.filter(or_(*product_conditions))
    
    # Keywords search
    if intent.keywords:
        keyword_conditions = []
        for keyword in intent.keywords:
            if len(keyword) > 2:
                keyword_conditions.extend([
                    func.lower(db_models.Product.name).like(f'%{keyword}%'),
                    func.lower(db_models.Product.description).like(f'%{keyword}%'),
                    func.lower(db_models.Product.ingredients_text).like(f'%{keyword}%')
                ])
        
        if keyword_conditions:
            query_obj = query_obj.filter(or_(*keyword_conditions))
    
    return query_obj 

def is_product_name_search(query: str) -> bool:
    """Simple detection: is this a direct product name search?"""
    
    query_lower = query.lower()
    
    # Indicators of product name search
    product_name_indicators = [
        "," in query,                    # "Kroger, smokehouse jerky"
        len(query.split()) >= 4,         # Multi-word product names
        any(brand in query_lower for brand in COMMON_BRANDS)  # Known brands
    ]
    
    # Indicators of intent search  
    intent_indicators = [
        any(word in query_lower for word in ["low", "high", "no", "free", "organic", "healthy", "without", "lean"])
    ]
    
    has_product_indicators = any(product_name_indicators)
    has_intent_indicators = any(intent_indicators)
    
    logger.debug(f"Query '{query}': product_indicators={has_product_indicators}, intent_indicators={has_intent_indicators}")
    
    return has_product_indicators and not has_intent_indicators 

def calculate_match_score(product: db_models.Product, intent: SearchIntent) -> Tuple[int, List[str]]:
    """Calculate match score and identify matched terms for intent-based search."""
    
    score = 0
    matched_terms = []
    
    # Meat type match (high priority)
    if intent.meat_types and hasattr(product, 'meat_type') and product.meat_type:
        if product.meat_type in intent.meat_types:
            score += 30
            matched_terms.append(f"meat_type:{product.meat_type}")
    
    # Nutritional constraints (high priority)
    for constraint, value in intent.nutritional_constraints.items():
        if constraint == "max_salt" and hasattr(product, 'salt') and product.salt:
            if product.salt <= value:
                score += 25
                matched_terms.append("nutrition:low_sodium")
        elif constraint == "min_protein" and hasattr(product, 'protein') and product.protein:
            if product.protein >= value:
                score += 25
                matched_terms.append("nutrition:high_protein")
        elif constraint == "max_fat" and hasattr(product, 'fat') and product.fat:
            if product.fat <= value:
                score += 20
                matched_terms.append("nutrition:low_fat")
        elif constraint == "max_carbohydrates" and hasattr(product, 'carbohydrates') and product.carbohydrates:
            if product.carbohydrates <= value:
                score += 20
                matched_terms.append("nutrition:low_carbs")
    
    # Health preferences (medium priority)
    for preference in intent.health_preferences:
        if preference == "organic":
            if any(field and "organic" in field.lower() 
                   for field in [product.name, product.description, product.brand] if field):
                score += 15
                matched_terms.append("health:organic")
        elif preference == "grass_fed":
            if any(field and "grass" in field.lower() and "fed" in field.lower()
                   for field in [product.name, product.description, product.ingredients_text] if field):
                score += 15
                matched_terms.append("health:grass_fed")
        elif preference == "antibiotic_free":
            if any(field and "antibiotic" in field.lower()
                   for field in [product.name, product.description] if field):
                score += 12
                matched_terms.append("health:antibiotic_free")
        elif preference == "hormone_free":
            if any(field and "hormone" in field.lower()
                   for field in [product.name, product.description] if field):
                score += 12
                matched_terms.append("health:hormone_free")
    
    # Risk rating preference (medium priority)
    if intent.risk_preference and hasattr(product, 'risk_rating') and product.risk_rating:
        if product.risk_rating == intent.risk_preference:
            score += 15
            matched_terms.append(f"risk:{product.risk_rating}")
    
    # Product type matches (medium priority)
    for product_type in intent.product_types:
        if any(field and product_type.lower() in field.lower()
               for field in [product.name, product.description] if field):
            score += 10
            matched_terms.append(f"type:{product_type}")
    
    # Keyword matches (lower priority)
    for keyword in intent.keywords:
        if len(keyword) > 2:
            if any(field and keyword.lower() in field.lower()
                   for field in [product.name, product.description, product.ingredients_text] if field):
                score += 5
                matched_terms.append(f"keyword:{keyword}")
    
    return score, matched_terms 