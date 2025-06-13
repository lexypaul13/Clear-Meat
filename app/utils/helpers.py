"""Helper functions for the MeatWise application."""

from typing import Any, Dict, List, Optional, Union
import re

from app.api.v1 import models
from app.db import models as db_models
from app.models.ingredient import AdditiveInfo


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


def extract_additives_from_text(ingredients_text: str) -> List[AdditiveInfo]:
    """
    Extract additives from ingredients text.
    This replaces the previous database lookup in the ingredients table.
    
    Args:
        ingredients_text: Raw ingredients text
        
    Returns:
        List[AdditiveInfo]: List of detected additives
    """
    if not ingredients_text:
        return []
    
    # Common additives and preservatives to look for
    additive_patterns = [
        # Format: (regex pattern, name, category, risk_level, concerns, alternatives)
        (r'(?<![a-zA-Z])E(\s)?250|sodium\s*nitrite', 
         'Sodium Nitrite (E250)', 'preservative', 'high', 
         ['Cancer risk', 'Blood vessel damage'], 
         ['Celery powder', 'Cherry powder', 'Vitamin C']),
        
        (r'(?<![a-zA-Z])E(\s)?251|sodium\s*nitrate', 
         'Sodium Nitrate (E251)', 'preservative', 'high', 
         ['Cancer risk', 'Blood vessel damage'], 
         ['Celery powder', 'Cherry powder']),
        
        (r'(?<![a-zA-Z])E(\s)?450|sodium\s*phosphate', 
         'Sodium Phosphate (E450)', 'stabilizer', 'medium', 
         ['Kidney damage', 'Heart issues'], 
         ['Potassium phosphate', 'Natural brines']),
        
        (r'(?<![a-zA-Z])E(\s)?621|monosodium\s*glutamate|MSG', 
         'Monosodium Glutamate (E621)', 'flavor enhancer', 'medium', 
         ['Headaches', 'Flushing'], 
         ['Yeast extract', 'Mushroom extract']),
        
        (r'BHA|butylated\s*hydroxyanisole|(?<![a-zA-Z])E(\s)?320', 
         'Butylated Hydroxyanisole (BHA/E320)', 'antioxidant', 'medium', 
         ['Hormone disruption', 'Potential carcinogen'], 
         ['Vitamin E', 'Rosemary extract']),
    ]
    
    found_additives = []
    
    # Check for each additive
    for pattern, name, category, risk_level, concerns, alternatives in additive_patterns:
        if re.search(pattern, ingredients_text, re.IGNORECASE):
            additive = AdditiveInfo(
                name=name,
                category=category,
                risk_level=risk_level,
                concerns=concerns,
                alternatives=alternatives
            )
            found_additives.append(additive)
    
    return found_additives


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
    
    try:
        # Handle different types of product objects
        if isinstance(product, dict):
            # Dictionary type
            salt = product.get('salt')
            fat = product.get('fat')
            
            if salt and salt > 1.5:
                concerns.append("High in sodium")
            if fat and fat > 20:
                concerns.append("High in fat")
                
        elif isinstance(product, (models.ProductBase, db_models.Product)):
            # Pydantic or SQLAlchemy model
            salt = getattr(product, 'salt', None)
            fat = getattr(product, 'fat', None)
            
            if salt and salt > 1.5:
                concerns.append("High in sodium")
            if fat and fat > 20:
                concerns.append("High in fat")
    except Exception as e:
        # Log the error but don't raise it
        import logging
        logging.error(f"Error assessing health concerns: {str(e)}")
    
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
    # Default values
    impact = "Moderate"
    details = "Environmental impact assessment based on meat type and processing method."
    practices = []
    
    try:
        # Get meat type safely
        meat_type = None
        if isinstance(product, dict):
            meat_type = product.get('meat_type')
        else:
            meat_type = getattr(product, 'meat_type', None)
        
        # Adjust impact based on meat type
        if meat_type:
            meat_type = meat_type.lower()
            if 'beef' in meat_type:
                impact = "High"
                details = "Beef production typically has a higher environmental footprint due to methane emissions and land use."
            elif 'pork' in meat_type:
                impact = "Moderate"
                details = "Pork production has a moderate environmental impact compared to beef but higher than poultry."
            elif 'chicken' in meat_type or 'poultry' in meat_type:
                impact = "Lower"
                details = "Poultry generally has a lower environmental footprint than red meat."
    except Exception as e:
        # Log the error but don't raise it
        import logging
        logging.error(f"Error assessing environmental impact: {str(e)}")
    
    return {
        "impact": impact,
        "details": details,
        "sustainability_practices": practices
    } 


