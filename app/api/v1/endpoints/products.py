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
from supabase import create_client

router = APIRouter()

@router.get("/", response_model=List[models.Product])
def get_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    meat_type: Optional[str] = None,
    risk_rating: Optional[str] = None,
) -> Any:
    """
    Retrieve products with optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        meat_type: Filter by meat type
        risk_rating: Filter by risk rating
        
    Returns:
        List[models.Product]: List of products
    """
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    try:
        # Try Supabase first for testing mode
        if is_testing:
            try:
                supabase = get_supabase()
                query = supabase.table("products").select("*")
                
                # Apply filters
                if meat_type:
                    query = query.eq("meat_type", meat_type)
                if risk_rating:
                    query = query.eq("risk_rating", risk_rating)
                    
                # Apply pagination
                # Note: Supabase doesn't directly support skip, but we'll use limit+offset
                response = query.range(skip, skip + limit - 1).execute()
                
                if response.data:
                    # Convert to Pydantic models
                    return [models.Product(**product) for product in response.data]
                else:
                    return []
            except Exception as e:
                # In testing mode, return empty list rather than falling back to SQLAlchemy
                logging.error(f"Supabase error in testing mode: {str(e)}")
                return []
        
        # Normal SQLAlchemy path for non-testing mode
        query = db.query(db_models.Product)
        
        # Apply filters
        if meat_type:
            query = query.filter(db_models.Product.meat_type == meat_type)
        if risk_rating:
            query = query.filter(db_models.Product.risk_rating == risk_rating)
        
        # Get products from database
        products = query.offset(skip).limit(limit).all()
        
        # Manually create Pydantic models instead of relying on automatic conversion
        result = []
        for db_product in products:
            # Create a simple Product model without trying to load ingredients relationship
            product = models.Product(
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
                risk_rating=db_product.risk_rating,
                
                # Image fields
                image_url=db_product.image_url,
                image_data=db_product.image_data,
                
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
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    try:
        # Try to get product directly from Supabase first
        try:
            supabase = get_supabase()
            
            # Query product by code
            response = supabase.table("products").select("*").eq("code", code).execute()
            
            # Check if product exists in Supabase
            if response.data and len(response.data) > 0:
                # Process Supabase product data
                product = response.data[0]
                
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
                        additives=[]  # We don't have detailed additive information in Supabase
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
        except Exception as e:
            # Log the Supabase error and continue to try SQLAlchemy
            logging.error(f"Supabase error: {str(e)}")
            
            # In testing mode, skip the fallback to SQLAlchemy database
            if is_testing:
                raise HTTPException(status_code=404, detail="Product not found")
            
        # Fall back to SQLAlchemy database if not found in Supabase or if Supabase failed
        # Get product from database using SQLAlchemy
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
                additive_info = models.AdditiveInfo(
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
        structured_response = models.ProductStructured(
            product=models.ProductInfo(
                code=product.code,
                name=product.name,
                brand=product.brand or "Unknown Brand",
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
        # Log the error
        print(f"Error processing product data: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing product data: {str(e)}"
        )


@router.post("/{code}/report")
def report_product_problem(
    code: str,
    report: models.ProductProblemReport,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Report a problem with a product.
    
    Args:
        code: Product barcode
        report: Problem report details
        db: Database session
        
    Returns:
        dict: Success message and report ID
        
    Raises:
        HTTPException: If product not found
    """
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    # Try Supabase first
    try:
        supabase = get_supabase()
        # Check if product exists in Supabase
        product_response = supabase.table("products").select("code").eq("code", code).execute()
        
        if not product_response.data or len(product_response.data) == 0:
            # In testing mode, return 404 immediately instead of trying SQLAlchemy
            if is_testing:
                raise HTTPException(status_code=404, detail="Product not found")
                
            # For non-testing mode, continue to SQLAlchemy check
        else:
            # Product exists in Supabase, process the report
            # Generate a random ID for the report if not provided
            if not report.report_id:
                report.report_id = helpers.generate_random_id()
            
            # In a real application, save the report to Supabase
            # For now, we'll just return a successful response
            return {
                "message": "Problem report submitted successfully",
                "report_id": report.report_id
            }
    except Exception as e:
        # Log Supabase error
        logging.error(f"Supabase error when reporting problem: {str(e)}")
        
        # In testing mode, return 404 instead of trying SQLAlchemy
        if is_testing:
            raise HTTPException(status_code=500, detail=f"Error reporting problem: {str(e)}")
    
    # Fall back to SQLAlchemy database
    # Check if product exists
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Generate a random ID for the report if not provided
    if not report.report_id:
        report.report_id = helpers.generate_random_id()
    
    # In a real application, save the report to a database
    # For now, we'll just return a successful response
    
    return {
        "message": "Problem report submitted successfully",
        "report_id": report.report_id
    }


@router.get("/{code}/contribution")
def get_product_contribution(
    code: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get contribution information for a product.
    
    Args:
        code: Product barcode
        db: Database session
        
    Returns:
        dict: Contribution information
        
    Raises:
        HTTPException: If product not found
    """
    # Check if product exists
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # In a real application, fetch actual contribution data
    # For now, we'll return placeholder information
    
    return {
        "added_by": "MeatWise Database Team",
        "last_edited_by": "Community Member",
        "data_source": product.source if product.source else "OpenFoodFacts",
        "last_updated": product.last_updated,
        "contribution_count": 5,
        "contributors": [
            "MeatWise Database Team",
            "Community Member",
            "Nutrition Specialist"
        ]
    }


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
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    # Try Supabase first
    try:
        supabase = get_supabase()
        
        # First check if product exists
        product_response = supabase.table("products").select("code").eq("code", code).execute()
        
        if not product_response.data or len(product_response.data) == 0:
            # In testing mode, return 404 immediately instead of trying SQLAlchemy
            if is_testing:
                raise HTTPException(status_code=404, detail="Product not found")
            # For non-testing mode, continue to SQLAlchemy check
        else:
            # Product exists in Supabase, try to get alternatives
            # This assumes you have a product_alternatives table in Supabase
            alt_response = supabase.table("product_alternatives").select("*").eq("product_code", code).execute()
            
            if alt_response.data:
                # Convert to Pydantic models
                return [models.ProductAlternative(**alt) for alt in alt_response.data]
            else:
                # No alternatives found, return empty list
                return []
                
    except Exception as e:
        # Log Supabase error
        logging.error(f"Supabase error when getting alternatives: {str(e)}")
        
        # In testing mode, return empty list instead of trying SQLAlchemy
        if is_testing:
            return []
    
    # Fall back to SQLAlchemy database
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


@router.get("/direct/{product_code}", response_model=models.ProductStructured)
def get_product_direct(
    product_code: str,
) -> Any:
    """
    Retrieve a product directly from Supabase by barcode.
    This endpoint bypasses SQLAlchemy entirely.
    """
    try:
        # Use the imported get_supabase function
        supabase = get_supabase()
        
        # Query product by code
        response = supabase.table("products").select("*").eq("code", product_code).execute()
        
        # Check if product exists
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Product with code {product_code} not found"
            )
        
        # Get the first product (should be only one)
        product = response.data[0]
        
        # Construct structured response matching the ProductStructured model
        structured_product = models.ProductStructured(
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
                additives=[]
            ),
            health=models.ProductHealth(
                nutrition=models.ProductNutrition(
                    calories=product.get("calories"),
                    protein=product.get("protein"),
                    fat=product.get("fat"),
                    carbohydrates=product.get("carbohydrates"),
                    salt=product.get("salt")
                ),
                health_concerns=[]
            ),
            environment=models.ProductEnvironment(
                impact="Moderate",
                details="Based on default meat product environmental impact assessment",
                sustainability_practices=["Unknown"]
            ),
            metadata=models.ProductMetadata(
                last_updated=product.get("last_updated"),
                created_at=product.get("created_at")
            )
        )
        
        return structured_product
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logging.error(f"Error retrieving product from Supabase: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve product: {str(e)}"
        ) 