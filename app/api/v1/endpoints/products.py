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
from app.db.supabase_client import get_supabase
from app.utils import helpers
from supabase import create_client
from app.internal.dependencies import get_current_active_user

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter()

@router.get("/", response_model=List[models.Product])
def get_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    risk_rating: Optional[str] = None,
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
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    try:
        # Try Supabase first for testing mode
        if is_testing:
            try:
                # Add debug logging
                logger.debug("Getting products using Supabase in testing mode")
                
                # Get Supabase client and add detailed logging
                supabase = get_supabase()
                logger.debug(f"Supabase URL being used: {supabase.supabase_url}")
                
                # Build and log the query
                query = supabase.table("products").select("*")
                logger.debug("Building Supabase query...")
                
                # Apply filters
                if risk_rating:
                    query = query.eq("risk_rating", risk_rating)
                    logger.debug(f"Added risk_rating filter: {risk_rating}")
                    
                # Apply pagination
                # Note: Supabase doesn't directly support skip, but we'll use limit+offset
                query = query.range(skip, skip + limit - 1)
                logger.debug(f"Added pagination: range({skip}, {skip + limit - 1})")
                
                # Execute query and log
                logger.debug("Executing Supabase query...")
                response = query.execute()
                logger.debug(f"Supabase response count: {len(response.data) if response.data else 0}")
                
                if response.data:
                    # Convert to Pydantic models
                    return [models.Product(**product) for product in response.data]
                else:
                    logger.warning("Supabase returned empty data array")
                    # Check if this is due to a connection issue or truly empty data
                    # Try a simple test query to confirm connection
                    test_response = supabase.table("products").select("count").limit(1).execute()
                    logger.debug(f"Test query result: {test_response.data}")
                    return []
            except Exception as e:
                # In testing mode, return empty list rather than falling back to SQLAlchemy
                logger.error(f"Supabase error in testing mode: {str(e)}")
                return []
        
        # Normal SQLAlchemy path for non-testing mode
        logger.debug("Getting products using SQLAlchemy")
        try:

            # Build the base query
            query = db.query(db_models.Product)
            
            # Apply standard filters
            # --- Apply meat type filter based on preferences first ---
            preferences = current_user.preferences if current_user else None
            if preferences and preferences.get('preferred_meat_types'):
                preferred_types = preferences['preferred_meat_types']
                if preferred_types: # Ensure list is not empty
                    query = query.filter(db_models.Product.meat_type.in_(preferred_types))
            
            # --- Apply other standard filters ---
            # Removed meat_type filter here as it's handled above
            # if meat_type:
            #     query = query.filter(db_models.Product.meat_type == meat_type)
            if risk_rating:
                query = query.filter(db_models.Product.risk_rating == risk_rating)
            
            # Get products from database with pagination
            db_products = query.offset(skip).limit(limit).all()

            # Convert to Pydantic models and apply preference sorting/filtering if applicable
            result = []
            # preferences = current_user.preferences if current_user else None # Already defined above

            # Define sodium threshold (e.g., grams per 100g) - adjust as needed
            REDUCED_SODIUM_THRESHOLD = 0.5 

            for db_product in db_products:
                product_model = models.Product(
                    code=db_product.code,
                    name=db_product.name,
                    brand=db_product.brand,
                    description=db_product.description,
                    ingredients_text=db_product.ingredients_text,
                    calories=db_product.calories,
                    protein=db_product.protein,
                    fat=db_product.fat,
                    carbohydrates=db_product.carbohydrates,
                    salt=db_product.salt,
                    meat_type=db_product.meat_type,
                    risk_rating=db_product.risk_rating,
                    image_url=db_product.image_url,
                    image_data=db_product.image_data,
                    last_updated=db_product.last_updated,
                    created_at=db_product.created_at,
                    ingredients=[]
                )
                
                # Calculate match score if preferences exist
                match_score = 0
                if preferences:
                    search_text = (f"{db_product.name or ''} {db_product.brand or ''} "
                                   f"{db_product.description or ''} {db_product.ingredients_text or ''}").lower()

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

                    # Q3: Check for hormone preference
                    if preferences.get('prefer_hormone_free'):
                        hormone_free_keywords = ['hormone-free', 'no added hormones', 'no hormones administered']
                        if any(keyword in search_text for keyword in hormone_free_keywords):
                            match_score += 1 # Reward

                    # Q4: Check for added sugars
                    if preferences.get('prefer_no_added_sugars'):
                        # Check ingredients list primarily
                        ingredients_lower = (db_product.ingredients_text or '').lower()
                        sugar_keywords = [
                            'sugar', 'syrup', 'dextrose', 'fructose', 'sucrose', 'maltodextrin', 
                            'corn syrup solids', 'brown sugar' # Add more as needed
                        ]
                        if any(keyword in ingredients_lower for keyword in sugar_keywords):
                            match_score -= 1 # Penalize
                        else:
                            match_score += 1 # Reward
                            
                    # Q5: Check for flavor enhancers (MSG)
                    if preferences.get('prefer_no_flavor_enhancers'):
                        enhancer_keywords = ['monosodium glutamate', 'msg', 'hydrolyzed', 'autolyzed yeast extract'] # Add more as needed
                        if any(keyword in search_text for keyword in enhancer_keywords):
                            match_score -= 1 # Penalize
                        else:
                            match_score += 1 # Reward
                            
                    # Q6: Check for reduced sodium (based on value)
                    if preferences.get('prefer_reduced_sodium') and product_model.salt is not None:
                        if product_model.salt < REDUCED_SODIUM_THRESHOLD:
                            match_score += 1 # Reward if below threshold
                        # Optional: Penalize if significantly above threshold?
                        # elif product_model.salt > HIGH_SODIUM_THRESHOLD:
                        #    match_score -= 1

                    # --- Removed Old Preference Logic ---
                    # if preferences.get('prefer_grass_fed'):
                    #    grass_fed_keywords = ['grass-fed', 'grass fed', 'pasture-raised']
                    #    if any(keyword in search_text for keyword in grass_fed_keywords):
                    #        match_score += 1 # Reward if keywords found

                    # --- TODO: Refine scoring weights? ---

                result.append((match_score, product_model))

            # Sort by score if preferences were applied
            if preferences:
                result.sort(key=lambda item: item[0], reverse=True)
                # Extract only the product models after sorting
                final_products = [item[1] for item in result]
            else:
                # No preferences, just return the models in DB order
                final_products = [item[1] for item in result]
                
            return final_products

        except Exception as sqlalchemy_error:
            logger.error(f"SQLAlchemy query failed: {sqlalchemy_error}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail=f"SQLAlchemy query failed: {str(sqlalchemy_error)}"
            )
    except Exception as e:
        # Log the error
        logger.error(f"Error retrieving products: {str(e)}")
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
        except Exception as e:
            # Log the Supabase error and continue to try SQLAlchemy
            logger.error(f"Supabase error: {str(e)}")
            
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
        
        # Extract additives from ingredients text
        additives = helpers.extract_additives_from_text(product.ingredients_text)
        
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
        logger.error(f"Error processing product data: {str(e)}")
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
        logger.error(f"Supabase error when reporting problem: {str(e)}")
        
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
            # Product exists in Supabase - return empty alternatives list
            # The product_alternatives table has been removed
            logger.info(f"Product {code} exists, but product_alternatives table has been removed. Returning empty list.")
            return []
                
    except Exception as e:
        # Log Supabase error
        logger.error(f"Supabase error when getting alternatives: {str(e)}")
        
        # In testing mode, return empty list instead of trying SQLAlchemy
        if is_testing:
            return []
    
    # Fall back to SQLAlchemy database
    product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Return empty list since product_alternatives table has been removed
    logger.info(f"Product {code} exists in SQLAlchemy, but product_alternatives table has been removed. Returning empty list.")
    return []


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
        logger.error(f"Error retrieving product from Supabase: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve product: {str(e)}"
        ) 