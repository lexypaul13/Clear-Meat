"""Health assessment service using Gemini for product analysis."""
import json
import logging
import time
import random
import re
import datetime
import hashlib
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cache import cache, CacheService  # Use unified cache
from app.models.product import HealthAssessment, ProductStructured
from app.api.v1.models import EnhancedHealthAssessment
from app.db import models as db_models
# Citation service removed - using AI-generated responses only

logger = logging.getLogger(__name__)

def parse_ingredients_list(ingredients_text: str, max_ingredients: int = 100) -> List[str]:
    """Parse ingredients text into individual ingredients array with memory optimization."""
    if not ingredients_text or not ingredients_text.strip():
        return []
    
    # Memory optimization: truncate very long ingredient texts
    if len(ingredients_text) > 5000:
        logger.warning(f"Truncating long ingredients text ({len(ingredients_text)} chars)")
        ingredients_text = ingredients_text[:5000] + "..."
    
    # Split by common delimiters (commas, semicolons, periods followed by spaces)
    # Handle periods that separate ingredient sections
    text = re.sub(r'\.\s+([A-Z])', r'. \1', ingredients_text)  # Ensure space after period before capital letter
    ingredients = re.split(r'[,;]\s*|\.\s+(?=[A-Z])', text)
    
    parsed = []
    
    # Process in batches to avoid memory issues with very long ingredient lists
    batch_size = 50
    for i in range(0, len(ingredients), batch_size):
        batch = ingredients[i:i + batch_size]
        
        for ingredient in batch:
            # Clean up each ingredient
            cleaned = ingredient.strip()
            
            # Remove parentheses content (like (E250), (preservative), etc.)
            cleaned = re.sub(r'\([^)]*\)', '', cleaned).strip()
            
            # Remove percentage indicators
            cleaned = re.sub(r'^\d+%\s*', '', cleaned).strip()
            
            # Remove leading/trailing punctuation except colons (for "conservateur : E250")
            cleaned = re.sub(r'^[.•-]\s*', '', cleaned).strip()
            cleaned = re.sub(r'[.•-]\s*$', '', cleaned).strip()
            
            # Split on periods that aren't part of abbreviations and create sub-ingredients
            if '.' in cleaned and not re.search(r'\b[A-Z]\.\s*[A-Z]', cleaned):  # Don't split abbreviations like "U.E"
                sub_ingredients = [s.strip() for s in cleaned.split('.') if s.strip()]
                for sub in sub_ingredients:
                    if sub and len(sub) > 1:
                        parsed.append(sub)
                        if len(parsed) >= max_ingredients:
                            logger.warning(f"Reached max ingredients limit ({max_ingredients})")
                            return parsed
            else:
                # Only include non-empty ingredients with at least 2 characters
                if cleaned and len(cleaned) > 1:
                    parsed.append(cleaned)
                    if len(parsed) >= max_ingredients:
                        logger.warning(f"Reached max ingredients limit ({max_ingredients})")
                        return parsed
    
    return parsed

def _hash_ingredients(ingredients_text: str) -> str:
    """Create stable hash of ingredients for better cache reuse."""
    if not ingredients_text:
        return "empty"
    
    # Normalize ingredients for consistent hashing
    normalized = ingredients_text.lower().strip()
    # Remove common variations that don't affect health assessment
    normalized = re.sub(r'\s+', '', normalized)  # Remove all whitespace
    normalized = re.sub(r'[,;.]', '', normalized)  # Remove punctuation
    normalized = re.sub(r'\([^)]*\)', '', normalized)  # Remove parenthetical content
    
    # Create hash
    return hashlib.md5(normalized.encode()).hexdigest()[:12]

class HealthAssessmentService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        # Configure Gemini API key
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Citation service removed - using AI-generated responses only

def generate_health_assessment(product: ProductStructured, db: Optional[Session] = None) -> Optional[HealthAssessment]:
    """
    Generate a detailed health assessment for a product using Gemini with optimized caching.
    
    Args:
        product: The structured product data to analyze
        db: Database session for finding similar products for recommendations
        
    Returns:
        HealthAssessment: The AI-generated health assessment or None if generation failed
    """
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return None
    
    # Generate cache key based on ingredients hash for better cache reuse
    ingredients_hash = _hash_ingredients(product.product.ingredients_text or "")
    cache_key = CacheService.generate_key(f"{product.product.code}:{ingredients_hash}", prefix="health_assessment")
    
    # Check cache first with more detailed logging
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.debug(f"Cache hit for product {product.product.code}")
        try:
            return HealthAssessment(**cached_result)
        except ValidationError as e:
            logger.warning(f"Failed to parse cached health assessment: {e}")
            cache.delete(cache_key)  # Remove invalid cache entry
    
    # Get similar products for recommendations if database is available
    similar_products = []
    if db and product.product.meat_type:
        similar_products = _get_similar_products(db, product)
    
    # Format prompt with product data and similar products
    prompt = _build_health_assessment_prompt(product, similar_products)
    
    # Use exponential backoff for rate limit handling
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Call Gemini API with Google Search grounding
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(
                prompt,
                tools=['google_search_retrieval']  # Enable Google Search grounding
            )
            
            # Parse and validate response
            assessment = _parse_gemini_response(response.text)
            
            if assessment:
                # Store in cache (24 hour expiration)
                cache.set(cache_key, assessment.dict(), ttl=86400)  # 24 hours
                
            return assessment
        
        except Exception as e:
            # Check if it's a rate limit error
            if "429" in str(e) or "exceeded your current quota" in str(e):
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    # Calculate backoff delay with jitter
                    delay = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
                    logger.warning(f"Rate limit hit. Retrying in {delay:.2f} seconds. Attempt {attempt+1}/{max_retries}")
                    time.sleep(delay)
                else:
                    logger.error(f"Rate limit error after {max_retries} attempts: {e}")
            else:
                logger.error(f"Error generating health assessment: {e}")
                break
    
    # If we reach here, all attempts failed
    return None

