from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
import openfoodfacts

from app.database.database import get_db
from app.models.product import Product
from app.schemas.product import Product as ProductSchema
from app.schemas.product import ProductSearch
from app.utils.auth import verify_token

router = APIRouter(
    prefix="/products",
    tags=["products"],
    # dependencies=[Depends(verify_token)],  # Uncomment when ready to use authentication
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[ProductSchema])
async def search_products(
    meat_type: Optional[str] = Query(None, description="Type of meat (beef, chicken, pork, seafood)"),
    contains_nitrites: Optional[bool] = Query(None, description="Filter by nitrites content"),
    contains_phosphates: Optional[bool] = Query(None, description="Filter by phosphates content"),
    contains_preservatives: Optional[bool] = Query(None, description="Filter by preservatives content"),
    risk_rating: Optional[str] = Query(None, description="Risk rating (Green, Yellow, Red)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
    # user = Depends(verify_token)  # Uncomment when ready to use authentication
):
    """
    Search for meat products with various filters
    """
    # This would normally query the database
    # For now, we'll return a placeholder response
    return {
        "message": "Search functionality will be implemented with database integration",
        "filters": {
            "meat_type": meat_type,
            "contains_nitrites": contains_nitrites,
            "contains_phosphates": contains_phosphates,
            "contains_preservatives": contains_preservatives,
            "risk_rating": risk_rating
        },
        "pagination": {
            "page": page,
            "page_size": page_size
        }
    }

@router.get("/{barcode}", response_model=ProductSchema)
async def get_product(
    barcode: str, 
    db: Session = Depends(get_db)
    # user = Depends(verify_token)  # Uncomment when ready to use authentication
):
    """
    Get detailed information about a specific product by barcode
    """
    product = openfoodfacts.products.get_product(barcode)
    if product.get('status') == 1:
        # Extract relevant information
        product_data = product.get('product', {})
        return {
            "product_name": product_data.get("product_name"),
            "ingredients": product_data.get("ingredients_text"),
            "nutritional_info": product_data.get("nutriments"),
            "image_url": product_data.get("image_url")
        }
    else:
        raise HTTPException(status_code=404, detail="Product not found")

@router.get("/meat-types", response_model=List[str])
async def get_meat_types(
    db: Session = Depends(get_db)
    # user = Depends(verify_token)  # Uncomment when ready to use authentication
):
    """
    Get all available meat types
    """
    return {
        "meat_types": ["beef", "chicken", "pork", "seafood"]
    } 