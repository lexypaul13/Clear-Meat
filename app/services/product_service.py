import openfoodfacts
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.models.product import Product

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_meat_products(db: Session):
    """
    Fetch meat products from Open Food Facts API and store them in the database
    """
    meat_types = ["beef", "pork", "chicken", "turkey", "lamb", "veal", "duck", "venison"]
    
    for meat_type in meat_types:
        logger.info(f"Fetching {meat_type} products...")
        
        # Fetch products for this meat type
        search_result = openfoodfacts.products.advanced_search({
            "search_terms": meat_type,
            "page_size": 100,
            "json": True
        })
        
        if search_result.get('count'):
            products = search_result.get('products', [])
            logger.info(f"Found {len(products)} {meat_type} products")
            
            for product_data in products:
                try:
                    # Check if this is actually a meat product
                    categories = product_data.get('categories_tags', [])
                    if not any(meat in ' '.join(categories) for meat in meat_types):
                        continue
                    
                    # Get product code
                    code = product_data.get('code')
                    if not code:
                        continue
                    
                    # Check if product already exists
                    existing_product = db.query(Product).filter(Product.code == code).first()
                    
                    # Create or update product
                    if not existing_product:
                        product = Product(
                            code=code,
                            name=product_data.get('product_name', ''),
                            ingredients=product_data.get('ingredients_text', ''),
                            meat_type=meat_type,
                            image_url=product_data.get('image_url')
                        )
                        db.add(product)
                    else:
                        existing_product.name = product_data.get('product_name', existing_product.name)
                        existing_product.ingredients = product_data.get('ingredients_text', existing_product.ingredients)
                        existing_product.image_url = product_data.get('image_url', existing_product.image_url)
                        existing_product.last_updated = datetime.utcnow()
                    
                    # Extract nutritional information
                    nutriments = product_data.get('nutriments', {})
                    if existing_product:
                        existing_product.calories = nutriments.get('energy-kcal_100g')
                        existing_product.protein = nutriments.get('proteins_100g')
                        existing_product.fat = nutriments.get('fat_100g')
                        existing_product.carbohydrates = nutriments.get('carbohydrates_100g')
                        existing_product.salt = nutriments.get('salt_100g')
                    else:
                        product.calories = nutriments.get('energy-kcal_100g')
                        product.protein = nutriments.get('proteins_100g')
                        product.fat = nutriments.get('fat_100g')
                        product.carbohydrates = nutriments.get('carbohydrates_100g')
                        product.salt = nutriments.get('salt_100g')
                    
                    # Check for additives
                    ingredients = product_data.get('ingredients', [])
                    ingredient_text = ' '.join([i.get('text', '') for i in ingredients])
                    
                    nitrites = any(additive in ingredient_text.lower() for additive in ['nitrite', 'nitrate', 'e249', 'e250', 'e251', 'e252'])
                    phosphates = any(additive in ingredient_text.lower() for additive in ['phosphate', 'e338', 'e339', 'e340', 'e341', 'e343'])
                    preservatives = any(additive in ingredient_text.lower() for additive in ['preservative', 'e200', 'e210', 'e220', 'e230', 'e270', 'e280', 'e290'])
                    
                    if existing_product:
                        existing_product.contains_nitrites = nitrites
                        existing_product.contains_phosphates = phosphates
                        existing_product.contains_preservatives = preservatives
                    else:
                        product.contains_nitrites = nitrites
                        product.contains_phosphates = phosphates
                        product.contains_preservatives = preservatives
                    
                    # Calculate risk rating
                    risk_score = 0
                    if nitrites:
                        risk_score += 2
                    if phosphates:
                        risk_score += 1
                    if preservatives:
                        risk_score += 1
                    
                    risk_rating = "Green"
                    if risk_score >= 3:
                        risk_rating = "Red"
                    elif risk_score >= 1:
                        risk_rating = "Yellow"
                    
                    if existing_product:
                        existing_product.risk_rating = risk_rating
                    else:
                        product.risk_rating = risk_rating
                    
                except Exception as e:
                    logger.error(f"Error processing product {product_data.get('code')}: {str(e)}")
                    continue
            
            # Commit changes for this batch
            db.commit()
            logger.info(f"Processed {meat_type} products")
        else:
            logger.warning(f"No {meat_type} products found")
    
    logger.info("Product fetch completed") 