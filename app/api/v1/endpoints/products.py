"""Product endpoints for the MeatWise API."""

from typing import Any, List, Optional, Dict, Tuple, Union
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import uuid

from app.api.v1 import models
from app.db import models as db_models
from app.db.connection import get_db, get_supabase_client, is_using_local_db
from app.utils import helpers
from app.internal.dependencies import get_current_active_user

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

@router.get("/count", response_model=Dict[str, int])
def get_product_count(
    db: Session = Depends(get_db),
) -> Any:
    """
    Get the total count of products in the database.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, int]: Total count of products
    """
    try:
        logger.info(f"Getting product count (using local DB: {is_using_local_db()})")
        
        try:
            # Try an optimized SQL count that's more efficient than ORM
            from sqlalchemy import text
            result = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
            return {"count": result or 0}
        except Exception as sql_err:
            logger.warning(f"Optimized count failed, falling back to ORM: {str(sql_err)}")
            
            # Fallback to ORM method if direct SQL fails
            try:
                # Count products using a SQL COUNT query through ORM
                total_count = db.query(func.count(db_models.Product.code)).scalar()
                return {"count": total_count or 0}
            except Exception as orm_err:
                logger.warning(f"ORM count failed, trying Supabase direct: {str(orm_err)}")
                
                # Try with Supabase directly as last resort
                if not is_using_local_db():
                    try:
                        with get_supabase_client() as supabase:
                            # Use a more efficient query that doesn't try to count exact records
                            # but instead gets the first 1000 and returns that count
                            response = supabase.table("products").select("code").limit(1000).execute()
                            return {"count": len(response.data), "note": "Approximate count"}
                    except Exception as sb_err:
                        logger.error(f"All count methods failed: {str(sb_err)}")
                        
                # If everything fails, raise the original error
                raise
    except Exception as e:
        logger.error(f"Error getting product count: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting product count: {str(e)}"
        )

@router.get("/", response_model=List[models.Product])
def get_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    risk_rating: Optional[int] = None,
    current_user: db_models.User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve products with optional filtering and preference-based sorting.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        risk_rating: Filter by risk rating
        current_user: Current active user
        
    Returns:
        List[models.Product]: List of products
    """
    try:
        logger.info(f"Getting products (using local DB: {is_using_local_db()})")
        
        # Using SQLAlchemy ORM for either local or production database
        # Build query
        query = db.query(db_models.Product)
        
        if risk_rating is not None:
            query = query.filter(db_models.Product.risk_rating == risk_rating)
            logger.debug("Added risk rating filter")
        
        # Add pagination
        query = query.offset(skip).limit(limit)
        logger.debug("Added pagination")
        
        # Execute query
        products = query.all()
        
        if not products:
            logger.warning("No products found")
            return []
            
        # Convert to Pydantic models
        return [models.Product.from_orm(product) for product in products]
            
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{code}")
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
        logger.info(f"Getting product with code {code} (using local DB: {is_using_local_db()})")
        
        # Query the product from database
        product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
        
        if not product:
            logger.warning(f"Product with code {code} not found")
            raise HTTPException(status_code=404, detail="Product not found")
            
        # Extract additives from ingredients text
        additives = helpers.extract_additives_from_text(product.ingredients_text or "")
        
        # Assess health concerns based on data
        health_concerns = []
        if product.protein and product.protein < 10:
            health_concerns.append("Low protein content")
        if product.fat and product.fat > 25:
            health_concerns.append("High fat content")
        if product.salt and product.salt > 1.5:
            health_concerns.append("High salt content")
            
        # Create basic environmental impact assessment
        env_impact = {
            "impact": "Moderate",
            "details": "Based on default meat product environmental impact assessment",
            "sustainability_practices": ["Unknown"]
        }
        
        if product.meat_type == "beef":
            env_impact["impact"] = "High"
            env_impact["details"] = "Beef production typically has higher environmental impact"
        elif product.meat_type in ["chicken", "turkey"]:
            env_impact["impact"] = "Lower"
            env_impact["details"] = "Poultry typically has lower environmental impact compared to red meat"
        
        # Build structured response
        structured_response = models.ProductStructured(
            product=models.ProductInfo(
                code=product.code,
                name=product.name,
                brand=product.brand,
                description=product.description,
                ingredients_text=product.ingredients_text,
                image_url=product.image_url,
                image_data=product.image_data,
                meat_type=product.meat_type
            ),
            criteria=models.ProductCriteria(
                risk_rating=product.risk_rating,
                additives=additives
            ),
            health=models.ProductHealth(
                nutrition=models.ProductNutrition(
                    calories=product.calories,
                    protein=product.protein,
                    fat=product.fat,
                    carbohydrates=product.carbohydrates,
                    salt=product.salt
                ),
                health_concerns=health_concerns
            ),
            environment=models.ProductEnvironment(
                impact=env_impact["impact"],
                details=env_impact["details"],
                sustainability_practices=env_impact["sustainability_practices"]
            ),
            metadata=models.ProductMetadata(
                last_updated=product.last_updated,
                created_at=product.created_at
            )
        )
        
        return structured_response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving product: {str(e)}"
        )


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
    try:
        logger.debug(f"Checking if product {code} exists in database (using local DB: {is_using_local_db()})")
        
        # Check if product exists
        product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
        
        if not product:
            logger.warning(f"Product with code {code} not found")
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Find alternative products with similar characteristics
        alternatives = (
            db.query(db_models.Product)
            .filter(db_models.Product.meat_type == product.meat_type)
            .filter(db_models.Product.code != code)
            .filter(db_models.Product.risk_rating < product.risk_rating)
            .limit(5)
            .all()
        )
        
        # Convert to alternative product models
        return [
            models.ProductAlternative(
                code=alt.code,
                name=alt.name,
                brand=alt.brand,
                risk_rating=alt.risk_rating,
                reason="Lower risk alternative"
            )
            for alt in alternatives
        ]
                
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing product alternatives: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing product alternatives: {str(e)}"
        )

