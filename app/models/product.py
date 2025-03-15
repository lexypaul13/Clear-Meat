from sqlalchemy import Column, String, Float, Boolean, DateTime, Text
from datetime import datetime
from app.database.database import Base

class Product(Base):
    __tablename__ = "products"
    
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    ingredients = Column(Text)
    
    # Nutritional information
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    carbohydrates = Column(Float, nullable=True)
    salt = Column(Float, nullable=True)
    
    # Meat-specific information
    meat_type = Column(String, index=True)  # beef, chicken, pork, seafood
    
    # Additives and criteria
    contains_nitrites = Column(Boolean, default=False)
    contains_phosphates = Column(Boolean, default=False)
    contains_preservatives = Column(Boolean, default=False)
    
    # Animal welfare criteria
    antibiotic_free = Column(Boolean, nullable=True)
    hormone_free = Column(Boolean, nullable=True)
    pasture_raised = Column(Boolean, nullable=True)
    
    # Risk rating (Green, Yellow, Red)
    risk_rating = Column(String, index=True)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow)
    image_url = Column(String, nullable=True) 