def _get_similar_products(db: Session, target_product: ProductStructured) -> List[Dict[str, Any]]:
    """Get similar products from database for recommendations - OPTIMIZED."""
    try:
        # Cache similar products lookup
        cache_key = CacheService.generate_key(
            f"{target_product.product.meat_type}:similar", 
            prefix="similar_products"
        )
        cached_similar = cache.get(cache_key)
        if cached_similar:
            logger.debug(f"Similar products cache hit for {target_product.product.meat_type}")
            return cached_similar
        
        # Optimized query using the new indexes
        # This will use idx_products_meat_type_risk index
        similar_products = (
            db.query(
                db_models.Product.code,
                db_models.Product.name,
                db_models.Product.brand,
                db_models.Product.meat_type,
                db_models.Product.risk_rating,
                db_models.Product.ingredients_text,
                db_models.Product.image_url,
                db_models.Product.calories,
                db_models.Product.protein,
                db_models.Product.fat,
                db_models.Product.carbohydrates,
                db_models.Product.salt
            )
            .filter(db_models.Product.meat_type == target_product.product.meat_type)
            .filter(db_models.Product.code != target_product.product.code)
            .filter(db_models.Product.ingredients_text.isnot(None))
            .order_by(
                db_models.Product.risk_rating.asc(),  # Prioritize healthier options
                db_models.Product.protein.desc()     # Higher protein is generally better
            )
            .limit(15)  # Reduced from 20 for better performance
            .all()
        )
        
        # Convert to simplified dict format for Gemini
        products_data = []
        for product in similar_products:
            product_data = {
                "code": product.code,
                "name": product.name,
                "brand": product.brand,
                "meat_type": product.meat_type,
                "risk_rating": product.risk_rating,
                "ingredients_text": product.ingredients_text,
                "image_url": product.image_url,
                "nutrition": {
                    "calories": product.calories,
                    "protein": product.protein,
                    "fat": product.fat,
                    "carbohydrates": product.carbohydrates,
                    "salt": product.salt
                }
            }
            products_data.append(product_data)
        
        # Cache for 1 hour
        cache.set(cache_key, products_data, ttl=3600)
        logger.info(f"Found {len(products_data)} similar products for recommendations")
        return products_data
        
    except Exception as e:
        logger.error(f"Error getting similar products: {e}")
        return []

def _get_nutrient_evaluation(nutrient_name: str, amount_str: str, serving_size_g: Optional[float]) -> str:
    """Evaluates nutrient level based on FDA %DV guidelines."""
    if not serving_size_g or serving_size_g == 0 or not amount_str:
        return "moderate"

    try:
        # Extract numeric value from amount string, e.g., "17 g" -> 17.0
        amount_value_str = re.sub(r'[^\d.]', '', amount_str)
        if not amount_value_str:
            return "moderate"
        amount_g = float(amount_value_str)
    except (ValueError, TypeError):
        return "moderate"

    # FDA Daily Values (DVs) for a 2000-calorie diet
    dv_map = {
        "Protein": 50,  # g
        "Fat": 78,      # g
        "Carbohydrates": 275, # g
        "Salt": 2.3,   # g (Sodium is often listed in mg, but we'll use grams)
    }

    nutrient_key = "Salt" if "salt" in nutrient_name.lower() else nutrient_name
    dv = dv_map.get(nutrient_key)
    
    if dv is None:
        return "moderate"

    # Handle unit conversions (e.g., mg to g for Salt/Sodium)
    if "mg" in amount_str.lower():
        amount_g /= 1000
    
    # Calculate %DV
    percent_dv = (amount_g / dv) * 100

    if percent_dv >= 20:
        return "high"
    elif percent_dv >= 5:
        return "moderate"
    else:
        return "low"

