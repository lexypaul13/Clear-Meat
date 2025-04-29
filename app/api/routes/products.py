"""Product routes for the MeatWise API."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.db.supabase import get_supabase

router = APIRouter()

class ProductBase(BaseModel):
    """Base product model."""
    name: str
    meat_type: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None

class ProductCreate(ProductBase):
    """Product creation model."""
    code: str

class Product(ProductBase):
    """Product model with code."""
    code: str
    brand: Optional[str] = None
    ingredients_text: Optional[str] = None
    risk_rating: Optional[str] = None
    image_data: Optional[str] = None

    class Config:
        """Pydantic config."""
        from_attributes = True

@router.get("/products", response_model=List[Product])
async def get_products(
    search: Optional[str] = None,
    meat_type: Optional[str] = None,
    risk_rating: Optional[str] = None
):
    """Get all products with optional filtering."""
    try:
        supabase = get_supabase()
        query = supabase.table('products').select('*')
        
        if search:
            query = query.ilike('name', f'%{search}%')
        if meat_type:
            query = query.eq('meat_type', meat_type)
        if risk_rating:
            query = query.eq('risk_rating', risk_rating)
            
        response = query.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products/{code}", response_model=Product)
async def get_product(code: str):
    """Get a single product by code."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').select('*').eq('code', code).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    """Create a new product."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').insert(product.dict()).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/products/{code}", response_model=Product)
async def update_product(code: str, product: ProductBase):
    """Update a product."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').update(
            product.dict()
        ).eq('code', code).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/products/{code}")
async def delete_product(code: str):
    """Delete a product."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').delete().eq('code', code).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return {"message": "Product deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 