def convert_to_structured_product(product: db_models.Product) -> models.ProductStructured:
    """
    Convert a database Product model to a ProductStructured model.
    
    Args:
        product: Database product model
        
    Returns:
        ProductStructured: Structured product model for API responses
    """
    # Extract additives from ingredients text
    additives = extract_additives_from_text(product.ingredients_text or "")
    
    # Assess health concerns based on data
    health_concerns = assess_health_concerns(product)
    
    # Create environmental impact assessment
    env_impact = assess_environmental_impact(product)
    
    # Build structured response
    return models.ProductStructured(
        product=models.ProductInfo(
            code=product.code,
            name=product.name,
            brand=product.brand,
            description=product.description,
            ingredients_text=product.ingredients_text,
            image_url=product.image_url,
            image_data=product.image_data,
            meat_type=product.meat_type
        ),
        criteria=models.ProductCriteria(
            risk_rating=product.risk_rating,
            additives=additives
        ),
        health=models.ProductHealth(
            nutrition=models.ProductNutrition(
                calories=product.calories,
                protein=product.protein,
                fat=product.fat,
                carbohydrates=product.carbohydrates,
                salt=product.salt
            ),
            health_concerns=health_concerns
        ),
        environment=models.ProductEnvironment(
            impact=env_impact["impact"],
            details=env_impact["details"],
            sustainability_practices=env_impact["sustainability_practices"]
        ),
        metadata=models.ProductMetadata(
            last_updated=product.last_updated,
            created_at=product.created_at
        )
    ) 


def convert_dict_to_structured_product(product_data: Dict[str, Any]) -> models.ProductStructured:
    """
    Convert a dictionary (from Supabase) to a ProductStructured model.
    
    Args:
        product_data: Dictionary containing product data from Supabase
        
    Returns:
        ProductStructured: Structured product model for API responses
    """
    # Extract additives from ingredients text
    additives = extract_additives_from_text(product_data.get('ingredients_text', '') or "")
    
    # Assess health concerns based on data
    health_concerns = assess_health_concerns(product_data)
    
    # Create environmental impact assessment
    env_impact = assess_environmental_impact(product_data)
    
    # Build structured response
    return models.ProductStructured(
        product=models.ProductInfo(
            code=product_data.get('code', ''),
            name=product_data.get('name', ''),
            brand=product_data.get('brand', ''),
            description=product_data.get('description', ''),
            ingredients_text=product_data.get('ingredients_text', ''),
            image_url=product_data.get('image_url', ''),
            image_data=product_data.get('image_data', ''),
            meat_type=product_data.get('meat_type', '')
        ),
        criteria=models.ProductCriteria(
            risk_rating=product_data.get('risk_rating', ''),
            additives=additives
        ),
        health=models.ProductHealth(
            nutrition=models.ProductNutrition(
                calories=product_data.get('calories'),
                protein=product_data.get('protein'),
                fat=product_data.get('fat'),
                carbohydrates=product_data.get('carbohydrates'),
                salt=product_data.get('salt')
            ),
            health_concerns=health_concerns
        ),
        environment=models.ProductEnvironment(
            impact=env_impact["impact"],
            details=env_impact["details"],
            sustainability_practices=env_impact["sustainability_practices"]
        ),
        metadata=models.ProductMetadata(
            last_updated=product_data.get('last_updated'),
            created_at=product_data.get('created_at')
        )
    ) 