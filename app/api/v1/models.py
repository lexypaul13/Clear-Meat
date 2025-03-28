"""Pydantic models for the MeatWise API."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, EmailStr


# Ingredient models
class IngredientBase(BaseModel):
    """Base Ingredient model."""
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class IngredientCreate(IngredientBase):
    """Ingredient creation model."""
    pass


class Ingredient(IngredientBase):
    """Ingredient response model."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


# Product models
class ProductBase(BaseModel):
    """Base Product model."""
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    ingredients_text: Optional[str] = None
    
    # Nutritional information
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None
    
    # Meat-specific information
    meat_type: Optional[str] = None
    
    # Additives and criteria
    contains_nitrites: Optional[bool] = False
    contains_phosphates: Optional[bool] = False
    contains_preservatives: Optional[bool] = False
    
    # Animal welfare criteria
    antibiotic_free: Optional[bool] = None
    hormone_free: Optional[bool] = None
    pasture_raised: Optional[bool] = None
    
    # Risk rating
    risk_rating: Optional[str] = None
    risk_score: Optional[int] = None
    
    # Additional fields
    image_url: Optional[str] = None
    source: Optional[str] = "openfoodfacts"


class ProductCreate(ProductBase):
    """Product creation model."""
    code: str


class ProductUpdate(ProductBase):
    """Product update model."""
    pass


class ProductInDB(ProductBase):
    """Product database model."""
    code: str
    last_updated: datetime
    created_at: datetime


class Product(ProductInDB):
    """Product response model."""
    ingredients: Optional[List[Ingredient]] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


class ProductAlternative(BaseModel):
    """Product alternative model."""
    product_code: str
    alternative_code: str
    similarity_score: float
    reason: Optional[str] = None
    alternative: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# User models
class UserBase(BaseModel):
    """Base User model."""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserUpdate(UserBase):
    """User update model."""
    password: Optional[str] = None


class User(UserBase):
    """User response model."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


# Token models
class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str
    message: Optional[str] = None


class TokenPayload(BaseModel):
    """Token payload model."""
    sub: Optional[str] = None


# Scan history models
class ScanHistoryBase(BaseModel):
    """Base Scan History model."""
    product_code: str
    location: Optional[Dict[str, Any]] = None
    device_info: Optional[str] = None


class ScanHistoryCreate(ScanHistoryBase):
    """Scan History creation model."""
    pass


class ScanHistory(ScanHistoryBase):
    """Scan History response model."""
    id: str
    user_id: str
    scanned_at: datetime
    product: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# User favorite models
class UserFavoriteBase(BaseModel):
    """Base User Favorite model."""
    product_code: str
    notes: Optional[str] = None


class UserFavoriteCreate(UserFavoriteBase):
    """User Favorite creation model."""
    pass


class UserFavorite(UserFavoriteBase):
    """User Favorite response model."""
    user_id: str
    added_at: datetime
    product: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# Structured product response models
class ProductNutrition(BaseModel):
    """Nutrition information model."""
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None


class AdditiveInfo(BaseModel):
    """Additive information model."""
    name: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class ProductCriteria(BaseModel):
    """Product criteria model."""
    risk_rating: Optional[str] = None
    risk_score: Optional[int] = None
    contains_nitrites: Optional[bool] = False
    contains_phosphates: Optional[bool] = False
    contains_preservatives: Optional[bool] = False
    antibiotic_free: Optional[bool] = None
    hormone_free: Optional[bool] = None
    pasture_raised: Optional[bool] = None
    additives: Optional[List[AdditiveInfo]] = None


class ProductHealth(BaseModel):
    """Product health model."""
    nutrition: Optional[ProductNutrition] = None
    health_concerns: Optional[List[str]] = None


class ProductEnvironment(BaseModel):
    """Product environment model."""
    impact: Optional[str] = None
    details: Optional[str] = None
    sustainability_practices: Optional[List[str]] = None


class ProductInfo(BaseModel):
    """Basic product information model."""
    code: str
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    ingredients_text: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = "openfoodfacts"
    meat_type: Optional[str] = None


class ProductMetadata(BaseModel):
    """Product metadata model."""
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ProductStructured(BaseModel):
    """Structured product response model."""
    product: ProductInfo
    criteria: ProductCriteria
    health: ProductHealth
    environment: ProductEnvironment
    metadata: ProductMetadata


# Problem report models
class ProductProblemReport(BaseModel):
    """Product problem report model."""
    problem_type: str = Field(..., description="Type of problem (incorrect_info, missing_info, other)")
    description: str = Field(..., description="Description of the problem")
    reporter_email: Optional[EmailStr] = Field(None, description="Email of the person reporting the problem")
    want_feedback: Optional[bool] = Field(False, description="Whether the reporter wants to be contacted about the resolution")
    report_id: Optional[str] = None 