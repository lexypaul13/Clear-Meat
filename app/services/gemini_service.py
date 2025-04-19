"""Gemini service for personalized recommendations."""
import google.generativeai as genai
from typing import Dict, List, Any
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini client
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")

def get_personalized_recommendations(user_preferences, available_products, recent_scans=None):
    """Generate personalized product recommendations using Gemini."""
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return {"sections": []}
    
    # Format prompt with user context and products
    prompt = _build_recommendation_prompt(user_preferences, available_products, recent_scans)
    
    try:
        # Call Gemini API
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)
        
        # Parse and validate response
        recommendations = _parse_gemini_response(response.text)
        return recommendations
    
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return {"sections": []}

def _build_recommendation_prompt(user_preferences, available_products, recent_scans=None):
    """Build prompt for Gemini with user context and products."""
    # Format recent scans summary if available
    recent_scans_summary = ""
    if recent_scans:
        recent_scans_summary = ", ".join([f"{scan.product.name} ({scan.product.brand})" for scan in recent_scans[:5]])
    
    # Construct the prompt using the template
    prompt = f"""
    You are a personalized meat product advisor for ClearCut AI, specializing in nutrition, health impact, and ethical sourcing. Your role is to recommend meat-based products from a structured dataset that best match the user's profile. Each recommendation must feel curated, thoughtful, and aligned with the user's goals and values.
    
    ## User Profile
    - Health Goals: {user_preferences.get('health_goal', 'Not specified')}  
    - Sourcing Preferences: {user_preferences.get('sourcing_preference', 'Not specified')}  
    - Cooking Style: {user_preferences.get('cooking_style', 'Not specified')}  
    - Ethical Concerns: {', '.join(user_preferences.get('ethical_concerns', []))}  
    - Additive Preferences: {user_preferences.get('additive_preference', 'Not specified')}  
    - Dietary Goals: {user_preferences.get('dietary_goal', 'Not specified')}  
    - Recent Scans: {recent_scans_summary}  
    
    ## Available Products
    {json.dumps(available_products, indent=2)}
    
    ## Instructions:
    1. Analyze the products and select 4–8 that best match the user's goals and values.
    2. If limited matches exist, prioritize health goals and additive avoidance.
    3. Group the results into 2–4 relevant sections based on the user's profile.
    4. For each product, provide:
       - A short human-like reason for recommendation
       - One highlight tag (e.g., "Antibiotic-Free," "Keto-Friendly")
    5. Format your response in structured JSON for easy rendering in a mobile Explore page.
    
    ## Response Format (JSON):
    {
      "sections": [
        {
          "title": "Clean & Heart-Healthy Choices",
          "description": "Products low in sodium and free of risky preservatives—great for cardiovascular health",
          "products": [
            {
              "code": "123456789",
              "name": "Grass-Fed Ground Beef",
              "reason": "This beef supports your heart-health goal and avoids nitrites, making it a clean protein choice.",
              "highlight": "Pasture-Raised"
            }
          ]
        }
      ]
    }
    
    Respond with valid JSON only.
    """
    
    return prompt

def _parse_gemini_response(response_text):
    """Parse Gemini response into structured format."""
    try:
        # Extract and parse JSON from the response
        recommendations = json.loads(response_text)
        
        # Basic validation
        if not isinstance(recommendations, dict) or "sections" not in recommendations:
            logger.error("Invalid response format from Gemini")
            return {"sections": []}
        
        return recommendations
    except json.JSONDecodeError:
        logger.error("Failed to parse Gemini response as JSON")
        return {"sections": []} 