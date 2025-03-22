"""Helper functions for the MeatWise application."""

from typing import Any, Dict, List, Optional, Union

from app.api.v1 import models
from app.db import models as db_models


def calculate_risk_score(product: Union[models.ProductBase, Dict[str, Any], db_models.Product]) -> int:
    """
    Calculate a risk score for a product based on its attributes.
    
    Args:
        product: Product data
        
    Returns:
        int: Risk score (0-100, where 100 is highest risk)
    """
    score = 0
    
    # Convert SQLAlchemy model to dict if needed
    if isinstance(product, db_models.Product):
        product = {
            "contains_nitrites": product.contains_nitrites,
            "contains_phosphates": product.contains_phosphates,
            "contains_preservatives": product.contains_preservatives,
            "antibiotic_free": product.antibiotic_free,
            "hormone_free": product.hormone_free,
            "pasture_raised": product.pasture_raised
        }
    
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
        # Extract specific fields without creating a ProductBase object
        salt = getattr(product, 'salt', None)
        contains_nitrites = getattr(product, 'contains_nitrites', False)
        fat = getattr(product, 'fat', None)
        contains_preservatives = getattr(product, 'contains_preservatives', False)
        contains_phosphates = getattr(product, 'contains_phosphates', False)
        
        # Check for high sodium
        if salt and salt > 1.5:
            concerns.append("High in sodium")
        
        # Check for nitrites
        if contains_nitrites:
            concerns.append("Contains nitrites which may form carcinogenic compounds")
        
        # Check for high fat
        if fat and fat > 20:
            concerns.append("High fat content")
        
        # Check for preservatives
        if contains_preservatives:
            concerns.append("Contains preservatives that may cause health issues")
        
        # Check for phosphates
        if contains_phosphates:
            concerns.append("Contains phosphates which may impact kidney health")
        
        return concerns
    # Handle dict case   
    elif isinstance(product, dict):
        # Extract specific fields without creating a ProductBase object
        salt = product.get('salt')
        contains_nitrites = product.get('contains_nitrites', False)
        fat = product.get('fat')
        contains_preservatives = product.get('contains_preservatives', False)
        contains_phosphates = product.get('contains_phosphates', False)
        
        # Check for high sodium
        if salt and salt > 1.5:
            concerns.append("High in sodium")
        
        # Check for nitrites
        if contains_nitrites:
            concerns.append("Contains nitrites which may form carcinogenic compounds")
        
        # Check for high fat
        if fat and fat > 20:
            concerns.append("High fat content")
        
        # Check for preservatives
        if contains_preservatives:
            concerns.append("Contains preservatives that may cause health issues")
        
        # Check for phosphates
        if contains_phosphates:
            concerns.append("Contains phosphates which may impact kidney health")
        
        return concerns
    
    # Check for high sodium
    if product.salt and product.salt > 1.5:
        concerns.append("High in sodium")
    
    # Check for nitrites
    if product.contains_nitrites:
        concerns.append("Contains nitrites which may form carcinogenic compounds")
    
    # Check for high fat
    if product.fat and product.fat > 20:
        concerns.append("High fat content")
    
    # Check for preservatives
    if product.contains_preservatives:
        concerns.append("Contains preservatives that may cause health issues")
    
    # Check for phosphates
    if product.contains_phosphates:
        concerns.append("Contains phosphates which may impact kidney health")
    
    return concerns


def assess_environmental_impact(product: Union[models.ProductBase, Dict[str, Any], db_models.Product]) -> Dict[str, Any]:
    """
    Assess environmental impact for a product.
    
    Args:
        product: Product data
        
    Returns:
        Dict[str, Any]: Environmental impact assessment
    """
    impact = "Medium"
    details = ""
    sustainability_practices = []
    
    # Check if it's already a ProductBase object
    if isinstance(product, models.ProductBase):
        pass  
    # Convert SQLAlchemy model to dict if needed
    elif isinstance(product, db_models.Product):
        meat_type = getattr(product, 'meat_type', None)
        pasture_raised = getattr(product, 'pasture_raised', False)
    # Handle dict case
    elif isinstance(product, dict):
        meat_type = product.get('meat_type')
        pasture_raised = product.get('pasture_raised', False)
    else:
        meat_type = product.meat_type
        pasture_raised = product.pasture_raised
    
    # Assess based on meat type
    if meat_type:
        meat_type_lower = meat_type.lower()
        
        if meat_type_lower == "beef":
            impact = "High"
            details = "Beef production has one of the highest environmental impacts among animal products."
        elif meat_type_lower in ["pork", "ham", "bacon"]:
            impact = "Medium"
            details = "Pork production has a moderate environmental impact compared to beef but higher than plant-based proteins."
        elif meat_type_lower in ["chicken", "turkey", "poultry"]:
            impact = "Low-Medium"
            details = "Poultry production generally has a lower environmental impact than red meat production."
        elif meat_type_lower in ["lamb", "mutton"]:
            impact = "High"
            details = "Lamb production has a high environmental impact comparable to beef."
        elif meat_type_lower in ["fish", "seafood"]:
            impact = "Low-Medium"
            details = "Seafood production impact varies greatly by species and fishing methods."
    
    # Add sustainability practices
    if pasture_raised:
        sustainability_practices.append("Pasture-raised which reduces environmental impact")
    else:
        sustainability_practices.append("Not pasture-raised")
        
    sustainability_practices.append("No information available on water usage or carbon footprint")
    
    return {
        "impact": impact,
        "details": details,
        "sustainability_practices": sustainability_practices
    } 