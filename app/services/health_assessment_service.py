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
    
    # Build instructions section
    instructions = """## Instructions:

You are a nutritional and health scientist specialized in food safety and ingredient analysis. Your task is to analyze the provided meat product and generate a comprehensive health assessment.

1. Carefully analyze the ingredients list and nutritional information
2. Identify all food additives, preservatives, and potentially concerning ingredients
3. Classify each identified ingredient into high_risk, moderate_risk, or low_risk categories
4. Provide plain language nutrition labels based on the nutritional values
5. For each concerning ingredient, create a detailed mini health report
6. Assign an overall health grade (A-F) and color (Green, Yellow, Red) based on your analysis
7. Cite reputable sources for your claims where possible
8. Format your response as structured JSON only (no explanatory text)"""

    # Build response format section
    response_format = """## Response Format (JSON):
{
  "risk_summary": {
    "grade": "B",
    "color": "Yellow"
  },
  "nutrition_labels": [
    "High fat",
    "Moderate carbohydrates",
    "Low sodium"
  ],
  "ingredients_assessment": {
    "high_risk": [
      {
        "name": "Sodium Nitrite",
        "risk_level": "high",
        "category": "preservative",
        "concerns": "Potential carcinogen when heated",
        "alternatives": ["Celery powder", "Cherry powder"]
      }
    ],
    "moderate_risk": [],
    "low_risk": []
  },
  "ingredient_reports": {
    "Sodium Nitrite": {
      "title": "Sodium Nitrite (E250) – Preservative",
      "summary": "Sodium nitrite is a preservative used to prevent bacterial growth in processed meats. While effective for food safety, it has been associated with health concerns when consumed in large amounts or when heated to high temperatures.",
      "health_concerns": [
        "May form nitrosamines (potential carcinogens) when heated [1]",
        "Associated with increased risk of colorectal cancer in high consumption [2]"
      ],
      "common_uses": "Found in bacon, ham, hot dogs, and other cured meats",
      "safer_alternatives": [
        "Celery powder (natural nitrate source)",
        "Vitamin C (reduces nitrosamine formation)"
      ],
      "citations": {
        "1": "World Health Organization, IARC Monographs",
        "2": "American Journal of Clinical Nutrition, 2009"
      }
    }
  }
}

Respond with valid JSON only."""
    
    # Combine all sections
    prompt = f"""You are an expert nutritionist and food scientist specializing in meat products. Your task is to analyze the provided product information and generate a detailed health assessment report.

## Product Information
{json.dumps(product_data, indent=2)}

{instructions}

{response_format}"""
    
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