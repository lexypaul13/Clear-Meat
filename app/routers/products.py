"""Product router for the MeatWise API."""

from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models import (
    Product, ProductStructured, 
    AdditiveInfo
)
from app.db import models as db_models
from app.db.session import get_db
from app.utils import helpers

router = APIRouter()


@router.get("/", response_model=List[Product])
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
    try:
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
        
        # Get products from database
        products = query.offset(skip).limit(limit).all()
        
        # Manually create Pydantic models instead of relying on automatic conversion
        result = []
        for db_product in products:
            # Create a simple Product model without trying to load ingredients relationship
            product = Product(
                code=db_product.code,
                name=db_product.name,
                brand=db_product.brand,
                description=db_product.description,
                ingredients_text=db_product.ingredients_text,
                
                # Nutritional information
                calories=db_product.calories,
                protein=db_product.protein,
                fat=db_product.fat,
                carbohydrates=db_product.carbohydrates,
                salt=db_product.salt,
                
                # Meat-specific information
                meat_type=db_product.meat_type,
                
                # Additives and criteria
                contains_nitrites=db_product.contains_nitrites,
                contains_phosphates=db_product.contains_phosphates,
                contains_preservatives=db_product.contains_preservatives,
                
                # Animal welfare criteria
                antibiotic_free=db_product.antibiotic_free,
                hormone_free=db_product.hormone_free,
                pasture_raised=db_product.pasture_raised,
                
                # Risk rating
                risk_rating=db_product.risk_rating,
                risk_score=db_product.risk_score,
                
                # Additional fields
                image_url=db_product.image_url,
                source=db_product.source,
                
                # Timestamps
                last_updated=db_product.last_updated,
                created_at=db_product.created_at,
                
                # Empty ingredients list to avoid complex relationship loading
                ingredients=[]
            )
            result.append(product)
        
        return result
    except Exception as e:
        # Log the error
        print(f"Error retrieving products: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving products: {str(e)}"
        )


@router.get("/{code}", response_model=ProductStructured)
def get_product(
    code: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific product by barcode with a structured response format.
    
    Args:
        code: Product barcode
        db: Database session
        
    Returns:
        dict: Structured product details
        
    Raises:
        HTTPException: If product not found or if there's an error processing the data
    """
    try:
        # Get product from database
        product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Verify required fields for ProductInfo
        if not product.name:
            # Add a default name if missing
            product.name = "Unknown Product"
        
        # Get ingredients
        ingredients_query = (
            db.query(db_models.ProductIngredient)
            .filter(db_models.ProductIngredient.product_code == code)
            .join(db_models.Ingredient)
            .all()
        )
        
        # Prepare additives information
        additives = []
        for product_ingredient in ingredients_query:
            ingredient = product_ingredient.ingredient
            if ingredient and hasattr(ingredient, 'category') and ingredient.category in ["preservative", "additive", "stabilizer", "flavor enhancer"]:
                additive_info = AdditiveInfo(
                    name=ingredient.name if hasattr(ingredient, 'name') else "Unknown",
                    category=ingredient.category if hasattr(ingredient, 'category') else None,
                    risk_level=ingredient.risk_level if hasattr(ingredient, 'risk_level') else None,
                    concerns=ingredient.concerns if hasattr(ingredient, 'concerns') else None,
                    alternatives=ingredient.alternatives if hasattr(ingredient, 'alternatives') else None
                )
                additives.append(additive_info)
        
        # Assess health concerns
        health_concerns = helpers.assess_health_concerns(product)
        
        # Assess environmental impact
        env_impact = helpers.assess_environmental_impact(product)
        
        # Build structured response
        from app.models.product import ProductStructured, ProductInfo, ProductCriteria, ProductHealth, ProductEnvironment, ProductMetadata, ProductNutrition
        
        structured_response = ProductStructured(
            product=ProductInfo(
                code=product.code,
                name=product.name,
                brand=product.brand or "Unknown Brand",
                description=product.description,
                ingredients_text=product.ingredients_text,
                image_url=product.image_url,
                source=product.source,
                meat_type=product.meat_type
            ),
            criteria=ProductCriteria(
                risk_rating=product.risk_rating,
                risk_score=product.risk_score,
                contains_nitrites=product.contains_nitrites,
                contains_phosphates=product.contains_phosphates,
                contains_preservatives=product.contains_preservatives,
                antibiotic_free=product.antibiotic_free,
                hormone_free=product.hormone_free,
                pasture_raised=product.pasture_raised,
                additives=additives
            ),
            health=ProductHealth(
                nutrition=ProductNutrition(
                    calories=product.calories,
                    protein=product.protein,
                    fat=product.fat,
                    carbohydrates=product.carbohydrates,
                    salt=product.salt
                ),
                health_concerns=health_concerns
            ),
            environment=ProductEnvironment(
                impact=env_impact["impact"],
                details=env_impact["details"],
                sustainability_practices=env_impact["sustainability_practices"]
            ),
            metadata=ProductMetadata(
                last_updated=product.last_updated,
                created_at=product.created_at
            )
        )
        
        return structured_response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error for debugging
        print(f"Error processing product {code}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing product data: {str(e)}"
        ) 