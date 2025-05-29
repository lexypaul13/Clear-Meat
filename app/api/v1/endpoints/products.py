"""Product endpoints for the MeatWise API."""

from typing import Any, List, Optional, Dict, Tuple, Union
import logging
import os
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import uuid

from app.api.v1 import models
from app.db import models as db_models
from app.db.connection import get_db, get_supabase_client, is_using_local_db
from app.utils import helpers
from app.internal.dependencies import get_current_active_user
from app.services.recommendation_service import (
    get_personalized_recommendations, analyze_product_match
)
from app.services.health_assessment_service import generate_health_assessment
from app.services.search_service import search_products
from app.utils.personalization import apply_user_preferences

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# NEW: Dedicated natural language search endpoint - placed at the top to avoid conflicts
@router.get("/nlp-search", response_model=Dict[str, Any])
def natural_language_search(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Search for products using natural language queries.
    
    Examples:
    - "Low sodium chicken snacks"
    - "High protein beef jerky with no sugar"  
    - "Healthy turkey-based alternatives"
    - "Organic grass-fed beef"
    - "Antibiotic-free chicken breast"
    
    Args:
        q: Natural language search query
        limit: Maximum number of results to return (1-100, default 20)
        skip: Number of results to skip for pagination
        db: Database session
        
    Returns:
        Dict containing search results and metadata
    """
    try:
        logger.info(f"Natural language search query: '{q}'")
        
        # Perform the search using our search service
        results = search_products(q, db, limit=limit, skip=skip)
        
        logger.info(f"Found {len(results)} products for query: '{q}'")
        
        return {
            "query": q,
            "total_results": len(results),
            "limit": limit,
            "skip": skip,
            "products": results
        }
        
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching products: {str(e)}"
        )

@router.get("/count", response_model=Dict[str, int])
def get_product_count(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Dict[str, int]:
    """Get total count of products in database."""
    try:
        total = db.query(db_models.Product).count()
        logger.info(f"Product count request: {total} products (user: {current_user.id})")
        return {"total": total}
    except Exception as e:
        logger.error(f"Error getting product count: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
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

@router.get("/recommendations", response_model=models.RecommendationResponse)
def get_product_recommendations(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of recommendations to return"),
) -> Any:
    """
    Get personalized product recommendations based on user preferences.
    
    Recommendations are tailored based on the preferences set during the user onboarding process,
    including nutrition focus, additives, ethical concerns, and preferred meat types.
    
    Args:
        db: Database session
        current_user: Current active user
        limit: Maximum number of recommendations to return (1-100, default 30)
        
    Returns:
        RecommendationResponse: List of recommended products with match details
    """
    try:
        logger.info(f"Generating personalized recommendations for user {current_user.id}")
        
        # Get user preferences
        preferences = getattr(current_user, "preferences", {}) or {}
        if not preferences:
            logger.warning(f"User {current_user.id} has no preferences set. Using defaults.")
            preferences = {
                # Default preferences if none are set
                "nutrition_focus": "protein",
                "avoid_preservatives": True,
                "meat_preferences": ["chicken", "beef", "pork"]
            }
        
        # Get personalized recommendations
        recommended_products = get_personalized_recommendations(db, preferences, limit)
        
        if not recommended_products:
            logger.warning("No recommendations found")
            return models.RecommendationResponse(
                recommendations=[],
                total_matches=0
            )
        
        # Build response with match details
        result = []
        for product in recommended_products:
            # Analyze why this product matches preferences
            matches, concerns = analyze_product_match(product, preferences)
            
            # Create RecommendedProduct object
            recommended_product = models.RecommendedProduct(
                product=models.Product.from_orm(product),
                match_details=models.ProductMatch(
                    matches=matches,
                    concerns=concerns
                ),
                match_score=None  # We don't expose raw scores to clients
            )
            
            result.append(recommended_product)
        
        logger.info(f"Returning {len(result)} personalized recommendations")
        
        return models.RecommendationResponse(
            recommendations=result,
            total_matches=len(result)
        )
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.get("/{code}/health-assessment", response_model=models.HealthAssessment)
def get_product_health_assessment(
    code: str,
    user_preferences: Optional[str] = Query(
        None, 
        description="JSON string of user health preferences"
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get a comprehensive health assessment for a product with AI insights.
    
    Args:
        code: Product barcode/code
        user_preferences: Optional JSON string of user health preferences
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dict containing detailed health assessment
    """
    try:
        # Get the product
        product = db.query(db_models.Product).filter(
            db_models.Product.code == code
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with code {code} not found"
            )
        
        # Parse user preferences if provided
        parsed_preferences = None
        if user_preferences:
            try:
                parsed_preferences = json.loads(user_preferences)
            except json.JSONDecodeError:
                logger.warning(f"Invalid user preferences JSON: {user_preferences}")
        
        # Generate health assessment using the service
        assessment = generate_health_assessment(product, parsed_preferences)
        
        # Log successful assessment generation
        logger.info(f"Generated health assessment for product {code} (user: {current_user.id})")
        
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating health assessment for product {code}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating health assessment: {str(e)}"
        )

