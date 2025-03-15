from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    ingredients: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None
    meat_type: str
    contains_nitrites: Optional[bool] = False
    contains_phosphates: Optional[bool] = False
    contains_preservatives: Optional[bool] = False
    antibiotic_free: Optional[bool] = None
    hormone_free: Optional[bool] = None
    pasture_raised: Optional[bool] = None
    risk_rating: Optional[str] = None
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    code: str

class Product(ProductBase):
    code: str
    last_updated: datetime
    
    class Config:
        orm_mode = True

class ProductSearch(BaseModel):
    meat_type: Optional[str] = None
    contains_nitrites: Optional[bool] = None
    contains_phosphates: Optional[bool] = None
    contains_preservatives: Optional[bool] = None
    risk_rating: Optional[str] = None
    page: int = 1
    page_size: int = 20 