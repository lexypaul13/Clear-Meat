"""SQLAlchemy models for the MeatWise application."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Product(Base):
    """Product model."""
    
    __tablename__ = "products"
    
    code = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    brand = Column(String)
    description = Column(Text)
    ingredients_text = Column(Text)
    
    # Nutritional information
    calories = Column(Float)
    protein = Column(Float)
    fat = Column(Float)
    carbohydrates = Column(Float)
    salt = Column(Float)
    
    # Meat-specific information
    meat_type = Column(String, index=True)
    
    # Risk rating
    risk_rating = Column(String, index=True)
    
    # Image fields
    image_url = Column(String)
    image_data = Column(Text)
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    scan_history = relationship("ScanHistory", back_populates="product")
    user_favorites = relationship("UserFavorite", back_populates="product")


class User(Base):
    """User model that maps to Supabase profiles table."""
    
    __tablename__ = "profiles"
    
    id = Column(String, primary_key=True, index=True)  # This is the Supabase user ID
    email = Column(String, unique=True, index=True, nullable=True)  # Managed by Supabase Auth
    full_name = Column(String, nullable=True)
    
    # User preferences from onboarding
    preferences = Column(JSONB, nullable=True)
    
    # Metadata (These are likely managed by Supabase Auth triggers/defaults)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    scan_history = relationship("ScanHistory", back_populates="user")
    favorites = relationship("UserFavorite", back_populates="user")


class ScanHistory(Base):
    """Scan history model."""
    
    __tablename__ = "scan_history"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("profiles.id", ondelete="CASCADE"))
    product_code = Column(String, ForeignKey("products.code", ondelete="SET NULL"))
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    location = Column(Text) # JSON stored as text
    device_info = Column(Text)
    personalized_insights = Column(JSONB, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="scan_history")
    product = relationship("Product", back_populates="scan_history")


class UserFavorite(Base):
    """User favorite model."""
    
    __tablename__ = "user_favorites"
    
    user_id = Column(String, ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="user_favorites")


# Placeholder classes for deleted tables - for backwards compatibility
class Ingredient(Base):
    """
    Empty placeholder class for the deleted Ingredient model.
    This exists only for backward compatibility with existing code.
    The actual ingredients table has been removed from the database.
    """
    __tablename__ = "ingredients"  # Table doesn't actually exist anymore
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)


class ProductIngredient(Base):
    """
    Empty placeholder class for the deleted ProductIngredient model.
    This exists only for backward compatibility with existing code.
    The actual product_ingredients table has been removed from the database.
    """
    __tablename__ = "product_ingredients"  # Table doesn't actually exist anymore
    
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    ingredient_id = Column(String, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer)
    
    # Relationship to ingredient
    ingredient = relationship("Ingredient")


# Placeholder classes for tables being removed in this migration (2024-05-15)
class ProductAlternative(Base):
    """
    Empty placeholder class for the deleted ProductAlternative model.
    This exists only for backward compatibility with existing code.
    The actual product_alternatives table has been removed from the database.
    
    Removed on: 2024-05-15
    """
    __tablename__ = "product_alternatives"  # Table doesn't actually exist anymore
    
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    alternative_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    similarity_score = Column(Float)
    reason = Column(String)


class ProductNutrition(Base):
    """
    Empty placeholder class for the deleted ProductNutrition model.
    This exists only for backward compatibility with existing code.
    The actual product_nutrition table has been removed from the database.
    
    Removed on: 2024-05-15
    """
    __tablename__ = "product_nutrition"  # Table doesn't actually exist anymore
    
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    calories = Column(Float)
    protein = Column(Float)
    fat = Column(Float)
    carbohydrates = Column(Float)
    salt = Column(Float)


class PriceHistory(Base):
    """
    Empty placeholder class for the deleted PriceHistory model.
    This exists only for backward compatibility with existing code.
    The actual price_history table has been removed from the database.
    
    Removed on: 2024-05-15
    """
    __tablename__ = "price_history"  # Table doesn't actually exist anymore
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"))
    price = Column(Float)
    currency = Column(String)
    store = Column(String)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class SupplyChain(Base):
    """
    Empty placeholder class for the deleted SupplyChain model.
    This exists only for backward compatibility with existing code.
    The actual supply_chain table has been removed from the database.
    
    Removed on: 2024-05-15
    """
    __tablename__ = "supply_chain"  # Table doesn't actually exist anymore
    
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    origin_country = Column(String)
    processing_location = Column(String)
    distribution_method = Column(String)
    storage_requirements = Column(String)
    shelf_life_days = Column(Integer)
    certifications = Column(ARRAY(String))


class ProductErrors(Base):
    """
    Empty placeholder class for the deleted ProductErrors model.
    This exists only for backward compatibility with existing code.
    The actual product_errors table has been removed from the database.
    
    Removed on: 2024-05-15
    """
    __tablename__ = "product_errors"  # Table doesn't actually exist anymore
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    product_code = Column(String)
    error_type = Column(String)
    error_message = Column(Text)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now()) 