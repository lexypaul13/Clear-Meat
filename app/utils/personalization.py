"""Personalization utilities for matching user preferences to product data."""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def apply_user_preferences(product_data: dict, user_preferences: dict) -> dict:
    """
    Apply user preference flags to product ingredients assessment.
    
    Args:
        product_data: Product JSON with ingredients_assessment
        user_preferences: User preferences from the database
        
    Returns:
        dict: Updated product data with matches_user_preference flags
    """
    if "ingredients_assessment" not in product_data:
        logger.warning("Product data missing ingredients_assessment")
        return product_data
    
    # Process each risk level
    for risk_level in ["high_risk", "moderate_risk", "low_risk"]:
        if risk_level not in product_data["ingredients_assessment"]:
            continue
            
        for ingredient in product_data["ingredients_assessment"][risk_level]:
            # Add the preference match flag
            ingredient["matches_user_preference"] = _check_ingredient_match(
                ingredient, user_preferences
            )
            
            # Remove safer_alternatives as requested
            ingredient.pop("safer_alternatives", None)
    
    return product_data


def _check_ingredient_match(ingredient: dict, preferences: dict) -> bool:
    """
    Check if an ingredient matches any user preference for flagging.
    
    Maps the task requirements to the actual database preference fields:
    - avoid_preservatives → prefer_no_preservatives OR avoid_preservatives
    - avoid_flavor_enhancers → prefer_no_flavor_enhancers  
    - avoid_added_sugars → prefer_no_added_sugars
    - prefer_low_sodium → prefer_reduced_sodium OR nutrition_focus == "salt"
    
    Args:
        ingredient: Ingredient dict with name, category, etc.
        preferences: User preferences from database
        
    Returns:
        bool: True if ingredient matches a user preference concern
    """
    name = ingredient.get("name", "").lower()
    category = ingredient.get("category", "").lower()
    
    # Check preservatives preference
    avoid_preservatives = (
        preferences.get("prefer_no_preservatives") or 
        preferences.get("avoid_preservatives")
    )
    if avoid_preservatives and category == "preservative":
        return True
    
    # Check flavor enhancers preference
    avoid_flavor_enhancers = preferences.get("prefer_no_flavor_enhancers")
    if avoid_flavor_enhancers:
        if "msg" in name or ingredient.get("name") == "Flavorings":
            return True
    
    # Check added sugars preference
    avoid_added_sugars = preferences.get("prefer_no_added_sugars")
    if avoid_added_sugars:
        if "sugar" in name or category == "sweetener":
            return True
    
    # Check sodium preference
    prefer_low_sodium = (
        preferences.get("prefer_reduced_sodium") or 
        preferences.get("nutrition_focus") == "salt"
    )
    if prefer_low_sodium and name == "salt":
        return True
    
    # Note: prefer_hormone_free and prefer_antibiotic_free would need 
    # meat source data which isn't available in ingredient assessment
    
    return False 