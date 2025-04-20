"""Gemini service for personalized recommendations."""
import google.generativeai as genai
from typing import Dict, List, Any, Optional
import json
import logging
import time
import random
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini client
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")

# Simple in-memory cache to reduce API calls
# Structure: {cache_key: {"data": response_data, "expires_at": timestamp}}
_recommendations_cache = {}

def get_personalized_recommendations(user_preferences, available_products, recent_scans=None):
    """Generate personalized product recommendations using Gemini."""
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return {"sections": []}
    
    # Generate cache key based on input data
    cache_key = _generate_cache_key(user_preferences, available_products, recent_scans)
    
    # Check cache first
    cached_result = _get_from_cache(cache_key)
    if cached_result:
        logger.info("Returning cached recommendations")
        return cached_result
    
    # Format prompt with user context and products
    prompt = _build_recommendation_prompt(user_preferences, available_products, recent_scans)
    
    # Use exponential backoff for rate limit handling
    max_retries = 3
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Call Gemini API
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(prompt)
            
            # Parse and validate response
            recommendations = _parse_gemini_response(response.text)
            
            # Store in cache (1 hour expiration)
            _store_in_cache(cache_key, recommendations, 3600)
            
            return recommendations
        
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
                logger.error(f"Error generating recommendations: {e}")
                break
    
    # If we reach here, all attempts failed
    return {"sections": []}

def _generate_cache_key(user_preferences, available_products, recent_scans) -> str:
    """Generate a cache key based on input parameters."""
    # Use only fields that affect recommendations
    key_data = {
        "preferences": user_preferences,
        # Use only relevant product fields, not full objects
        "product_codes": [p.get("code") for p in available_products[:10]] if available_products else []
    }
    # Add a hash of the first few recent scans if available
    if recent_scans:
        key_data["recent_scans"] = [s.get("product_code") for s in recent_scans[:3]] if recent_scans else []
    
    # Create a string hash
    return str(hash(json.dumps(key_data, sort_keys=True)))

def _store_in_cache(key: str, data: Dict, ttl: int) -> None:
    """Store data in cache with expiration."""
    _recommendations_cache[key] = {
        "data": data,
        "expires_at": time.time() + ttl
    }
    logger.debug(f"Stored in cache with key {key}, expires in {ttl}s")
    
    # Clean up expired entries occasionally
    if random.random() < 0.1:  # ~10% chance on each call
        _clean_expired_cache()

def _get_from_cache(key: str) -> Optional[Dict]:
    """Get data from cache if not expired."""
    if key not in _recommendations_cache:
        return None
        
    cache_entry = _recommendations_cache[key]
    if time.time() > cache_entry["expires_at"]:
        # Expired
        del _recommendations_cache[key]
        return None
        
    return cache_entry["data"]

def _clean_expired_cache() -> None:
    """Remove expired entries from cache."""
    now = time.time()
    expired_keys = [
        k for k, v in _recommendations_cache.items() 
        if now > v["expires_at"]
    ]
    for k in expired_keys:
        del _recommendations_cache[k]
    
    if expired_keys:
        logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")

def _build_recommendation_prompt(user_preferences, available_products, recent_scans=None):
    """Build prompt for Gemini with user context and products."""
    # Format recent scans summary if available
    recent_scans_summary = ""
    if recent_scans:
        recent_scans_summary = ", ".join([f"{scan.product.name} ({scan.product.brand})" for scan in recent_scans[:5]])
    
    # Build user profile section
    user_profile = f"""## User Profile
- Health Goals: {user_preferences.get('health_goal', 'Not specified')}  
- Sourcing Preferences: {user_preferences.get('sourcing_preference', 'Not specified')}  
- Cooking Style: {user_preferences.get('cooking_style', 'Not specified')}  
- Ethical Concerns: {', '.join(user_preferences.get('ethical_concerns', []))}  
- Additive Preferences: {user_preferences.get('additive_preference', 'Not specified')}  
- Dietary Goals: {user_preferences.get('dietary_goal', 'Not specified')}  
- Recent Scans: {recent_scans_summary}"""
    
    # Build product data section
    product_data = f"## Available Products\n{json.dumps(available_products, indent=2)}"
    
    # Build instructions section
    instructions = """## Instructions:
1. Analyze the products and select 4–8 that best match the user's goals and values.
2. If limited matches exist, prioritize health goals and additive avoidance.
3. Group the results into 2–4 relevant sections based on the user's profile.
4. For each product, provide:
   - A short one-line reason (max 12 words)
   - A simple highlight tag (max 2-3 words)
5. Keep all text concise and focused - section titles should be 2-4 words.
6. Format your response in structured JSON for easy rendering in a mobile Explore page."""

    # Build response format section
    response_format = """## Response Format (JSON):
{
  "sections": [
    {
      "title": "Heart-Healthy Picks",
      "description": "Low-sodium, lean meats aligned with your goals",
      "products": [
        {
          "code": "123456789",
          "name": "Grass-Fed Ground Beef",
          "reason": "Great for heart health and ethically sourced",
          "highlight": "Antibiotic-Free"
        }
      ]
    }
  ]
}

Respond with valid JSON only."""
    
    # Combine all sections
    prompt = f"""You are a personalized meat product advisor for ClearCut AI, specializing in nutrition, health impact, and ethical sourcing. Your role is to recommend meat-based products from a structured dataset that best match the user's profile. Each recommendation must feel curated, thoughtful, and aligned with the user's goals and values.

{user_profile}

{product_data}

{instructions}

{response_format}"""
    
    return prompt

def _parse_gemini_response(response_text):
    """Parse Gemini response into structured format."""
    try:
        # Check if the response is wrapped in Markdown code blocks
        text = response_text.strip()
        if text.startswith("```json") and text.endswith("```"):
            # Extract the JSON content from the Markdown code block
            json_content = text[7:-3].strip()  # Remove ```json and ``` markers
            recommendations = json.loads(json_content)
        else:
            # Try direct JSON parsing
            recommendations = json.loads(text)
        
        # Basic validation
        if not isinstance(recommendations, dict) or "sections" not in recommendations:
            logger.error("Invalid response format from Gemini")
            return {"sections": []}
        
        return recommendations
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return {"sections": []} 