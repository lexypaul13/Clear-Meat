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
    
    # Additives and criteria
    contains_nitrites = Column(Boolean, default=False)
    contains_phosphates = Column(Boolean, default=False)
    contains_preservatives = Column(Boolean, default=False)
    
    # Animal welfare criteria
    antibiotic_free = Column(Boolean)
    hormone_free = Column(Boolean)
    pasture_raised = Column(Boolean)
    
    # Risk rating
    risk_rating = Column(String, index=True)
    risk_score = Column(Integer)
    
    # Additional fields
    image_url = Column(String)
    source = Column(String, default="openfoodfacts")
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ingredients = relationship("ProductIngredient", back_populates="product")
    scan_history = relationship("ScanHistory", back_populates="product")
    user_favorites = relationship("UserFavorite", back_populates="product")


class Ingredient(Base):
    """Ingredient model."""
    
    __tablename__ = "ingredients"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text)
    category = Column(String)
    risk_level = Column(String)
    concerns = Column(ARRAY(String), nullable=True)
    alternatives = Column(ARRAY(String), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    products = relationship("ProductIngredient", back_populates="ingredient")


class ProductIngredient(Base):
    """Product-Ingredient relationship model."""
    
    __tablename__ = "product_ingredients"
    
    product_code = Column(String, ForeignKey("products.code", ondelete="CASCADE"), primary_key=True)
    ingredient_id = Column(String, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True)
    position = Column(Integer)
    
    # Relationships
    product = relationship("Product", back_populates="ingredients")
    ingredient = relationship("Ingredient", back_populates="products")


class User(Base):
    """User model that maps to Supabase profiles table."""
    
    __tablename__ = "profiles"
    
    id = Column(String, primary_key=True, index=True)  # This is the Supabase user ID
    email = Column(String, unique=True, index=True, nullable=True)  # Managed by Supabase Auth
    full_name = Column(String, nullable=True)
    
    # Add our application-specific fields to the profiles table
    is_active = Column(Boolean, default=True, nullable=True)
    is_superuser = Column(Boolean, default=False, nullable=True)
    role = Column(String, default="basic", nullable=True)  # basic, contributor, moderator, admin
    
    # User preferences from onboarding
    preferences = Column(JSONB, nullable=True)
    
    # Metadata
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