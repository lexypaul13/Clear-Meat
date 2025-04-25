"""
Ingredient Extraction Script
--------------------------
This script extracts individual ingredients from the raw ingredients_text field
in the products table and populates the ingredients and product_ingredients tables.
"""

import os
import re
import uuid
import asyncio
import logging
import asyncpg
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import from app modules to reuse existing code
import sys
sys.path.append(".")  # Add the current directory to the path
from app.db.session import get_db_context, engine
from app.db.models import Product, Ingredient, ProductIngredient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IngredientExtractor:
    """Handles extraction of ingredients from products"""
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        
    def generate_ingredient_id(self, name):
        """Generate a stable ID for an ingredient based on its name."""
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
        # Use a fixed namespace for consistency
        namespace = uuid.UUID('12345678-1234-5678-1234-567812345678')
        return str(uuid.uuid5(namespace, clean_name))
    
    def extract_ingredients_from_text(self, ingredients_text):
        """Parse raw ingredients text into individual ingredients."""
        if not ingredients_text or not isinstance(ingredients_text, str):
            return []
            
        # Split by common separators and clean up
        raw_ingredients = []
        for separator in [',', ';', '•', '(', ')', '\n']:
            ingredients_text = ingredients_text.replace(separator, ',')
            
        for ingredient in ingredients_text.split(','):
            # Clean up the ingredient
            ingredient = ingredient.strip()
            
            # Skip if too short or empty
            if not ingredient or len(ingredient) < 3:
                continue
                
            # Add to the list
            raw_ingredients.append(ingredient)
            
        return raw_ingredients
    
    def extract_ingredients_sqlalchemy(self, batch_size=50):
        """Extract ingredients using SQLAlchemy session."""
        logger.info("Starting ingredient extraction using SQLAlchemy")
        total_processed = 0
        total_ingredients = 0
        
        try:
            # Process products in batches
            with get_db_context() as db:
                # Get count of products with ingredients_text
                product_count = db.query(Product).filter(
                    Product.ingredients_text.isnot(None)
                ).count()
                
                logger.info(f"Found {product_count} products with ingredients text")
                
                # Process in batches
                for offset in range(0, product_count, batch_size):
                    products = db.query(Product).filter(
                        Product.ingredients_text.isnot(None)
                    ).offset(offset).limit(batch_size).all()
                    
                    for product in products:
                        try:
                            # Extract ingredients
                            raw_ingredients = self.extract_ingredients_from_text(product.ingredients_text)
                            
                            # Skip if no ingredients found
                            if not raw_ingredients:
                                continue
                                
                            # Process each ingredient
                            for position, ingredient_name in enumerate(raw_ingredients):
                                # Generate ID
                                ingredient_id = self.generate_ingredient_id(ingredient_name)
                                
                                # Check if ingredient exists
                                ingredient = db.query(Ingredient).filter(
                                    Ingredient.id == ingredient_id
                                ).first()
                                
                                # Create if not exists
                                if not ingredient:
                                    ingredient = Ingredient(
                                        id=ingredient_id,
                                        name=ingredient_name
                                    )
                                    db.add(ingredient)
                                
                                # Create relationship if not exists
                                product_ingredient = db.query(ProductIngredient).filter(
                                    ProductIngredient.product_code == product.code,
                                    ProductIngredient.ingredient_id == ingredient_id
                                ).first()
                                
                                if not product_ingredient:
                                    product_ingredient = ProductIngredient(
                                        product_code=product.code,
                                        ingredient_id=ingredient_id,
                                        position=position
                                    )
                                    db.add(product_ingredient)
                                    total_ingredients += 1
                            
                            db.commit()
                            total_processed += 1
                            
                            # Log progress periodically
                            if total_processed % 10 == 0:
                                logger.info(f"Processed {total_processed}/{product_count} products")
                                
                        except Exception as e:
                            db.rollback()
                            logger.error(f"Error processing product {product.code}: {str(e)}")
                            self.error_count += 1
            
            logger.info(f"Completed extraction. Processed {total_processed} products with {total_ingredients} ingredient relationships. Encountered {self.error_count} errors.")
            return total_processed, total_ingredients
            
        except Exception as e:
            logger.error(f"Error in extract_ingredients_sqlalchemy: {str(e)}")
            return 0, 0
    
    async def extract_ingredients_asyncpg(self, batch_size=100):
        """Extract ingredients using asyncpg for better performance."""
        logger.info("Starting ingredient extraction using asyncpg")
        total_processed = 0
        total_ingredients = 0
        
        # Load environment variables for database connection
        load_dotenv()
        db_url = os.getenv('DATABASE_URL')
        
        # Connect to database
        conn = await asyncpg.connect(db_url)
        
        try:
            # Check if the name column has a unique constraint
            has_unique_name = await conn.fetchval(
                """
                SELECT COUNT(*) FROM pg_constraint
                WHERE conrelid = 'ingredients'::regclass 
                AND conname = 'ingredients_name_key'
                """
            )
            
            logger.info(f"Ingredients table has unique name constraint: {bool(has_unique_name)}")
            
            # Get count of products with ingredients_text
            product_count = await conn.fetchval(
                "SELECT COUNT(*) FROM products WHERE ingredients_text IS NOT NULL"
            )
            
            logger.info(f"Found {product_count} products with ingredients text")
            
            # Process in batches
            for offset in range(0, product_count, batch_size):
                products = await conn.fetch(
                    "SELECT code, ingredients_text FROM products WHERE ingredients_text IS NOT NULL ORDER BY code LIMIT $1 OFFSET $2",
                    batch_size, offset
                )
                
                for product in products:
                    try:
                        product_code = product['code']
                        ingredients_text = product['ingredients_text']
                        
                        # Extract ingredients
                        raw_ingredients = self.extract_ingredients_from_text(ingredients_text)
                        
                        # Skip if no ingredients found
                        if not raw_ingredients:
                            continue
                            
                        # Process each ingredient
                        for position, ingredient_name in enumerate(raw_ingredients):
                            # Skip if too short
                            if len(ingredient_name) < 3:
                                continue
                                
                            # Generate ID
                            ingredient_id = self.generate_ingredient_id(ingredient_name)
                            
                            try:
                                # First check if ingredient exists by name
                                existing_id = await conn.fetchval(
                                    "SELECT id FROM ingredients WHERE name = $1", 
                                    ingredient_name
                                )
                                
                                if existing_id:
                                    # Use existing ID
                                    ingredient_id = existing_id
                                else:
                                    # Insert new ingredient
                                    await conn.execute(
                                        """
                                        INSERT INTO ingredients (id, name)
                                        VALUES ($1, $2)
                                        ON CONFLICT DO NOTHING
                                        """,
                                        ingredient_id, ingredient_name
                                    )
                                
                                # Create relationship with appropriate ID
                                await conn.execute(
                                    """
                                    INSERT INTO product_ingredients (product_code, ingredient_id, position)
                                    VALUES ($1, $2, $3)
                                    ON CONFLICT (product_code, ingredient_id) DO NOTHING
                                    """,
                                    product_code, ingredient_id, position
                                )
                                
                                total_ingredients += 1
                            except Exception as ing_error:
                                logger.error(f"Error processing ingredient '{ingredient_name}': {str(ing_error)}")
                                # Continue with next ingredient
                                continue
                        
                        total_processed += 1
                        
                        # Log progress periodically
                        if total_processed % 10 == 0:
                            logger.info(f"Processed {total_processed}/{product_count} products")
                            
                    except Exception as e:
                        logger.error(f"Error processing product {product['code']}: {str(e)}")
                        self.error_count += 1
            
            logger.info(f"Completed extraction. Processed {total_processed} products with {total_ingredients} ingredient relationships. Encountered {self.error_count} errors.")
            return total_processed, total_ingredients
            
        except Exception as e:
            logger.error(f"Error in extract_ingredients_asyncpg: {str(e)}")
            return 0, 0
        finally:
            await conn.close()
    
    def validate_extraction(self):
        """Validate the results of ingredient extraction."""
        logger.info("Validating ingredient extraction")
        
        with get_db_context() as db:
            # Count totals
            product_count = db.query(Product).count()
            ingredient_count = db.query(Ingredient).count()
            relationship_count = db.query(ProductIngredient).count()
            
            # Count products with ingredients
            products_with_ingredients = db.scalar(
                text("SELECT COUNT(DISTINCT product_code) FROM product_ingredients")
            )
            
            # Get sample ingredients
            sample_ingredients = db.query(Ingredient.name).limit(5).all()
            sample_names = [ing[0] for ing in sample_ingredients]
            
            logger.info(f"Validation Results:")
            logger.info(f"  Total products: {product_count}")
            logger.info(f"  Total unique ingredients: {ingredient_count}")
            logger.info(f"  Total product-ingredient relationships: {relationship_count}")
            logger.info(f"  Products with at least one ingredient: {products_with_ingredients}")
            logger.info(f"  Sample ingredients: {', '.join(sample_names)}")
            
            return {
                "product_count": product_count,
                "ingredient_count": ingredient_count,
                "relationship_count": relationship_count,
                "products_with_ingredients": products_with_ingredients,
                "sample_ingredients": sample_names
            }

async def main():
    """Main function to run extraction."""
    try:
        extractor = IngredientExtractor()
        
        # Choose extraction method based on the size of the dataset
        # For smaller datasets, SQLAlchemy is simpler
        # For larger datasets, asyncpg is more efficient
        use_async = True  # Set to True for large datasets
        
        if use_async:
            products_processed, ingredients_added = await extractor.extract_ingredients_asyncpg()
        else:
            products_processed, ingredients_added = extractor.extract_ingredients_sqlalchemy()
        
        # Validate results
        validation_results = extractor.validate_extraction()
        
        logger.info("Ingredient extraction completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 