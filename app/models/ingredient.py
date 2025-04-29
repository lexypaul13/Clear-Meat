"""Additive information model for the MeatWise API.

This file previously contained ingredient models that were connected to the 
ingredients table in the database. That table has been removed, and now this
file only contains the AdditiveInfo model which is used for structured responses.
"""

from typing import List, Optional
from pydantic import BaseModel


class AdditiveInfo(BaseModel):
    """Additive information model."""
    name: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None 