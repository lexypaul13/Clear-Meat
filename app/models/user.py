"""User models for the MeatWise API."""

from datetime import datetime
from typing import Dict, List, Optional, Any, ForwardRef, TYPE_CHECKING

from pydantic import BaseModel, EmailStr

# Forward references for circular imports
if TYPE_CHECKING:
    from app.models.product import Product
else:
    Product = ForwardRef("Product")


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
    id: str
    user_id: str
    created_at: datetime
    product: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True 