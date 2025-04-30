"""User models for the MeatWise API."""

from datetime import datetime
from typing import Dict, List, Optional, Any, ForwardRef, TYPE_CHECKING, Union

from pydantic import BaseModel, EmailStr

# Import Product model properly
if TYPE_CHECKING:
    from app.models.product import Product
else:
    Product = ForwardRef("Product")


class UserPreferences(BaseModel):
    """User preferences from onboarding."""
    # Screen 1: Nutrition Priorities
    nutrition_focus: Optional[str] = None  # "protein", "fat", "salt"
    
    # Screen 2: Additives and Preservatives
    avoid_preservatives: Optional[bool] = None  # True/False
    
    # Screen 3: Antibiotics and Hormones in Raising
    prefer_antibiotic_free: Optional[bool] = None  # True/False
    
    # Screen 4: Sourcing & Animal Diet
    prefer_grass_fed: Optional[bool] = None  # True/False
    
    # Screen 5: Typical Cooking Style
    cooking_style: Optional[str] = None  # "grilling", "pan_frying", "oven_slow_cooker"
    
    # Screen 6: Openness to Meat Alternatives
    open_to_alternatives: Optional[bool] = None  # True/False
    
    # Keeping legacy fields for backward compatibility
    health_goal: Optional[str] = None  
    sourcing_preference: Optional[str] = None
    ethical_concerns: Optional[List[str]] = None
    additive_preference: Optional[str] = None
    dietary_goal: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nutrition_focus": "protein",
                    "avoid_preservatives": True,
                    "prefer_antibiotic_free": True,
                    "prefer_grass_fed": True,
                    "cooking_style": "grilling",
                    "open_to_alternatives": False
                }
            ]
        }
    }


class UserBase(BaseModel):
    """Base User model with common fields."""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    role: Optional[str] = "basic"


class UserCreate(UserBase):
    """User creation model with password field."""
    password: str


class UserUpdate(BaseModel):
    """User update model for partial updates."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role: Optional[str] = None
    preferences: Optional[UserPreferences] = None


class User(UserBase):
    """User response model with ID and timestamps."""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    preferences: Optional[UserPreferences] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# Token models
class Token(BaseModel):
    """Token model for authentication responses."""
    access_token: str
    token_type: str
    message: Optional[str] = None


class TokenPayload(BaseModel):
    """Token payload model for JWT contents."""
    sub: Optional[str] = None


# Scan history models
class ScanHistoryBase(BaseModel):
    """Base Scan History model with common fields."""
    product_code: str
    location: Optional[Union[Dict[str, Any], str]] = None
    device_info: Optional[str] = None


class ScanHistoryCreate(ScanHistoryBase):
    """Scan History creation model."""
    pass


class ScanHistory(ScanHistoryBase):
    """Scan History response model with ID, user_id and timestamps."""
    id: str
    user_id: str
    scanned_at: datetime
    product: Optional["Product"] = None
    personalized_insights: Optional[Dict[str, Any]] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {
            # Handle SQLAlchemy UUID objects
            "UUID": lambda v: str(v),
        }
    }


# User favorite models
class UserFavoriteBase(BaseModel):
    """Base User Favorite model with common fields."""
    product_code: str
    notes: Optional[str] = None


class UserFavoriteCreate(UserFavoriteBase):
    """User Favorite creation model."""
    pass


class UserFavorite(UserFavoriteBase):
    """User Favorite response model with user_id and timestamps."""
    user_id: str
    added_at: datetime
    product: Optional["Product"] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {
            # Handle SQLAlchemy UUID objects
            "UUID": lambda v: str(v),
        }
    }


# Update forward references
from app.models.product import Product
ScanHistory.model_rebuild()
UserFavorite.model_rebuild() 