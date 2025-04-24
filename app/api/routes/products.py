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
    price: float
    image_url: Optional[str] = None
    nutrition: dict
    description: str

class ProductCreate(ProductBase):
    """Product creation model."""
    pass

class Product(ProductBase):
    """Product model with ID."""
    id: int

    class Config:
        """Pydantic config."""
        from_attributes = True

@router.get("/products", response_model=List[Product])
async def get_products(
    search: Optional[str] = None,
    meat_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """Get all products with optional filtering."""
    try:
        supabase = get_supabase()
        query = supabase.table('products').select('*')
        
        if search:
            query = query.ilike('name', f'%{search}%')
        if meat_type:
            query = query.eq('meat_type', meat_type)
        if min_price is not None:
            query = query.gte('price', min_price)
        if max_price is not None:
            query = query.lte('price', max_price)
            
        response = query.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """Get a single product by ID."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').select('*').eq('id', product_id).single().execute()
        
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

@router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product: ProductCreate):
    """Update a product."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').update(
            product.dict()
        ).eq('id', product_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/products/{product_id}")
async def delete_product(product_id: int):
    """Delete a product."""
    try:
        supabase = get_supabase()
        response = supabase.table('products').delete().eq('id', product_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        return {"message": "Product deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 