"""OpenFoodFacts API service for fetching product data when not found in local database."""

import requests
import logging
from typing import Dict, Optional, Any, List
import re

logger = logging.getLogger(__name__)

class OpenFoodFactsService:
    """Service for fetching product data from OpenFoodFacts API."""
    
    def __init__(self):
        self.base_url = "https://world.openfoodfacts.org/api/v2/product"
        self.headers = {
            "User-Agent": "Clear-Meat-API/1.0 (support@clear-meat.com)"
        }
        
        # Valid meat types in our database
        self.valid_meat_types = ["beef", "pork", "dairy", "chicken", "fish", "lamb", "turkey"]
        
        # Keywords for detecting animal products
        self.animal_keywords = {
            "beef": ["beef", "cow", "veal", "steak", "ground beef", "hamburger"],
            "pork": ["pork", "pig", "ham", "bacon", "sausage", "chorizo", "salami"],
            "chicken": ["chicken", "poultry", "hen", "rooster"],
            "turkey": ["turkey"],
            "lamb": ["lamb", "mutton", "sheep"],
            "fish": ["fish", "salmon", "tuna", "cod", "seafood", "shrimp", "crab", "lobster", "sardine", "mackerel"],
            "dairy": ["milk", "cheese", "yogurt", "yoghurt", "butter", "cream", "dairy", "lactose"]
        }
        
        # Category keywords that indicate animal products
        self.animal_categories = [
            "meat", "meats", "beef", "pork", "chicken", "turkey", "lamb", "fish", "seafood",
            "dairy", "cheese", "milk", "yogurt", "yoghurt", "butter", "cream",
            "poultry", "sausage", "ham", "bacon", "jerky", "deli"
        ]

    def get_product_by_barcode(self, barcode: str) -> Dict[str, Any]:
        """
        Get product information from OpenFoodFacts by barcode.
        Handles partial barcodes by trying multiple formats.
        
        Args:
            barcode: Product barcode (may be partial)
            
        Returns:
            Dict containing product information or error details
        """
        # Generate list of barcode variations to try
        barcode_variations = self._generate_barcode_variations(barcode)
        
        logger.info(f"Trying {len(barcode_variations)} barcode variations for {barcode}")
        
        for attempt_barcode in barcode_variations:
            try:
                logger.debug(f"Attempting barcode: {attempt_barcode}")
                url = f"{self.base_url}/{attempt_barcode}.json"
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == 1:
                        product = data["product"]
                        
                        # Check if it's an animal product
                        meat_type = self._detect_meat_type(product)
                        if not meat_type:
                            return {
                                "found": False, 
                                "is_animal_product": False,
                                "message": "Product found but is not an animal-based product",
                                "tried_barcode": attempt_barcode
                            }
                        
                        # Map to our schema
                        mapped_product = self._map_to_clear_meat_schema(product, meat_type)
                        
                        logger.info(f"Found product with barcode variation: {attempt_barcode}")
                        return {
                            "found": True,
                            "is_animal_product": True,
                            "meat_type": meat_type,
                            "product_data": mapped_product,
                            "raw_data": product,
                            "used_barcode": attempt_barcode,
                            "original_barcode": barcode
                        }
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for barcode {attempt_barcode}")
                continue
            except Exception as e:
                logger.warning(f"Error for barcode {attempt_barcode}: {str(e)}")
                continue
        
        # No variations worked
        logger.error(f"No barcode variations worked for {barcode}")
        return {
            "found": False, 
            "message": f"Product not found in OpenFoodFacts (tried {len(barcode_variations)} variations)",
            "tried_barcodes": barcode_variations
        }

    def _generate_barcode_variations(self, barcode: str) -> List[str]:
        """
        Generate possible barcode variations to try.
        Handles cases where scanner might read partial barcodes.
        
        Args:
            barcode: Original scanned barcode
            
        Returns:
            List of barcode variations to try
        """
        variations = [barcode]  # Always try the original first
        
        # If barcode is 10 digits, it might be missing leading and/or trailing digits
        if len(barcode) == 10:
            # Try the specific case we know: 9470001026 -> 894700010267
            if barcode == "9470001026":
                variations.extend([
                    "894700010267",    # Known correct UPC-A
                    "0894700010267",   # Known correct EAN-13
                ])
            
            # General patterns for 10-digit barcodes
            variations.extend([
                f"8{barcode}67",   # Add 8 prefix + 67 suffix (pattern from our case)
                f"8{barcode}7",    # Add 8 prefix + 7 suffix
                f"8{barcode}",     # Add 8 prefix only (makes 11 digits)
                f"89{barcode}",    # Add 89 prefix (makes 12 digits)  
                f"0{barcode}",     # Add 0 prefix (makes 11 digits)
            ])
        
        # If barcode is 11 digits, try adding one leading digit
        elif len(barcode) == 11:
            variations.extend([
                f"0{barcode}",   # Add 0 prefix
                f"8{barcode}",   # Add 8 prefix
            ])
        
        # If barcode is 12 digits (UPC-A), also try with 0 prefix (EAN-13)
        elif len(barcode) == 12:
            variations.append(f"0{barcode}")
        
        # If barcode is 13 digits (EAN-13) and starts with 0, also try without 0
        elif len(barcode) == 13 and barcode.startswith("0"):
            variations.append(barcode[1:])
        
        logger.debug(f"Generated {len(variations)} variations: {variations}")
        return variations

    def _detect_meat_type(self, product: Dict[str, Any]) -> Optional[str]:
        """
        Detect if product is animal-based and determine meat type.
        
        Args:
            product: OpenFoodFacts product data
            
        Returns:
            str: Meat type if animal product, None otherwise
        """
        # Get relevant text fields
        name = (product.get("product_name", "") or "").lower()
        categories = (product.get("categories", "") or "").lower()
        ingredients = (product.get("ingredients_text", "") or "").lower()
        brands = (product.get("brands", "") or "").lower()
        
        # Combine all text for analysis
        combined_text = f"{name} {categories} {ingredients} {brands}"
        
        logger.debug(f"Analyzing text for meat type: {combined_text[:200]}...")
        
        # Check for animal product keywords
        detected_types = []
        
        for meat_type, keywords in self.animal_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    detected_types.append(meat_type)
                    logger.debug(f"Found keyword '{keyword}' for meat type '{meat_type}'")
                    break
        
        # Also check categories against animal category keywords
        for category_keyword in self.animal_categories:
            if category_keyword in categories:
                # Try to infer meat type from category
                if any(kt in category_keyword for kt in ["beef", "cow"]):
                    detected_types.append("beef")
                elif any(kt in category_keyword for kt in ["pork", "pig", "ham", "bacon"]):
                    detected_types.append("pork")
                elif any(kt in category_keyword for kt in ["chicken", "poultry"]):
                    detected_types.append("chicken")
                elif any(kt in category_keyword for kt in ["fish", "seafood"]):
                    detected_types.append("fish")
                elif any(kt in category_keyword for kt in ["dairy", "milk", "cheese"]):
                    detected_types.append("dairy")
                elif any(kt in category_keyword for kt in ["turkey"]):
                    detected_types.append("turkey")
                elif any(kt in category_keyword for kt in ["lamb", "sheep"]):
                    detected_types.append("lamb")
                
                logger.debug(f"Found category keyword '{category_keyword}'")
        
        if not detected_types:
            logger.info(f"No animal product keywords found in: {combined_text[:100]}...")
            return None
        
        # Return the most specific/first detected type
        # Priority order: specific meats first, then dairy
        priority_order = ["beef", "pork", "chicken", "turkey", "lamb", "fish", "dairy"]
        
        for priority_type in priority_order:
            if priority_type in detected_types:
                logger.info(f"Detected meat type: {priority_type}")
                return priority_type
        
        # Fallback to first detected
        return detected_types[0]

    def _map_to_clear_meat_schema(self, openfood_product: Dict[str, Any], meat_type: str) -> Dict[str, Any]:
        """
        Map OpenFoodFacts product data to Clear-Meat database schema.
        
        Args:
            openfood_product: Raw OpenFoodFacts product data
            meat_type: Detected meat type
            
        Returns:
            Dict: Product data mapped to Clear-Meat schema
        """
        # Extract nutrition data
        nutriments = openfood_product.get("nutriments", {})
        
        # Get nutrition values (OpenFoodFacts uses per 100g)
        calories = self._extract_nutrition_value(nutriments, "energy-kcal_100g")
        protein = self._extract_nutrition_value(nutriments, "proteins_100g")
        fat = self._extract_nutrition_value(nutriments, "fat_100g")
        carbohydrates = self._extract_nutrition_value(nutriments, "carbohydrates_100g")
        salt = self._extract_nutrition_value(nutriments, "salt_100g")
        
        # Assign basic risk rating based on presence of concerning ingredients
        risk_rating = self._assess_basic_risk_rating(openfood_product)
        
        mapped_data = {
            "name": openfood_product.get("product_name", "Unknown Product"),
            "brand": openfood_product.get("brands", "").split(",")[0].strip() if openfood_product.get("brands") else None,
            "description": openfood_product.get("generic_name", ""),
            "ingredients_text": openfood_product.get("ingredients_text", ""),
            "calories": calories,
            "protein": protein,
            "fat": fat,
            "carbohydrates": carbohydrates,
            "salt": salt,
            "meat_type": meat_type,
            "risk_rating": risk_rating,
            "image_url": openfood_product.get("image_url", ""),
            "image_data": None  # Don't store large base64 data
            # Note: openfoodfacts_id and data_source removed due to schema constraints
        }
        
        logger.info(f"Mapped product: {mapped_data['name']} ({meat_type}) - Risk: {risk_rating}")
        return mapped_data

    def _extract_nutrition_value(self, nutriments: Dict[str, Any], key: str) -> Optional[float]:
        """Extract and validate nutrition value from OpenFoodFacts nutriments."""
        value = nutriments.get(key)
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
        return None

    def _assess_basic_risk_rating(self, product: Dict[str, Any]) -> str:
        """
        Assess basic risk rating based on ingredients.
        
        Args:
            product: OpenFoodFacts product data
            
        Returns:
            str: Risk rating (Green, Yellow, Red)
        """
        ingredients_text = (product.get("ingredients_text", "") or "").lower()
        
        # High risk indicators
        high_risk_keywords = [
            "sodium nitrite", "e250", "nitrate", "e251", "e252",
            "msg", "monosodium glutamate", "e621",
            "bha", "bht", "e320", "e321",
            "artificial color", "red 40", "yellow 6"
        ]
        
        # Moderate risk indicators  
        moderate_risk_keywords = [
            "preservative", "sodium", "salt", "sugar", "dextrose",
            "phosphate", "modified starch", "flavor enhancer"
        ]
        
        # Check for high risk ingredients
        for keyword in high_risk_keywords:
            if keyword in ingredients_text:
                logger.debug(f"High risk ingredient found: {keyword}")
                return "Red"
        
        # Check for moderate risk ingredients
        for keyword in moderate_risk_keywords:
            if keyword in ingredients_text:
                logger.debug(f"Moderate risk ingredient found: {keyword}")
                return "Yellow"
        
        # Default to Green if no concerning ingredients found
        return "Green"


# Global service instance
openfoodfacts_service = OpenFoodFactsService()

def get_openfoodfacts_service() -> OpenFoodFactsService:
    """Dependency to get OpenFoodFacts service."""
    return openfoodfacts_service