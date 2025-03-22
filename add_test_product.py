#!/usr/bin/env python3

"""Script to add a test product to the database."""

import sys
from datetime import datetime

sys.path.append(".")  # Add the current directory to the path

from app.db.session import SessionLocal
from app.db import models

def add_test_product():
    """Add a test product to the database."""
    db = SessionLocal()
    
    try:
        # Check if product already exists
        existing_product = db.query(models.Product).filter(models.Product.code == "1234567890123").first()
        if existing_product:
            print(f"Product with code 1234567890123 already exists: {existing_product.name}")
            return
        
        # Create a new test product
        test_product = models.Product(
            code="1234567890123",
            name="Test Beef Product",
            brand="MeatWise Test",
            description="A test product for the MeatWise API",
            ingredients_text="Beef, salt, spices, preservatives (E250, E251)",
            
            # Nutritional information
            calories=250.5,
            protein=20.3,
            fat=15.7,
            carbohydrates=0.5,
            salt=1.8,
            
            # Meat-specific information
            meat_type="beef",
            
            # Additives and criteria
            contains_nitrites=True,
            contains_phosphates=True,
            contains_preservatives=True,
            
            # Animal welfare criteria
            antibiotic_free=False,
            hormone_free=False,
            pasture_raised=False,
            
            # Risk rating
            risk_rating="Red",
            risk_score=8,
            
            # Additional fields
            image_url="https://example.com/test-product.jpg",
            source="test",
            
            # Metadata
            last_updated=datetime.now(),
            created_at=datetime.now()
        )
        
        db.add(test_product)
        db.commit()
        print("Test product added successfully!")
        
    except Exception as e:
        print(f"Error adding test product: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_product() 