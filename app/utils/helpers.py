"""Helper functions for the MeatWise application."""

from typing import Any, Dict, List, Optional, Union

from app.api.v1 import models


def calculate_risk_score(product: Union[models.ProductBase, Dict[str, Any]]) -> int:
    """
    Calculate a risk score for a product based on its attributes.
    
    Args:
        product: Product data
        
    Returns:
        int: Risk score (0-100, where 100 is highest risk)
    """
    score = 0
    
    # Convert dict to object if needed
    if isinstance(product, dict):
        product = models.ProductBase(**product)
    
    # Additives (up to 60 points)
    if product.contains_nitrites:
        score += 30
    if product.contains_phosphates:
        score += 15
    if product.contains_preservatives:
        score += 15
    
    # Animal welfare (up to 40 points, subtract from score)
    welfare_score = 0
    if product.antibiotic_free:
        welfare_score += 15
    if product.hormone_free:
        welfare_score += 10
    if product.pasture_raised:
        welfare_score += 15
    
    # Final score calculation
    final_score = score - welfare_score
    
    # Ensure score is between 0 and 100
    return max(0, min(100, final_score))


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
    
    Args:
        ingredients: List of ingredients
        
    Returns:
        Dict[str, bool]: Dictionary of detected additives
    """
    result = {
        "contains_nitrites": False,
        "contains_phosphates": False,
        "contains_preservatives": False,
    }
    
    # Common nitrites
    nitrites = ["sodium nitrite", "potassium nitrite", "nitrite", "nitrate", "e250", "e251", "e252"]
    
    # Common phosphates
    phosphates = ["sodium phosphate", "phosphate", "e339", "e340", "e341", "e450", "e451", "e452"]
    
    # Common preservatives
    preservatives = [
        "preservative", "bha", "bht", "tbhq", "sodium benzoate", "potassium sorbate",
        "sodium erythorbate", "sodium nitrite", "sodium nitrate", "e200", "e202", "e211",
        "e220", "e221", "e223", "e250", "e251", "e252", "e270", "e280", "e281", "e282",
        "e283", "e300", "e301", "e302", "e304", "e306", "e307", "e308", "e309", "e310",
        "e311", "e312", "e315", "e316", "e319", "e320", "e321"
    ]
    
    # Check each ingredient
    for ingredient in ingredients:
        ingredient_lower = ingredient.lower()
        
        # Check for nitrites
        if any(nitrite in ingredient_lower for nitrite in nitrites):
            result["contains_nitrites"] = True
        
        # Check for phosphates
        if any(phosphate in ingredient_lower for phosphate in phosphates):
            result["contains_phosphates"] = True
        
        # Check for preservatives
        if any(preservative in ingredient_lower for preservative in preservatives):
            result["contains_preservatives"] = True
    
    return result 