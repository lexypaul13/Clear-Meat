#!/usr/bin/env python
"""Script to add a test product that matches our criteria."""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the current directory to the path so we can import app modules
sys.path.append('.')

from app.db.models import Product, Base

# Load environment variables
load_dotenv()

def add_test_product():
    """Add a test product that matches our criteria."""
    try:
        # Get database URL from environment
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            print("No DATABASE_URL found in environment variables")
            return False
            
        # Create SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create a test product
        test_product = Product(
            code="test123456789",
            name="Organic Pasture-Raised Chicken Breast",
            brand="FarmFresh Organics",
            description="Premium pasture-raised, antibiotic-free chicken breast",
            ingredients_text="Chicken breast",
            calories=120.0,
            protein=26.0,
            fat=2.5,
            carbohydrates=0.0,
            salt=0.2,
            meat_type="chicken",
            contains_nitrites=False,
            contains_phosphates=False,
            contains_preservatives=False,
            antibiotic_free=True,
            hormone_free=True,
            pasture_raised=True,
            risk_rating="Green",
            risk_score=10,
            image_url="https://example.com/images/chicken_breast.jpg",
            source="test",
            last_updated=datetime.now(),
            created_at=datetime.now()
        )
        
        # Add the product
        session.add(test_product)
        session.commit()
        
        print(f"Added test product: {test_product.name}")
        return True
    except Exception as e:
        print(f"Error adding test product: {str(e)}")
        return False

if __name__ == "__main__":
    add_test_product() 