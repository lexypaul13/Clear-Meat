"""Product router for the MeatWise API."""

from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models import (
    Product, ProductStructured
)
from app.models.ingredient import AdditiveInfo
from app.db import models as db_models
from app.db.supabase_client import get_supabase_service
from app.db.session import get_db
from app.utils import helpers
from app.services.ai_service import generate_personalized_insights
from app.internal.dependencies import get_current_user_optional

router = APIRouter()


@router.get("/", response_model=List[Product])
def get_products(
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
    current_user: Optional[db_models.User] = Depends(get_current_user_optional),
    skip: int = 0,
    limit: int = 100,
    meat_type: Optional[str] = None,
    risk_rating: Optional[str] = None,
) -> Any:
    """
    Retrieve products with optional filtering.
    
    Args:
        db: Database session
        current_user: Optional current user for personalized filtering
        skip: Number of records to skip
        limit: Maximum number of records to return
        meat_type: Filter by meat type
        risk_rating: Filter by risk rating
        
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
        
        # Apply user preference-based filtering if user is logged in and has preferences
        if current_user and hasattr(current_user, "preferences") and current_user.preferences:
            preferences = current_user.preferences
            
            # Example: Filter by dietary goal
            if preferences.get("dietary_goal") == "keto":
                # For keto, prioritize high-protein, low-carb options
                query = query.order_by(db_models.Product.protein.desc())
        
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
                
                # Risk rating
                risk_rating=getattr(db_product, 'risk_rating', None),
                
                # Additional fields
                image_url=db_product.image_url,
                
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
    supabase_service = Depends(get_supabase_service),
    current_user: Optional[db_models.User] = Depends(get_current_user_optional),
) -> Any:
    """
    Get a specific product by barcode with a structured response format.
    
    Args:
        code: Product barcode
        db: Database session
        current_user: Optional current user for personalized insights
        
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
        
        # Additives information is now determined through analysis of ingredients_text
        # rather than from the database, since the ingredients table is gone
        additives = []
        if product.ingredients_text:
            # Extract additives from ingredients text
            additive_info = helpers.extract_additives_from_text(product.ingredients_text)
            additives = additive_info or []
        
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
                image_data=product.image_data,
                meat_type=product.meat_type
            ),
            criteria=ProductCriteria(
                risk_rating=getattr(product, 'risk_rating', None),
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
        
        # Add personalized insights if user is logged in and has preferences
        if current_user and hasattr(current_user, "preferences") and current_user.preferences:
            personalized_insights = generate_personalized_insights(product, current_user.preferences)
            structured_response.personalized_insights = personalized_insights
        
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


 