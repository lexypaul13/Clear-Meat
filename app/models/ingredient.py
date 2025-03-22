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


class Ingredient(IngredientBase):
    """Ingredient response model."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


class AdditiveInfo(BaseModel):
    """Additive information model."""
    name: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None 