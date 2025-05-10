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
from app.db.session import get_db
from app.db.supabase import get_supabase
from app.utils import helpers
from app.internal.dependencies import get_current_active_user

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

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
        logger.info("Getting products using Supabase")
        supabase = get_supabase()
        
        # Remove sensitive URL logging
        logger.debug("Building Supabase query...")
        
        query = supabase.table('products').select('*')
        
        if risk_rating is not None:
            query = query.eq('risk_rating', risk_rating)
            logger.debug("Added risk rating filter")
        
        # Add pagination
        query = query.range(skip, skip + limit - 1)
        logger.debug("Added pagination")
        
        logger.debug("Executing Supabase query...")
        response = query.execute()
        
        if not response.data:
            logger.warning("No products found")
            return []
            
        # Further filtering and sorting based on user preferences can be applied here
        # after fetching the data from Supabase
        
        preferences = current_user.preferences if current_user else None
        
        if not response.data:
            logger.warning("Supabase returned empty data array")
            # Check if this is due to a connection issue or truly empty data
            test_response = supabase.table("products").select("count").limit(1).execute()
            logger.debug(f"Test query result: {test_response.data}")
            return []
            
        # Convert to Pydantic models
        products = [models.Product(**product) for product in response.data]
        
        # If we have user preferences, we can apply sorting/filtering here
        if preferences:
            # Process products based on preferences
            scored_products = []
            
            # Define threshold values
            REDUCED_SODIUM_THRESHOLD = 0.5
            
            for product in products:
                # Calculate match score
                match_score = 0
                
                # Text to search in
                search_text = (f"{product.name or ''} {product.brand or ''} "
                               f"{product.description or ''} {product.ingredients_text or ''}").lower()
                
                # Apply preference-based scoring similar to the original implementation
                # Q1: Check for preservatives
                if preferences.get('prefer_no_preservatives'):
                    preservative_keywords = ['sorbate', 'benzoate', 'nitrite', 'sulfite', 'bha', 'bht', 'sodium erythorbate']
                    if any(keyword in search_text for keyword in preservative_keywords):
                        match_score -= 1 # Penalize
                    else:
                        match_score += 1 # Reward
                
                # Q2: Check for antibiotic preference
                if preferences.get('prefer_antibiotic_free'):
                    antibiotic_free_keywords = [
                        'antibiotic-free', 'no antibiotics', 'raised without antibiotics', 
                        'never administered antibiotics'
                    ]
                    if any(keyword in search_text for keyword in antibiotic_free_keywords):
                        match_score += 1 # Reward
                
                # Add other preference checks as in the original implementation
                # ...
                
                scored_products.append((match_score, product))
            
            # Sort by score
            scored_products.sort(key=lambda item: item[0], reverse=True)
            return [item[1] for item in scored_products]
        
        return products
            
    except Exception as e:
        logger.error("Error retrieving products")
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
        logger.info(f"Getting product with code {code}")
        supabase = get_supabase()
        
        # Remove sensitive URL logging
        response = supabase.table('products').select('*').eq('code', code).execute()
        
        if not response.data:
            logger.warning(f"Product with code {code} not found")
            raise HTTPException(status_code=404, detail="Product not found")
            
        # Process Supabase product data
        product = response.data[0]
        
        # Extract additives from ingredients text
        additives = helpers.extract_additives_from_text(product.get("ingredients_text", ""))
        
        # Assess health concerns based on Supabase data
        health_concerns = []
        if product.get("protein") and product.get("protein") < 10:
            health_concerns.append("Low protein content")
        if product.get("fat") and product.get("fat") > 25:
            health_concerns.append("High fat content")
        if product.get("salt") and product.get("salt") > 1.5:
            health_concerns.append("High salt content")
            
        # Create basic environmental impact assessment
        env_impact = {
            "impact": "Moderate",
            "details": "Based on default meat product environmental impact assessment",
            "sustainability_practices": ["Unknown"]
        }
        
        if product.get("meat_type") == "beef":
            env_impact["impact"] = "High"
            env_impact["details"] = "Beef production typically has higher environmental impact"
        elif product.get("meat_type") in ["chicken", "turkey"]:
            env_impact["impact"] = "Lower"
            env_impact["details"] = "Poultry typically has lower environmental impact compared to red meat"
        
        # Build structured response from Supabase data
        structured_response = models.ProductStructured(
            product=models.ProductInfo(
                code=product.get("code", ""),
                name=product.get("name", "Unknown Product"),
                brand=product.get("brand", "Unknown Brand"),
                description=product.get("description", ""),
                ingredients_text=product.get("ingredients_text", ""),
                image_url=product.get("image_url", ""),
                image_data=product.get("image_data", ""),
                meat_type=product.get("meat_type", "")
            ),
            criteria=models.ProductCriteria(
                risk_rating=product.get("risk_rating", ""),
                additives=additives  # Now using additive info extracted from text
            ),
            health=models.ProductHealth(
                nutrition=models.ProductNutrition(
                    calories=product.get("calories"),
                    protein=product.get("protein"),
                    fat=product.get("fat"),
                    carbohydrates=product.get("carbohydrates"),
                    salt=product.get("salt")
                ),
                health_concerns=health_concerns
            ),
            environment=models.ProductEnvironment(
                impact=env_impact["impact"],
                details=env_impact["details"],
                sustainability_practices=env_impact["sustainability_practices"]
            ),
            metadata=models.ProductMetadata(
                last_updated=product.get("last_updated"),
                created_at=product.get("created_at")
            )
        )
        
        return structured_response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("Error retrieving product")
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
        # Add debug logging
        logger.debug(f"Checking if product {code} exists in Supabase")
        
        # Get Supabase client
        supabase = get_supabase()
        
        # First check if product exists
        product_response = supabase.table("products").select("code").eq("code", code).execute()
        
        if not product_response.data or len(product_response.data) == 0:
            logger.warning(f"Product with code {code} not found in Supabase")
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Product exists in Supabase - return empty alternatives list
        # The product_alternatives table has been removed
        logger.info(f"Product {code} exists, but product_alternatives table has been removed. Returning empty list.")
        return []
                
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error processing product alternatives: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing product alternatives: {str(e)}"
        )

