"""Product endpoints for the MeatWise API."""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1 import models
from app.db import models as db_models
from app.db.session import get_db
from app.utils import helpers

router = APIRouter()


@router.get("/", response_model=List[models.Product])
def get_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    meat_type: Optional[str] = None,
    risk_rating: Optional[str] = None,
    contains_nitrites: Optional[bool] = None,
    contains_phosphates: Optional[bool] = None,
    contains_preservatives: Optional[bool] = None,
) -> Any:
    """
    Retrieve products with optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        meat_type: Filter by meat type
        risk_rating: Filter by risk rating
        contains_nitrites: Filter by nitrites content
        contains_phosphates: Filter by phosphates content
        contains_preservatives: Filter by preservatives content
        
    Returns:
        List[models.Product]: List of products
    """
    query = db.query(db_models.Product)
    
    # Apply filters
    if meat_type:
        query = query.filter(db_models.Product.meat_type == meat_type)
    if risk_rating:
        query = query.filter(db_models.Product.risk_rating == risk_rating)
    if contains_nitrites is not None:
        query = query.filter(db_models.Product.contains_nitrites == contains_nitrites)
    if contains_phosphates is not None:
        query = query.filter(db_models.Product.contains_phosphates == contains_phosphates)
    if contains_preservatives is not None:
        query = query.filter(db_models.Product.contains_preservatives == contains_preservatives)
    
    return query.offset(skip).limit(limit).all()


@router.get("/{code}", response_model=models.Product)
def get_product(
    code: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific product by barcode.
    
    Args:
        code: Product barcode
        db: Database session
        
    Returns:
        models.Product: Product details
        
    Raises:
        HTTPException: If product not found
    """
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/{code}/alternatives", response_model=List[models.ProductAlternative])
def get_product_alternatives(
    code: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get alternative products for a specific product.
    
    Args:
        code: Product barcode
        db: Database session
        
    Returns:
        List[models.ProductAlternative]: List of alternative products
        
    Raises:
        HTTPException: If product not found
    """
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    alternatives = (
        db.query(db_models.ProductAlternative)
        .filter(db_models.ProductAlternative.product_code == code)
        .all()
    )
    
    return alternatives


@router.post("/", response_model=models.Product)
def create_product(
    product_in: models.ProductCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Create a new product.
    
    Args:
        product_in: Product data
        db: Database session
        
    Returns:
        models.Product: Created product
        
    Raises:
        HTTPException: If product already exists
    """
    product = db.query(db_models.Product).filter(db_models.Product.code == product_in.code).first()
    if product:
        raise HTTPException(status_code=400, detail="Product already exists")
    
    # Calculate risk score and rating if not provided
    if product_in.risk_score is None or product_in.risk_rating is None:
        risk_score = helpers.calculate_risk_score(product_in)
        risk_rating = helpers.get_risk_rating(risk_score)
        product_in.risk_score = risk_score
        product_in.risk_rating = risk_rating
    
    product = db_models.Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{code}", response_model=models.Product)
def update_product(
    code: str,
    product_in: models.ProductUpdate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Update a product.
    
    Args:
        code: Product barcode
        product_in: Updated product data
        db: Database session
        
    Returns:
        models.Product: Updated product
        
    Raises:
        HTTPException: If product not found
    """
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_in.model_dump(exclude_unset=True)
    
    # Calculate risk score and rating if relevant fields were updated
    risk_related_fields = [
        "contains_nitrites", "contains_phosphates", "contains_preservatives",
        "antibiotic_free", "hormone_free", "pasture_raised"
    ]
    
    if any(field in update_data for field in risk_related_fields):
        # Create a merged product for risk calculation
        merged_data = {**product.__dict__, **update_data}
        merged_product = models.ProductBase(**merged_data)
        
        risk_score = helpers.calculate_risk_score(merged_product)
        risk_rating = helpers.get_risk_rating(risk_score)
        
        update_data["risk_score"] = risk_score
        update_data["risk_rating"] = risk_rating
    
    for key, value in update_data.items():
        setattr(product, key, value)
    
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{code}")
def delete_product(
    code: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Delete a product.
    
    Args:
        code: Product barcode
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If product not found
    """
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"} 