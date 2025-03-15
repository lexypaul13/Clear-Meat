from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import openfoodfacts
import firebase_admin
from firebase_admin import credentials, auth
from datetime import datetime
import os

# Initialize FastAPI app
app = FastAPI(
    title="Meat Products API",
    description="API for retrieving information about meat products from Open Food Facts",
    version="1.0.0"
)

# Firebase Authentication setup
# Note: In production, use environment variables for the service account path
# cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS_PATH"))
# firebase_admin.initialize_app(cred)

# For development, we'll comment out the Firebase initialization
# Uncomment and configure with your Firebase credentials when ready
# security = HTTPBearer()

# Database setup
# In production, use environment variables for database credentials
DATABASE_URL = "postgresql://username:password@host:5432/meatproducts"
# DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class Product(Base):
    __tablename__ = "products"
    
    code = Column(String, primary_key=True, index=True)
    name = Column(String)
    ingredients = Column(Text)
    
    # Nutritional information
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    carbohydrates = Column(Float, nullable=True)
    salt = Column(Float, nullable=True)
    
    # Meat-specific information
    meat_type = Column(String, index=True)  # beef, chicken, pork, seafood
    
    # Additives and criteria
    contains_nitrites = Column(Boolean, default=False)
    contains_phosphates = Column(Boolean, default=False)
    contains_preservatives = Column(Boolean, default=False)
    
    # Animal welfare criteria
    antibiotic_free = Column(Boolean, nullable=True)
    hormone_free = Column(Boolean, nullable=True)
    pasture_raised = Column(Boolean, nullable=True)
    
    # Risk rating (Green, Yellow, Red)
    risk_rating = Column(String, index=True)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow)
    image_url = Column(String, nullable=True)

# Uncomment to create tables
# Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication dependency
# async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     token = credentials.credentials
#     try:
#         decoded_token = auth.verify_id_token(token)
#         return decoded_token
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Invalid authentication credentials: {e}"
#         )

# API endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to the Meat Products API"}

@app.get("/product/{barcode}")
# async def get_product(barcode: str, user = Depends(verify_token)):
async def get_product(barcode: str):
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

@app.get("/products/search")
# async def search_products(user = Depends(verify_token),
async def search_products(
    meat_type: Optional[str] = Query(None, description="Type of meat (beef, chicken, pork, seafood)"),
    contains_nitrites: Optional[bool] = Query(None, description="Filter by nitrites content"),
    contains_phosphates: Optional[bool] = Query(None, description="Filter by phosphates content"),
    contains_preservatives: Optional[bool] = Query(None, description="Filter by preservatives content"),
    risk_rating: Optional[str] = Query(None, description="Risk rating (Green, Yellow, Red)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
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

@app.get("/products/meat-types")
# async def get_meat_types(user = Depends(verify_token)):
async def get_meat_types():
    """
    Get all available meat types
    """
    return {
        "meat_types": ["beef", "chicken", "pork", "seafood"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 