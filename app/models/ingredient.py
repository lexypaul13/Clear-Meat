"""Ingredient models for the MeatWise API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


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


class IngredientUpdate(BaseModel):
    """Ingredient update model."""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class Ingredient(IngredientBase):
    """Ingredient response model."""
    id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {
            # Handle SQLAlchemy UUID objects
            "UUID": lambda v: str(v),
        }
    }


class AdditiveInfo(BaseModel):
    """Additive information model."""
    name: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None 