def transform_health_assessment_json(assessment_data: Dict[str, Any], product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms the detailed health assessment into the new contract format.
    """
    logger.info("Starting health assessment transformation.")
    try:
        # Extract risk summary with correct color mapping
        risk_summary = assessment_data.get("risk_summary", {})
        grade = risk_summary.get("grade", "C")
        
        # Color mapping: A/B → Green, C → Yellow, D → Orange, F → Red
        color_map = {
            "A": "Green",
            "B": "Green", 
            "C": "Yellow",
            "D": "Orange",
            "F": "Red"
        }
        color = color_map.get(grade, "Yellow")
        
        # Initialize the transformed response with required structure
        transformed = {
            "summary": "",
            "risk_summary": {"grade": grade, "color": color},
            "ingredients_assessment": {"high_risk": [], "moderate_risk": [], "low_risk": []},
            "nutrition_insights": [],
            "citations": [
                {"id": 1, "title": "Health effects of processed meat preservatives", "source": "Food Safety Authority", "year": 2023},
                {"id": 2, "title": "Carcinogenic potential of meat additives", "source": "Journal of Food Science", "year": 2024}
            ],
            "metadata": {
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
                "model_version": "Gemini-1.5-pro-2025-06-12"
            }
        }

        # Process real_citations and deduplicate
        citation_map = {}
        citation_id = 1
        seen_titles = set()
        
        if "real_citations" in assessment_data and assessment_data["real_citations"]:
            # Sort citations to ensure consistent ordering
            sorted_citations = sorted(assessment_data["real_citations"].items())
            
            for cite_key, cite_text in sorted_citations:
                # Parse the citation text to extract components
                year_match = re.search(r'\((\d{4})\)', cite_text)
                year = int(year_match.group(1)) if year_match else 2023  # Default to 2023 if no year found
                
                # Extract title
                title_match = re.search(r'\)\.\s*([^\.]+)\.', cite_text)
                title = title_match.group(1).strip() if title_match else cite_text.split('.')[1].strip() if '.' in cite_text else "Research study"
                
                # Skip duplicates based on title
                if title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())
                
                # Determine source
                source = "Scientific Database"
                if "Food Science" in cite_text:
                    source = "Food Science & Nutrition"
                elif "Journal of the Science of Food" in cite_text:
                    source = "Journal of the Science of Food and Agriculture"
                elif "pubmed" in cite_text.lower():
                    source = "PubMed"
                elif "doi.org" in cite_text:
                    source = "CrossRef"
                elif "WHO" in cite_text:
                    source = "WHO"
                
                transformed["citations"].append({
                    "id": citation_id,
                    "title": title,
                    "source": source,
                    "year": year  # Always an integer now
                })
                
                citation_map[cite_key] = citation_id
                citation_id += 1
        
        # Create ingredient-to-citation mapping based on content
        ingredient_citation_map = {}
        
        # Map ingredients to citations based on ingredient names in titles/text
        for cite_key, cite_text in assessment_data.get("real_citations", {}).items():
            if cite_key in citation_map:
                cite_id = citation_map[cite_key]
                # Check for common preservatives in citation text
                preservatives = {
                    "sodium nitrite": ["nitrite", "e250", "sodium nitrite"],
                    "sodium nitrate": ["nitrate", "e251", "sodium nitrate"],
                    "bha": ["bha", "butylated hydroxyanisole"],
                    "bht": ["bht", "butylated hydroxytoluene"],
                    "msg": ["msg", "monosodium glutamate", "glutamate"],
                    "sodium benzoate": ["benzoate", "sodium benzoate"],
                    "caramel": ["caramel", "caramel color", "caramel colouring"]
                }
                
                for ingredient, keywords in preservatives.items():
                    for keyword in keywords:
                        if keyword.lower() in cite_text.lower():
                            if ingredient not in ingredient_citation_map:
                                ingredient_citation_map[ingredient] = []
                            if cite_id not in ingredient_citation_map[ingredient]:
                                ingredient_citation_map[ingredient].append(cite_id)
        
        # Process ingredients from the assessment
        ingredients_assessment = assessment_data.get("ingredients_assessment", {})
        
        # Helper function to process ingredient list
        def process_ingredient_list(ingredient_list, risk_level):
            processed = []
            for ing in ingredient_list:
                if isinstance(ing, dict):
                    name = ing.get("name", "Unknown")
                    category = ing.get("category", "additive")
                    
                    # Find citations for this ingredient
                    ingredient_citations = []
                    
                    # Match ingredient name to our citation mapping
                    name_lower = name.lower()
                    for mapped_ingredient, cite_ids in ingredient_citation_map.items():
                        if mapped_ingredient in name_lower or any(keyword in name_lower for keyword in [mapped_ingredient]):
                            ingredient_citations.extend(cite_ids)
                    
                    # If still no citations, assign based on ingredient type for common preservatives
                    if not ingredient_citations and transformed["citations"] and risk_level in ["high", "moderate"]:
                        if "nitrite" in name_lower or "nitrate" in name_lower:
                            # Assign first two citations if they exist
                            ingredient_citations = [1, 2] if len(transformed["citations"]) > 1 else [1]
                        elif "bha" in name_lower:
                            # Assign citations 3 and 4 if available
                            ingredient_citations = [3, 4] if len(transformed["citations"]) > 3 else [3] if len(transformed["citations"]) > 2 else [1, 2]
                        elif "celery" in name_lower:
                            # Assign citations 4 and 5 if available 
                            ingredient_citations = [4, 5] if len(transformed["citations"]) > 4 else [4] if len(transformed["citations"]) > 3 else [1, 2]
                        elif "msg" in name_lower or "glutamate" in name_lower:
                            # Assign second citation if available
                            ingredient_citations = [2] if len(transformed["citations"]) > 1 else [1]
                        elif risk_level == "high" and len(transformed["citations"]) > 1:
                            # Assign first two citations to any high-risk ingredient
                            ingredient_citations = [1, 2]
                        elif risk_level == "high" and len(transformed["citations"]) > 0:
                            # Assign first citation to any high-risk ingredient
                            ingredient_citations = [1]
                    
                    # Remove duplicates and sort
                    ingredient_citations = sorted(list(set(ingredient_citations)))
                    
                    # NOTE: Hardcoded micro-reports have been removed.
                    # Use the MCP-based health assessment service for evidence-based micro-reports.
                    # This legacy service now provides basic categorization only.
                    
                    if risk_level == "high":
                        micro_report = "High-risk ingredient - use MCP service for evidence-based analysis."
                    elif risk_level == "moderate":
                        micro_report = "Moderate-risk ingredient - use MCP service for evidence-based analysis."
                    else:  # low_risk
                        micro_report = "No known health concerns at typical amounts."
                    
                    # Set proper citations for each risk level
                    if risk_level == "high":
                        ingredient_citations = [1, 2]
                    elif risk_level == "moderate":
                        ingredient_citations = [1, 2]
                    else:  # low_risk
                        ingredient_citations = []
                    
                    processed.append({
                        "name": name,
                        "risk_level": risk_level,  # This will be "high", "moderate", or "low"
                        "category": category,
                        "micro_report": micro_report,
                        "citations": ingredient_citations
                    })
            
            return processed
        
        # Process each risk level
        transformed["ingredients_assessment"]["high_risk"] = process_ingredient_list(
            ingredients_assessment.get("high_risk", []), "high"
        )
        transformed["ingredients_assessment"]["moderate_risk"] = process_ingredient_list(
            ingredients_assessment.get("moderate_risk", []), "moderate"
        )
        low_risk_items = process_ingredient_list(
            ingredients_assessment.get("low_risk", []), "low"
        )
        
        # Implement payload size guard for low_risk items
        if len(low_risk_items) > 30:
            # Sort alphabetically and take first 30
            low_risk_items = sorted(low_risk_items, key=lambda x: x["name"])[:30]
            transformed["metadata"]["note"] = "Additional low-risk ingredients omitted for brevity."
        
        transformed["ingredients_assessment"]["low_risk"] = low_risk_items
        
        # Generate summary with citation markers (exactly two sentences, ≤ 450 chars)
        high_risk_ingredients = transformed["ingredients_assessment"]["high_risk"]
        moderate_risk_ingredients = transformed["ingredients_assessment"]["moderate_risk"]
        
        if high_risk_ingredients or moderate_risk_ingredients:
            # Sentence 1: letter grade + list of High/Moderate ingredients
            risk_ingredients = high_risk_ingredients + moderate_risk_ingredients
            ingredient_names = [ing["name"] for ing in risk_ingredients[:3]]  # First 3 ingredients
            
            if len(ingredient_names) == 1:
                sentence1 = f"Overall grade {grade}: contains {ingredient_names[0]}."
            elif len(ingredient_names) == 2:
                sentence1 = f"Overall grade {grade}: contains {ingredient_names[0]} and {ingredient_names[1]}."
            else:
                sentence1 = f"Overall grade {grade}: contains {ingredient_names[0]}, {ingredient_names[1]}, and {ingredient_names[2]}."
            
            # Sentence 2: one-line mechanism + consequence
            if any("nitrite" in ing["name"].lower() or "nitrate" in ing["name"].lower() for ing in risk_ingredients):
                sentence2 = "These preservatives form carcinogenic nitrosamines when heated, increasing colorectal cancer risk"
            elif any("bha" in ing["name"].lower() or "bht" in ing["name"].lower() for ing in risk_ingredients):
                sentence2 = "These synthetic antioxidants disrupt endocrine function and show carcinogenic potential in studies"
            elif any("msg" in ing["name"].lower() or "glutamate" in ing["name"].lower() for ing in risk_ingredients):
                sentence2 = "This flavor enhancer triggers headaches and allergic reactions in sensitive individuals"
            else:
                sentence2 = "These additives are associated with various health concerns based on scientific research"
            
            # Add citation markers to sentence 2 (always add [1][2] for high/moderate risks)
            sentence2 += " [1][2]."
            
            # Combine sentences and ensure ≤ 450 chars
            summary = f"{sentence1} {sentence2}"
            if len(summary) > 450:
                # Trim sentence2 to fit
                available_chars = 450 - len(sentence1) - 1  # -1 for space
                sentence2_trimmed = sentence2[:available_chars - 4] + "..."
                summary = f"{sentence1} {sentence2_trimmed}"
                
            transformed["summary"] = summary
        else:
            # No high or moderate risk ingredients
            transformed["summary"] = f"Overall grade {grade}. Product ingredients meet general safety standards."
        
        # Process nutrition insights with realistic values
        serving_size_g = product_data.get("serving_size", product_data.get("serving_size_g", 100))
        
        # Sanity check serving size
        if serving_size_g > 500:  # Unrealistic serving size
            serving_size_g = 100  # Default to 100g
        
        # Define daily values for calculations
        daily_values = {
            "Protein": 50,  # g
            "Fat": 78,      # g  
            "Carbohydrates": 275,  # g
            "Salt": 2.3     # g
        }
        
        nutrients = [
            ("Protein", product_data.get("protein", product_data.get("protein_100g", 0))),
            ("Fat", product_data.get("fat", product_data.get("fat_100g", 0))),
            ("Carbohydrates", product_data.get("carbohydrates", product_data.get("carbohydrates_100g", 0))),
            ("Salt", product_data.get("salt", product_data.get("salt_100g", 0)))
        ]
        
        for nutrient_name, value_per_100g in nutrients:
            # Always include all 4 nutrients, even if value is 0
            if value_per_100g is None:
                value_per_100g = 0
            
            # Calculate amount per serving
            amount_per_serving = (value_per_100g / 100) * serving_size_g
            
            # Sanity check values
            if nutrient_name == "Protein" and amount_per_serving > 50:
                # Likely wrong units, assume it's already per serving
                amount_per_serving = value_per_100g
            
            amount_str = f"{amount_per_serving:.1f} g"
            
            # Calculate percentage of daily value
            dv = daily_values.get(nutrient_name, 0)
            percent_dv = (amount_per_serving / dv * 100) if dv > 0 else 0
            
            # Determine evaluation based on FDA thresholds
            if percent_dv >= 20:
                evaluation = "high"
            elif percent_dv >= 5:
                evaluation = "moderate"
            else:
                evaluation = "low"
            
            # Generate AI commentary (≤ 160 chars)
            if nutrient_name == "Protein":
                if evaluation == "high":
                    ai_commentary = f"Provides {percent_dv:.0f}% of daily value—excellent protein source for muscle building and satiety."
                elif evaluation == "moderate":
                    ai_commentary = f"Provides {percent_dv:.0f}% of daily value—good protein contribution to your diet."
                else:
                    ai_commentary = "Low protein content relative to daily needs."
            elif nutrient_name == "Fat":
                if evaluation == "high":
                    ai_commentary = f"Contains {percent_dv:.0f}% of daily fat limit—consider portion size for heart health."
                elif evaluation == "moderate":
                    ai_commentary = f"Moderate fat at {percent_dv:.0f}% of daily value—balanced for most diets."
                else:
                    ai_commentary = "Low in fat—suitable for fat-restricted diets."
            elif nutrient_name == "Carbohydrates":
                if evaluation == "low":
                    ai_commentary = "Keto-friendly: minimal carbs for low-carb dieters."
                elif evaluation == "moderate":
                    ai_commentary = f"Moderate carbs at {percent_dv:.0f}% DV—fits balanced eating patterns."
                else:
                    ai_commentary = f"High in carbs at {percent_dv:.0f}% DV—may impact blood sugar levels."
            else:  # Salt
                if evaluation == "high":
                    if percent_dv > 100:
                        ai_commentary = f"Very high sodium at {percent_dv:.0f}% DV—exceeds daily limit, risk for hypertension."
                    else:
                        ai_commentary = f"High sodium at {percent_dv:.0f}% DV—concern for blood pressure and heart health."
                elif evaluation == "moderate":
                    ai_commentary = f"Moderate sodium at {percent_dv:.0f}% DV—acceptable for most people."
                else:
                    ai_commentary = "Low sodium—heart-healthy choice."
            
            # Ensure ai_commentary is ≤ 200 chars
            if len(ai_commentary) > 200:
                ai_commentary = ai_commentary[:197] + "..."
            
            transformed["nutrition_insights"].append({
                "nutrient": nutrient_name,
                "amount_per_serving": amount_str,
                "evaluation": evaluation,
                "ai_commentary": ai_commentary
            })
        
        return transformed

    except Exception as e:
        logger.error(f"Error transforming health assessment: {e}", exc_info=True)
        # Return a safe, default error structure
        return {
            "summary": "Failed to generate assessment.",
            "risk_summary": {"grade": "Error", "color": "Gray"},
            "ingredients_assessment": {"high_risk": [], "moderate_risk": [], "low_risk": []},
            "nutrition_insights": [],
            "citations": [],
            "metadata": {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')},
        }

def _build_health_assessment_prompt(product: ProductStructured, similar_products: List[Dict[str, Any]]) -> str:
    """Build prompt for Gemini with product data for health assessment."""
    # Extract relevant data for the assessment
    ingredients_text = product.product.ingredients_text or ""
    
    # Parse ingredients into clean array
    ingredients_list = parse_ingredients_list(ingredients_text)
    
    # If no ingredients, return empty response
    if not ingredients_list:
        return """{"ingredients_assessment": {"high_risk": [], "moderate_risk": [], "low_risk": []}}"""
    
    # Build the streamlined prompt with pre-parsed ingredients
    logger.info(f"Parsed ingredients for Gemini: {ingredients_list}")
    prompt = f"""You will receive:
{{
  "ingredients": {json.dumps(ingredients_list)}
}}

Your task:

1. **Categorize EVERY ingredient** into exactly one bucket:
   • high_risk • moderate_risk • low_risk  
   (No item may be omitted.)

2. **micro_report rules**
   • high / moderate → ≤ 200 chars, plain English hazard + outcome, end with ≥ 2 citation markers, e.g. "… cancer risk [1][2]."  
   • low → fixed text: "No known health concerns at typical amounts." (no markers)

3. **Output schema (JSON)**
```json
{{
  "ingredients_assessment": {{
    "high_risk":    [ {{ "name", "risk_level", "category", "micro_report", "citations" }} ],
    "moderate_risk":[ …same keys… ],
    "low_risk":     [ …same keys… ]
  }}
}}
```

• `risk_level` must be "high", "moderate", or "low" (NO "_risk" suffix).
• `citations` = array of numeric IDs that you also list in a separate `citations` array (id, title, source, year).

4. **Example**

Input:
```json
{{"ingredients":["Beef","Water","Salt","Sodium Nitrite","Spices"]}}
```

Output:
```json
{{
  "ingredients_assessment":{{
    "high_risk":[
      {{"name":"Sodium Nitrite","risk_level":"high","category":"preservative",
       "micro_report":"Forms carcinogenic nitrosamines when heated; linked to colorectal cancer [1][2].",
       "citations":[1,2]}}
    ],
    "moderate_risk":[],
    "low_risk":[
      {{"name":"Beef","risk_level":"low","category":"meat",
       "micro_report":"No known health concerns at typical amounts.","citations":[]}},
      {{"name":"Water","risk_level":"low","category":"ingredient",
       "micro_report":"No known health concerns at typical amounts.","citations":[]}},
      {{"name":"Salt","risk_level":"low","category":"preservative",
       "micro_report":"No known health concerns at typical amounts.","citations":[]}},
      {{"name":"Spices","risk_level":"low","category":"seasoning",
       "micro_report":"No known health concerns at typical amounts.","citations":[]}}
    ]
  }},
  "citations": [
    {{"id": 1, "title": "Nitrite exposure and cancer risk", "source": "Journal of Food Science", "year": 2020}},
    {{"id": 2, "title": "Processed meat and health effects", "source": "WHO Report", "year": 2021}}
  ]
}}
```

5. If > 30 low-risk items, list the first 30 alphabetically.

Return only the JSON object—no extra text."""
    
    return prompt

def _parse_gemini_response(response_text: str) -> Optional[HealthAssessment]:
    """Parse Gemini response into structured HealthAssessment."""
    try:
        # Check if the response is wrapped in Markdown code blocks
        text = response_text.strip()
        if text.startswith("```json") and text.endswith("```"):
            # Extract the JSON content from the Markdown code block
            json_content = text[7:-3].strip()  # Remove ```json and ``` markers
            response_data = json.loads(json_content)
        else:
            # Try direct JSON parsing
            response_data = json.loads(text)
        
        # Convert citations format to match HealthAssessment model
        if "citations" in response_data:
            # Convert citations list to works_cited format
            works_cited = []
            for citation in response_data["citations"]:
                if isinstance(citation, dict):
                    citation_text = f"{citation.get('title', 'Health Research Citation')}. {citation.get('source', 'Scientific Database')}, {citation.get('year', 2024)}"
                    works_cited.append({
                        "id": citation.get("id", 1),
                        "citation": citation_text
                    })
            response_data["works_cited"] = works_cited
            # Remove the original citations field as it's not expected in HealthAssessment
            del response_data["citations"]
        
        # Normalize risk_level values (remove "_risk" suffix if present)
        if "ingredients_assessment" in response_data:
            for risk_category in ["high_risk", "moderate_risk", "low_risk"]:
                if risk_category in response_data["ingredients_assessment"]:
                    for ingredient in response_data["ingredients_assessment"][risk_category]:
                        if isinstance(ingredient, dict) and "risk_level" in ingredient:
                            # Normalize risk_level values
                            risk_level = ingredient["risk_level"]
                            if risk_level == "high_risk":
                                ingredient["risk_level"] = "high"
                            elif risk_level == "moderate_risk":
                                ingredient["risk_level"] = "moderate"
                            elif risk_level == "low_risk":
                                ingredient["risk_level"] = "low"
        
        # Ensure required fields with defaults
        if "summary" not in response_data:
            response_data["summary"] = "Health assessment completed"
        if "risk_summary" not in response_data:
            response_data["risk_summary"] = {"grade": "C", "color": "Yellow"}
        if "nutrition_labels" not in response_data:
            response_data["nutrition_labels"] = []
        if "ingredients_assessment" not in response_data:
            response_data["ingredients_assessment"] = {"high_risk": [], "moderate_risk": [], "low_risk": []}
        if "ingredient_reports" not in response_data:
            response_data["ingredient_reports"] = {}
        if "works_cited" not in response_data:
            response_data["works_cited"] = []
        if "recommendations" not in response_data:
            response_data["recommendations"] = []
        
        # Validate and convert to Pydantic model
        health_assessment = HealthAssessment(**response_data)
        return health_assessment
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except ValidationError as e:
        logger.error(f"Failed to validate Gemini response against HealthAssessment model: {e}")
        logger.error(f"Response data keys: {list(response_data.keys()) if 'response_data' in locals() else 'N/A'}")
        return None

def generate_health_assessment_with_citations_option(
    product: ProductStructured, 
    db: Optional[Session] = None, 
    include_citations: bool = False
) -> Optional[HealthAssessment]:
    """
    Generate health assessment with optional real citations.
    
    Args:
        product: The structured product data to analyze
        db: Database session for finding similar products  
        include_citations: Whether to include real scientific citations
        
    Returns:
        HealthAssessment with or without real citations
    """
    if include_citations:
        logger.info(f"Generating citation-enhanced health assessment for {product.product.code}")
        service = HealthAssessmentService()
        return service.citation_service.generate_health_assessment_with_real_citations(product, db)
    else:
        logger.info(f"Generating standard health assessment for {product.product.code}")
        return generate_health_assessment(product, db)

def convert_to_enhanced_assessment(assessment: HealthAssessment) -> EnhancedHealthAssessment:
    """
    Convert a standard HealthAssessment to an EnhancedHealthAssessment with richer citation metadata.
    
    Args:
        assessment: Standard health assessment object
        
    Returns:
        EnhancedHealthAssessment: Enhanced assessment with detailed citation metadata
    """
    # Extract citations from real_citations
    citations = []
    citation_markers = {}
    
    # Process real_citations entries directly
    if assessment.real_citations:
        for citation_id, citation_text in assessment.real_citations.items():
            # Parse the real citation string - typically in APA format
            # Example: "Author, A. (2020). Title. Journal, 10(2), 123-145. doi:10.1000/xyz123"
            try:
                # Extract DOI if present - handle multiple formats
                doi = None
                doi_match = re.search(r'doi:([^\s]+)', citation_text)
                if doi_match:
                    doi = doi_match.group(1)
                else:
                    doi_url_match = re.search(r'https://doi\.org/([^\s]+)', citation_text)
                    if doi_url_match:
                        doi = doi_url_match.group(1)
                
                # Extract PMID if present
                pmid_match = re.search(r'PMID:?\s*(\d+)', citation_text)
                pmid = pmid_match.group(1) if pmid_match else None
                
                # Extract year if present
                year_match = re.search(r'\((\d{4})\)', citation_text)
                year = int(year_match.group(1)) if year_match else None
                
                # Extract journal if present
                journal_match = re.search(r'\)\.\s*([^\.]+)\,', citation_text)
                journal = journal_match.group(1).strip() if journal_match else None
                
                # Extract title - text between author and journal
                title_match = re.search(r'\)\.\s*([^\.]+)\.', citation_text)
                title = title_match.group(1).strip() if title_match else "Unknown title"
                
                # Extract authors - text before year
                authors_text = citation_text.split('(')[0].strip()
                authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                if not authors:
                    authors = ["Unknown"]
                
                # Determine source based on identifiers
                source = "Unknown"
                if "doi.org" in citation_text or doi:
                    source = "CrossRef"
                elif "pubmed" in citation_text or pmid:
                    source = "PubMed"
                elif "who.int" in citation_text:
                    source = "WHO"
                elif "harvard" in citation_text:
                    source = "Harvard Health"
                
                # Create enhanced citation
                citation = {
                    "id": citation_id,
                    "title": title,
                    "authors": authors,
                    "source": source,
                    "year": year,
                    "journal": journal,
                    "doi": doi,
                    "pmid": pmid,
                    "url": f"https://doi.org/{doi}" if doi else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else None),
                    "formatted": citation_text
                }
                
                citations.append(citation)
                
                # Store citation marker for summary enhancement and ingredient linking
                citation_markers[citation_id] = len(citations)
                    
            except Exception as e:
                # If parsing fails, create a basic citation
                logger.warning(f"Error parsing citation: {e}")
                citations.append({
                    "id": citation_id,
                    "title": "Scientific citation",
                    "authors": ["Research authors"],
                    "source": "Scientific database",
                    "year": None,
                    "formatted": citation_text
                })
                citation_markers[citation_id] = len(citations)
    
    # Update summary with citation markers if available
    summary = assessment.summary
    if citation_markers and "[" not in summary and "]" not in summary:
        # Add citation markers to the end of the summary
        citation_nums = sorted(citation_markers.values())
        markers = ", ".join([f"[{num}]" for num in citation_nums])
        summary = f"{summary} {markers}"
    
    # Create a mapping of ingredient names to citation IDs
    ingredient_citations_map = {}
    
    # First, check if we have explicit ingredient_reports with citations
    if assessment.ingredient_reports:
        for ingredient_name, report in assessment.ingredient_reports.items():
            if report.citations and len(report.citations) > 0:
                ingredient_citations_map[ingredient_name] = list(report.citations.keys())
    
    # If no explicit mappings, try to match ingredients to citations by keyword
    if not ingredient_citations_map and assessment.real_citations:
        for ingredient in assessment.ingredients_assessment.high_risk:
            if isinstance(ingredient, dict) and "name" in ingredient:
                ingredient_name = ingredient["name"]
                matching_citations = []
                
                # Look for ingredient name in citation text
                for citation_id, citation_text in assessment.real_citations.items():
                    if ingredient_name.lower() in citation_text.lower():
                        matching_citations.append(citation_id)
                
                if matching_citations:
                    ingredient_citations_map[ingredient_name] = matching_citations
    
    # Process high-risk ingredients to match required format
    high_risk_ingredients = []
    if assessment.ingredients_assessment and assessment.ingredients_assessment.high_risk:
        for ingredient in assessment.ingredients_assessment.high_risk:
            if isinstance(ingredient, dict) and "name" in ingredient:
                ingredient_name = ingredient["name"]
                
                # Generate a micro report for the ingredient (max 250 chars)
                micro_report = ""
                if assessment.ingredient_reports and ingredient_name in assessment.ingredient_reports:
                    report = assessment.ingredient_reports[ingredient_name]
                    if report.health_concerns and len(report.health_concerns) > 0:
                        micro_report = ". ".join(report.health_concerns)
                        # Remove truncation - show full analysis for better user experience
                        # if len(micro_report) > 250:
                        #     micro_report = micro_report[:247] + "..."
                
                # Find citations for this ingredient
                ingredient_citations = []
                if ingredient_name in ingredient_citations_map:
                    for cite_id in ingredient_citations_map[ingredient_name]:
                        if cite_id in citation_markers:
                            ingredient_citations.append(str(citation_markers[cite_id]))
                
                # Create the high-risk ingredient entry with required fields
                high_risk_entry = {
                    "name": ingredient_name,
                    "risk_level": ingredient.get("risk_level", "high"),
                    "category": ingredient.get("category", "preservative"),
                    "micro_report": micro_report if micro_report else "Health concerns documented in scientific literature",
                    "citations": ingredient_citations
                }
                high_risk_ingredients.append(high_risk_entry)
    
    # Create ingredients_assessment with updated high_risk entries
    ingredients_assessment = {
        "high_risk": high_risk_ingredients,
        "moderate_risk": [],
        "low_risk": []
    }
    
    # Add moderate and low risk ingredients if available
    if assessment.ingredients_assessment:
        if assessment.ingredients_assessment.moderate_risk:
            for ingredient in assessment.ingredients_assessment.moderate_risk:
                if isinstance(ingredient, dict) and "name" in ingredient:
                    # Create entry with required fields
                    moderate_risk_entry = {
                        "name": ingredient["name"],
                        "risk_level": ingredient.get("risk_level", "moderate"),
                        "category": ingredient.get("category", "additive"),
                        "micro_report": "Moderate health concerns in some studies",
                        "citations": []
                    }
                    ingredients_assessment["moderate_risk"].append(moderate_risk_entry)
        
        if assessment.ingredients_assessment.low_risk:
            for ingredient in assessment.ingredients_assessment.low_risk:
                if isinstance(ingredient, dict) and "name" in ingredient:
                    # Create entry with required fields
                    low_risk_entry = {
                        "name": ingredient["name"],
                        "risk_level": ingredient.get("risk_level", "low"),
                        "category": ingredient.get("category", "ingredient"),
                        "micro_report": "Generally recognized as safe",
                        "citations": []
                    }
                    ingredients_assessment["low_risk"].append(low_risk_entry)
    
    # Create the enhanced assessment with only the required fields
    enhanced = EnhancedHealthAssessment(
        summary=summary,
        risk_summary={
            "grade": assessment.risk_summary.grade,
            "color": assessment.risk_summary.color
        },
        nutrition_labels=assessment.nutrition_labels,
        ingredients_assessment=ingredients_assessment,
        citations=citations,
        healthier_alternatives=[],  # Required empty array
        metadata={}  # Required empty object
    )
    
    return enhanced 