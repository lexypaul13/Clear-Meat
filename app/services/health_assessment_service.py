"""Health assessment service using Gemini for product analysis."""
import json
import logging
import time
import random
import hashlib
from typing import Dict, Any, Optional

import google.generativeai as genai
from pydantic import ValidationError

from app.core.config import settings
from app.models.product import HealthAssessment, ProductStructured

logger = logging.getLogger(__name__)

# Simple in-memory cache for health assessments
# Structure: {product_code: {"data": assessment_data, "expires_at": timestamp}}
_health_assessment_cache = {}

def generate_health_assessment(product: ProductStructured) -> Optional[HealthAssessment]:
    """
    Generate a detailed health assessment for a product using Gemini.
    
    Args:
        product: The structured product data to analyze
        
    Returns:
        HealthAssessment: The AI-generated health assessment or None if generation failed
    """
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return None
    
    # Generate cache key based on product code and data
    cache_key = product.product.code
    
    # Check cache first
    cached_result = _get_from_cache(cache_key)
    if cached_result:
        logger.info(f"Returning cached health assessment for product {cache_key}")
        return cached_result
    
    # Format prompt with product data
    prompt = _build_health_assessment_prompt(product)
    
    # Use exponential backoff for rate limit handling
    max_retries = 3
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Call Gemini API
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(prompt)
            
            # Parse and validate response
            assessment = _parse_gemini_response(response.text)
            
            if assessment:
                # Store in cache (24 hour expiration)
                _store_in_cache(cache_key, assessment, 86400)  # 24 hours in seconds
                
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

def _store_in_cache(key: str, data: HealthAssessment, ttl: int) -> None:
    """Store health assessment in cache with expiration."""
    _health_assessment_cache[key] = {
        "data": data,
        "expires_at": time.time() + ttl
    }
    logger.debug(f"Stored health assessment in cache with key {key}, expires in {ttl}s")
    
    # Clean up expired entries occasionally
    if random.random() < 0.1:  # ~10% chance on each call
        _clean_expired_cache()

def _get_from_cache(key: str) -> Optional[HealthAssessment]:
    """Get health assessment from cache if not expired."""
    if key not in _health_assessment_cache:
        return None
        
    cache_entry = _health_assessment_cache[key]
    if time.time() > cache_entry["expires_at"]:
        # Expired
        del _health_assessment_cache[key]
        return None
        
    return cache_entry["data"]

def _clean_expired_cache() -> None:
    """Remove expired entries from cache."""
    now = time.time()
    expired_keys = [
        k for k, v in _health_assessment_cache.items() 
        if now > v["expires_at"]
    ]
    for k in expired_keys:
        del _health_assessment_cache[k]
    
    if expired_keys:
        logger.debug(f"Cleaned {len(expired_keys)} expired health assessment cache entries")

