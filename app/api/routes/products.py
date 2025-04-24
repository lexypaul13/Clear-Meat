from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# Create router
router = APIRouter()

# Models
class Nutrition(BaseModel):
    protein: str
    fat: str
    calories: int

class Product(BaseModel):
    id: int
    name: str
    meat_type: str
    price: float
    image_url: str
    nutrition: Nutrition
    description: str

# Mock product data
mock_products = [
    {
        "id": 1,
        "name": "Premium Beef Steak",
        "meat_type": "Beef",
        "price": 15.99,
        "image_url": "https://images.openfoodfacts.org/images/products/327/408/000/5003/front_en.648.400.jpg",
        "nutrition": {
            "protein": "25g",
            "fat": "15g",
            "calories": 280
        },
        "description": "Premium quality beef steak from grass-fed cows. Perfect for grilling or pan-searing."
    },
    {
        "id": 2,
        "name": "Organic Chicken Breast",
        "meat_type": "Poultry",
        "price": 8.99,
        "image_url": "https://images.openfoodfacts.org/images/products/000/000/000/9875/front_en.4.400.jpg",
        "nutrition": {
            "protein": "22g",
            "fat": "3g",
            "calories": 165
        },
        "description": "Organic chicken breast from free-range chickens. Low in fat and high in protein."
    },
    {
        "id": 3,
        "name": "Grass-fed Ground Beef",
        "meat_type": "Beef",
        "price": 7.99,
        "image_url": "https://images.openfoodfacts.org/images/products/843/704/349/1158/front_en.7.400.jpg",
        "nutrition": {
            "protein": "20g",
            "fat": "18g",
            "calories": 250
        },
        "description": "Ground beef from grass-fed cows. Perfect for burgers, meatballs, or any recipe calling for ground beef."
    },
    {
        "id": 4,
        "name": "Pork Tenderloin",
        "meat_type": "Pork",
        "price": 9.99,
        "image_url": "https://images.openfoodfacts.org/images/products/376/020/616/4542/front_fr.93.400.jpg",
        "nutrition": {
            "protein": "26g",
            "fat": "4g",
            "calories": 170
        },
        "description": "Lean and tender pork tenderloin. Great for roasting or grilling."
    },
    {
        "id": 5,
        "name": "Lamb Chops",
        "meat_type": "Lamb",
        "price": 18.99,
        "image_url": "https://images.openfoodfacts.org/images/products/500/015/940/4953/front_fr.56.400.jpg",
        "nutrition": {
            "protein": "20g",
            "fat": "12g",
            "calories": 210
        },
        "description": "Premium lamb chops from grass-fed lambs. Perfect for grilling or roasting."
    },
    {
        "id": 6,
        "name": "Turkey Breast",
        "meat_type": "Poultry",
        "price": 6.99,
        "image_url": "https://images.openfoodfacts.org/images/products/309/264/039/8690/front_fr.24.400.jpg",
        "nutrition": {
            "protein": "24g",
            "fat": "1g",
            "calories": 120
        },
        "description": "Lean turkey breast. Low in fat and high in protein."
    },
    {
        "id": 7,
        "name": "Duck Breast",
        "meat_type": "Duck",
        "price": 12.99,
        "image_url": "https://images.openfoodfacts.org/images/products/20135750/front_en.7.400.jpg",
        "nutrition": {
            "protein": "19g",
            "fat": "12g",
            "calories": 180
        },
        "description": "Premium duck breast. Rich in flavor and perfect for special occasions."
    },
    {
        "id": 8,
        "name": "Venison Steak",
        "meat_type": "Venison",
        "price": 22.99,
        "image_url": "https://images.openfoodfacts.org/images/products/20168144/front_en.4.400.jpg",
        "nutrition": {
            "protein": "26g",
            "fat": "2g",
            "calories": 150
        },
        "description": "Lean venison steak. Low in fat and high in protein with a rich, gamey flavor."
    },
    {
        "id": 9,
        "name": "Turkey Burgers",
        "meat_type": "Poultry",
        "price": 5.99,
        "image_url": "https://images.openfoodfacts.org/images/products/00222629/front_en.3.400.jpg",
        "nutrition": {
            "protein": "20g",
            "fat": "8g",
            "calories": 160
        },
        "description": "Lean turkey burgers. A healthier alternative to beef burgers."
    }
]

@router.get("/", response_model=List[Product])
async def get_products(
    search: Optional[str] = Query(None, description="Search query"),
    meat_type: Optional[str] = Query(None, description="Filter by meat type"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price")
):
    """Get a list of products with optional filtering"""
    filtered_products = mock_products
    
    # Filter by search query
    if search:
        filtered_products = [p for p in filtered_products 
                            if search.lower() in p["name"].lower()]
    
    # Filter by meat type
    if meat_type and meat_type.lower() != "all":
        filtered_products = [p for p in filtered_products 
                            if p["meat_type"].lower() == meat_type.lower()]
    
    # Filter by price range
    if min_price is not None:
        filtered_products = [p for p in filtered_products 
                            if p["price"] >= min_price]
    
    if max_price is not None:
        filtered_products = [p for p in filtered_products 
                            if p["price"] <= max_price]
    
    return filtered_products

@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """Get a single product by ID"""
    for product in mock_products:
        if product["id"] == product_id:
            return product
    
    raise HTTPException(status_code=404, detail="Product not found") 