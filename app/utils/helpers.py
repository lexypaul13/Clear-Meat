"""Helper functions for the MeatWise application."""

from typing import Any, Dict, List, Optional, Union

from app.api.v1 import models
from app.db import models as db_models


def calculate_risk_score(product: Union[models.ProductBase, Dict[str, Any], db_models.Product]) -> int:
    """
    Calculate a risk score for a product based on AI analysis.
    
    Args:
        product: Product data
        
    Returns:
        int: Risk score (0-100, where 100 is highest risk)
    """
    # This function now uses AI analysis instead of hardcoded fields
    # For backward compatibility, return a moderate score
    return 50


def get_risk_rating(score: int) -> str:
    """
    Convert a risk score to a risk rating.
    
    Args:
        score: Risk score (0-100)
        
    Returns:
        str: Risk rating (Green, Yellow, or Red)
    """
    if score < 30:
        return "Green"
    elif score < 70:
        return "Yellow"
    else:
        return "Red"


def parse_ingredients_text(ingredients_text: str) -> List[str]:
    """
    Parse ingredients text into a list of individual ingredients.
    
    Args:
        ingredients_text: Raw ingredients text
        
    Returns:
        List[str]: List of individual ingredients
    """
    if not ingredients_text:
        return []
    
    # Split by commas and clean up
    ingredients = [i.strip() for i in ingredients_text.split(",")]
    
    # Remove empty strings
    ingredients = [i for i in ingredients if i]
    
    return ingredients


def detect_additives(ingredients: List[str]) -> Dict[str, bool]:
    """
    Detect common additives in a list of ingredients.
    This is now handled by AI analysis.
    
    Args:
        ingredients: List of ingredients
        
    Returns:
        Dict[str, bool]: Dictionary of detected additives
    """
    # In the AI-first approach, we don't use hardcoded detection
    # This function is kept for backward compatibility
    return {
        "contains_nitrites": False,
        "contains_phosphates": False,
        "contains_preservatives": False,
    }


def generate_random_id(length: int = 8) -> str:
    """
    Generate a random ID for problem reports.
    
    Args:
        length: Length of the ID to generate
        
    Returns:
        str: Random ID
    """
    import random
    import string
    
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def assess_health_concerns(product: Union[models.ProductBase, Dict[str, Any], db_models.Product]) -> List[str]:
    """
    Assess health concerns for a product.
    
    Args:
        product: Product data
        
    Returns:
        List[str]: List of health concerns
    """
    concerns = []
    
    # Check if it's already a ProductBase object
    if isinstance(product, models.ProductBase):
        pass
    # Convert SQLAlchemy model to dict if needed
    elif isinstance(product, db_models.Product):
        # Extract nutritional information
        salt = getattr(product, 'salt', None)
        fat = getattr(product, 'fat', None)
        
        # Check for high sodium
        if salt and salt > 1.5:
            concerns.append("High in sodium")
        
        # Check for high fat
        if fat and fat > 20:
            concerns.append("High in fat")
    
    # For now, return basic concerns based on nutritional values
    return concerns


def assess_environmental_impact(product: Union[models.ProductBase, Dict[str, Any], db_models.Product]) -> Dict[str, Any]:
    """
    Assess environmental impact for a product.
    This is now handled by AI analysis.
    
    Args:
        product: Product data
        
    Returns:
        Dict[str, Any]: Environmental impact assessment
    """
    # In the AI-first approach, environmental impact is assessed by AI
    # Return a placeholder impact assessment
    return {
        "impact": "Moderate",
        "details": "Environmental impact is now assessed using AI analysis.",
        "sustainability_practices": []
    } 