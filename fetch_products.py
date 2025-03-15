import openfoodfacts
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Product, Base
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection
# In production, use environment variables for database credentials
DATABASE_URL = "postgresql://username:password@host:5432/meatproducts"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def fetch_meat_products():
    """
    Fetch meat products from Open Food Facts API and store them in the database
    """
    meat_types = ["beef", "pork", "chicken", "turkey", "lamb", "veal", "duck", "venison"]
    
    for meat_type in meat_types:
        logger.info(f"Fetching {meat_type} products...")
        
        # Fetch products for this meat type
        results = openfoodfacts.products.advanced_search({
            "search_terms": meat_type,
            "tagtype_0": "categories",
            "tag_contains_0": "contains",
            "tag_0": "meats",
            "page_size": 50
        })
        
        products = results.get('products', [])
        logger.info(f"Found {len(products)} {meat_type} products")
        
        # Process each product
        for product in products:
            try:
                code = product.get('code')
                if not code:
                    continue
                
                # Get detailed product info
                detailed_product = openfoodfacts.products.get_product(code)
                if detailed_product.get('status') != 1:
                    continue
                
                product_data = detailed_product.get('product', {})
                
                # Extract nutritional information
                nutriments = product_data.get('nutriments', {})
                
                # Check for additives
                additives_tags = product_data.get('additives_tags', [])
                ingredients_text = product_data.get('ingredients_text', '')
                
                # Determine risk rating based on additives and other factors
                risk_rating = "Green"  # Default
                if any(additive for additive in additives_tags if 'e250' in additive.lower() or 'nitrite' in additive.lower()):
                    contains_nitrites = True
                    risk_rating = "Red"
                else:
                    contains_nitrites = False
                
                if any(additive for additive in additives_tags if 'phosphate' in additive.lower()):
                    contains_phosphates = True
                    if risk_rating != "Red":
                        risk_rating = "Yellow"
                else:
                    contains_phosphates = False
                
                if len(additives_tags) > 3:
                    contains_preservatives = True
                    if risk_rating == "Green":
                        risk_rating = "Yellow"
                else:
                    contains_preservatives = False
                
                # Create or update product in database
                db = SessionLocal()
                try:
                    # Check if product already exists
                    existing_product = db.query(Product).filter(Product.code == code).first()
                    
                    if existing_product:
                        # Update existing product
                        existing_product.name = product_data.get('product_name', '')
                        existing_product.ingredients = product_data.get('ingredients_text', '')
                        existing_product.calories = nutriments.get('energy-kcal_100g')
                        existing_product.protein = nutriments.get('proteins_100g')
                        existing_product.fat = nutriments.get('fat_100g')
                        existing_product.carbohydrates = nutriments.get('carbohydrates_100g')
                        existing_product.salt = nutriments.get('salt_100g')
                        existing_product.meat_type = meat_type
                        existing_product.contains_nitrites = contains_nitrites
                        existing_product.contains_phosphates = contains_phosphates
                        existing_product.contains_preservatives = contains_preservatives
                        existing_product.risk_rating = risk_rating
                        existing_product.last_updated = datetime.utcnow()
                        existing_product.image_url = product_data.get('image_url')
                        
                        logger.info(f"Updated product: {existing_product.name} ({code})")
                    else:
                        # Create new product
                        new_product = Product(
                            code=code,
                            name=product_data.get('product_name', ''),
                            ingredients=product_data.get('ingredients_text', ''),
                            calories=nutriments.get('energy-kcal_100g'),
                            protein=nutriments.get('proteins_100g'),
                            fat=nutriments.get('fat_100g'),
                            carbohydrates=nutriments.get('carbohydrates_100g'),
                            salt=nutriments.get('salt_100g'),
                            meat_type=meat_type,
                            contains_nitrites=contains_nitrites,
                            contains_phosphates=contains_phosphates,
                            contains_preservatives=contains_preservatives,
                            risk_rating=risk_rating,
                            image_url=product_data.get('image_url')
                        )
                        db.add(new_product)
                        logger.info(f"Added new product: {new_product.name} ({code})")
                    
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error processing product {code}: {str(e)}")
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Error processing product: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting meat product fetch process")
    fetch_meat_products()
    logger.info("Completed meat product fetch process") 