def _build_health_assessment_prompt(product: ProductStructured) -> str:
    """Build prompt for Gemini with product data for health assessment."""
    # Extract relevant data for the assessment
    ingredients_text = product.product.ingredients_text or "Ingredients not available"
    
    # Extract nutrition data
    nutrition = {}
    if product.health and product.health.nutrition:
        nutrition = {
            "calories": product.health.nutrition.calories,
            "protein": product.health.nutrition.protein,
            "fat": product.health.nutrition.fat,
            "carbohydrates": product.health.nutrition.carbohydrates,
            "salt": product.health.nutrition.salt
        }
    
    # Get risk rating if available
    risk_rating = None
    if product.criteria and product.criteria.risk_rating:
        risk_rating = product.criteria.risk_rating
    
    # Build product data section
    product_data = {
        "product_name": product.product.name,
        "brand": product.product.brand,
        "ingredients_text": ingredients_text,
        "nutrition": nutrition,
        "risk_rating": risk_rating
    }
    
    # Use the new comprehensive prompt template
    prompt = f"""You are an AI assistant specialized in generating health-assessment reports for consumer food products. When provided with a JSON payload describing a product's ingredient list and nutritional facts, follow the steps below to produce a compact, UI-ready health summary.

Your Tasks:

Analyze each ingredient and assign it to one of three risk categories—high_risk, moderate_risk, or low_risk—based on potential health concerns (e.g., allergenicity, toxicity, processing, regulatory limits).

Exclude ingredients from the low_risk group if they have:

No health risks or concerns

Generic or empty descriptions like "None identified"

Do not include alternatives[] in the ingredients_assessment block. Safer alternatives should only appear in detailed ingredient reports.

Generate a 2–3 sentence plain-language summary of the product's overall health profile, including standout ingredients or concerns.

Create a nutrition_labels array based on the nutrition values provided, with AI-generated plain terms like:

"High Fat"

"Moderate Carbohydrates"

"Low Sodium"

For every ingredient in high_risk and moderate_risk, return an entry in the ingredient_reports section that includes:

title: ingredient name + category

summary: short explanation of what it is and why it matters

health_concerns: bulleted list of concerns with in-text citation markers (e.g., "[1]")

common_uses: where it's commonly used

safer_alternatives: optional list of better ingredient swaps

citations: citation dictionary with keys matching in-text markers

Append a works_cited array listing all references used, formatted in APA style and linked where possible.

User Input

{json.dumps(product_data, indent=2)}

Expected Output (as machine-readable JSON only)

{{
  "summary": "This product contains multiple processed ingredients...",
  "risk_summary": {{
    "grade": "C",
    "color": "Yellow"
  }},
  "nutrition_labels": [
    "High Fat",
    "Low Sodium"
  ],
  "ingredients_assessment": {{
    "high_risk": [
      {{
        "name": "Ingredient A",
        "risk_level": "high",
        "category": "preservative",
        "concerns": "May cause X or Y"
      }}
    ],
    "moderate_risk": [
      {{
        "name": "Ingredient B",
        "risk_level": "moderate",
        "category": "coloring",
        "concerns": "Linked to sensitivity in some individuals"
      }}
    ],
    "low_risk": [
      {{
        "name": "Ingredient C",
        "risk_level": "low",
        "category": "vegetable",
        "concerns": "Minimal health concerns"
      }}
    ]
  }},
  "ingredient_reports": {{
    "Ingredient A": {{
      "title": "Ingredient A – Preservative",
      "summary": "Ingredient A is a synthetic preservative used to extend shelf life...",
      "health_concerns": [
        "Linked to kidney strain in sensitive populations [1]"
      ],
      "common_uses": "Found in canned meats, processed sauces, and frozen meals.",
      "safer_alternatives": [
        "Natural preservatives like vinegar or lemon juice"
      ],
      "citations": {{
        "1": "FDA. (2022). Food Additive Safety. https://fda.gov/..."
      }}
    }}
  }},
  "works_cited": [
    {{
      "id": 1,
      "citation": "U.S. Food and Drug Administration. (2022). Food Additive Safety. Retrieved from https://fda.gov/..."
    }}
  ]
}}

Approved Sources:

Government & International Health Agencies

U.S. Food and Drug Administration (FDA) – fda.gov

World Health Organization (WHO) – who.int

Centers for Disease Control and Prevention (CDC) – cdc.gov

USDA FoodData Central – fdc.nal.usda.gov

Nutrition.gov – nutrition.gov

Academic & Research Institutions

Harvard T.H. Chan School of Public Health – nutritionsource.hsph.harvard.edu

National Institutes of Health (NIH) – nih.gov

Examine.com – examine.com

Professional & Advocacy Organizations

Academy of Nutrition and Dietetics – eatright.org

Environmental Working Group (EWG) – ewg.org

Center for Science in the Public Interest (CSPI) – cspinet.org

You must ignore information from any other source.

Respond with valid JSON only."""
    
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
        
        # Validate and convert to Pydantic model
        health_assessment = HealthAssessment(**response_data)
        return health_assessment
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except ValidationError as e:
        logger.error(f"Failed to validate Gemini response against HealthAssessment model: {e}")
        return None 