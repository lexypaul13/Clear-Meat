"""Product endpoints for the MeatWise API."""

from typing import Any, List, Optional, Dict, Tuple, Union
import logging
import os
import json
import html
import re

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
from app.services.health_assessment_service import generate_health_assessment, generate_health_assessment_with_citations_option
from app.services.search_service import search_products
from app.utils.personalization import apply_user_preferences

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Input validation patterns  
SAFE_QUERY_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_,.\'"()]+$')
MAX_QUERY_LENGTH = 200

def sanitize_search_query(query: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not query:
        return ""
    
    # Limit query length
    if len(query) > MAX_QUERY_LENGTH:
        query = query[:MAX_QUERY_LENGTH]
    
    # HTML escape to prevent XSS
    query = html.escape(query)
    
    # Remove any remaining HTML tags
    query = re.sub(r'<[^>]*>', '', query)
    
    # Remove script-related keywords
    dangerous_patterns = [
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<script',
        r'</script>',
        r'eval\s*\(',
        r'expression\s*\('
    ]
    
    for pattern in dangerous_patterns:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)
    
    return query.strip()

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
        # Sanitize the search query to prevent XSS and injection attacks
        sanitized_query = sanitize_search_query(q)
        
        # Validate query format
        if not sanitized_query:
            raise HTTPException(
                status_code=400,
                detail="Search query cannot be empty after sanitization"
            )
        
        if not SAFE_QUERY_PATTERN.match(sanitized_query):
            raise HTTPException(
                status_code=400,
                detail="Search query contains invalid characters"
            )
        
        logger.info(f"Natural language search query: '{sanitized_query}'")
        
        # Perform the search using our search service
        results = search_products(sanitized_query, db, limit=limit, skip=skip)
        
        logger.info(f"Found {len(results)} products for query: '{sanitized_query}'")
        
        return {
            "query": sanitized_query,  # Return sanitized query
            "total_results": len(results),
            "limit": limit,
            "skip": skip,
            "products": results
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while searching products"  # Generic error message
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
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return"),
    risk_rating: Optional[str] = Query(None, description="Filter by risk rating (Green, Yellow, Red)"),
    current_user: db_models.User = Depends(get_current_active_user)
) -> List[models.Product]:
    """
    Retrieve products with optional filtering and pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        risk_rating: Filter by risk rating (Green, Yellow, Red)
        current_user: Current active user
        
    Returns:
        List[models.Product]: List of products
    """
    try:
        logger.info(f"Getting products - skip={skip}, limit={limit}, risk_rating={risk_rating}")
        
        # Build the base query
        query = db.query(db_models.Product)
        
        # Apply risk rating filter if provided
        if risk_rating is not None:
            risk_rating = risk_rating.strip()
            if risk_rating in ["Green", "Yellow", "Red"]:
                query = query.filter(db_models.Product.risk_rating == risk_rating)
                logger.info(f"Applied risk rating filter: {risk_rating}")
            else:
                logger.warning(f"Invalid risk rating: {risk_rating}. Ignoring filter.")
        
        # Add ordering for consistent results
        query = query.order_by(db_models.Product.created_at.desc())
        
        # Apply pagination
        if skip > 0:
            query = query.offset(skip)
        if limit > 0:
            query = query.limit(limit)
            
        logger.info(f"Executing query with skip={skip}, limit={limit}")
        
        # Execute the query
        products = query.all()
        logger.info(f"Found {len(products)} products")
            
        # Convert to Pydantic models
        result = []
        for product in products:
            try:
                # Use model_validate for Pydantic v2 or parse_obj for v1
                product_model = models.Product.model_validate({
                    "code": product.code,
                    "name": product.name,
                    "brand": product.brand,
                    "description": product.description,
                    "ingredients_text": product.ingredients_text,
                    "calories": product.calories,
                    "protein": product.protein,
                    "fat": product.fat,
                    "carbohydrates": product.carbohydrates,
                    "salt": product.salt,
                    "meat_type": product.meat_type,
                    "risk_rating": product.risk_rating,
                    "image_url": product.image_url,
                    "image_data": product.image_data,
                    "last_updated": product.last_updated,
                    "created_at": product.created_at
                })
                result.append(product_model)
            except AttributeError:
                # Fallback for Pydantic v1
                try:
                    product_model = models.Product.parse_obj({
                        "code": product.code,
                        "name": product.name,
                        "brand": product.brand,
                        "description": product.description,
                        "ingredients_text": product.ingredients_text,
                        "calories": product.calories,
                        "protein": product.protein,
                        "fat": product.fat,
                        "carbohydrates": product.carbohydrates,
                        "salt": product.salt,
                        "meat_type": product.meat_type,
                        "risk_rating": product.risk_rating,
                        "image_url": product.image_url,
                        "image_data": product.image_data,
                        "last_updated": product.last_updated,
                        "created_at": product.created_at
                    })
                    result.append(product_model)
                except Exception:
                    # Final fallback: direct construction
                    product_model = models.Product(
                        code=product.code,
                        name=product.name,
                        brand=product.brand,
                        description=product.description,
                        ingredients_text=product.ingredients_text,
                        calories=product.calories,
                        protein=product.protein,
                        fat=product.fat,
                        carbohydrates=product.carbohydrates,
                        salt=product.salt,
                        meat_type=product.meat_type,
                        risk_rating=product.risk_rating,
                        image_url=product.image_url,
                        image_data=product.image_data,
                        last_updated=product.last_updated,
                        created_at=product.created_at
                    )
                    result.append(product_model)
            except Exception as e:
                logger.error(f"Error converting product {product.code}: {str(e)}")
                continue
                
        logger.info(f"Successfully converted {len(result)} products to Pydantic models")
        return result
            
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve products: {str(e)}"
        )

@router.get("/recommendations", response_model=models.RecommendationResponse)
def get_product_recommendations(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of recommendations to return"),
) -> models.RecommendationResponse:
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
        
        # If preferences is a string (JSON), parse it
        if isinstance(preferences, str):
            try:
                preferences = json.loads(preferences)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse user preferences JSON: {preferences}")
                preferences = {
                    "nutrition_focus": "protein",
                    "avoid_preservatives": True,
                    "meat_preferences": ["chicken", "beef", "pork"]
                }
        
        logger.info(f"Using preferences: {preferences}")
        
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
            try:
                # Analyze why this product matches preferences
                matches, concerns = analyze_product_match(product, preferences)
                
                # Create Product model using our proven method
                product_model = models.Product(
                    code=product.code,
                    name=product.name,
                    brand=product.brand,
                    description=product.description,
                    ingredients_text=product.ingredients_text,
                    calories=product.calories,
                    protein=product.protein,
                    fat=product.fat,
                    carbohydrates=product.carbohydrates,
                    salt=product.salt,
                    meat_type=product.meat_type,
                    risk_rating=product.risk_rating,
                    image_url=product.image_url,
                    image_data=product.image_data,
                    last_updated=product.last_updated,
                    created_at=product.created_at
                )
                
                # Create RecommendedProduct object
                recommended_product = models.RecommendedProduct(
                    product=product_model,
                    match_details=models.ProductMatch(
                        matches=matches,
                        concerns=concerns
                    ),
                    match_score=None  # We don't expose raw scores to clients
                )
                
                result.append(recommended_product)
                
            except Exception as prod_err:
                logger.error(f"Error processing recommendation for product {product.code}: {str(prod_err)}")
                continue
        
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
) -> List[models.ProductAlternative]:
    """
    Get alternative products for a specific product.
    
    Finds healthier alternatives with lower risk ratings and similar characteristics.
    
    Args:
        code: Product barcode
        db: Database session
        
    Returns:
        List[models.ProductAlternative]: List of alternative products
        
    Raises:
        HTTPException: If product not found
    """
    try:
        logger.info(f"Finding alternatives for product {code}")
        
        # Check if product exists
        product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
        
        if not product:
            logger.warning(f"Product with code {code} not found")
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"Found product: {product.name} (Risk: {product.risk_rating}, Type: {product.meat_type})")
        
        # Define risk rating hierarchy (lower is better)
        risk_hierarchy = {"Green": 1, "Yellow": 2, "Red": 3}
        current_risk_level = risk_hierarchy.get(product.risk_rating, 3)
        
        # Build query for alternatives
        alternatives_query = (
            db.query(db_models.Product)
            .filter(db_models.Product.code != code)  # Exclude the original product
        )
        
        # Add filters for better alternatives
        if product.meat_type:
            alternatives_query = alternatives_query.filter(
                db_models.Product.meat_type == product.meat_type
            )
        
        # Find products with better (lower) risk ratings
        better_risk_ratings = [rating for rating, level in risk_hierarchy.items() 
                              if level < current_risk_level]
        
        if better_risk_ratings:
            alternatives_query = alternatives_query.filter(
                db_models.Product.risk_rating.in_(better_risk_ratings)
            )
        else:
            # If already Green, find similar Green products
            alternatives_query = alternatives_query.filter(
                db_models.Product.risk_rating == product.risk_rating
            )
        
        # Order by risk rating (Green first) and limit results
        alternatives_query = alternatives_query.order_by(
            db_models.Product.risk_rating.asc(),
            db_models.Product.protein.desc()  # Higher protein is better
        ).limit(5)
        
        alternatives = alternatives_query.all()
        logger.info(f"Found {len(alternatives)} alternative products")
        
        # Convert to ProductAlternative models
        result = []
        for alt in alternatives:
            try:
                # Calculate similarity score based on nutritional similarity
                similarity_score = 0.8  # Base score
                
                # Adjust score based on risk improvement
                alt_risk_level = risk_hierarchy.get(alt.risk_rating, 3)
                if alt_risk_level < current_risk_level:
                    similarity_score += 0.2  # Bonus for better risk rating
                
                # Determine reason for recommendation
                if alt.risk_rating != product.risk_rating:
                    reason = f"Better risk rating ({alt.risk_rating} vs {product.risk_rating})"
                else:
                    reason = "Similar nutritional profile with same risk rating"
                
                alternative = models.ProductAlternative(
                    product_code=code,
                    alternative_code=alt.code,
                    similarity_score=similarity_score,
                    reason=reason,
                    alternative=models.Product(
                code=alt.code,
                name=alt.name,
                brand=alt.brand,
                        description=alt.description,
                        ingredients_text=alt.ingredients_text,
                        calories=alt.calories,
                        protein=alt.protein,
                        fat=alt.fat,
                        carbohydrates=alt.carbohydrates,
                        salt=alt.salt,
                        meat_type=alt.meat_type,
                risk_rating=alt.risk_rating,
                        image_url=alt.image_url,
                        image_data=alt.image_data,
                        last_updated=alt.last_updated,
                        created_at=alt.created_at
                    )
                )
                result.append(alternative)
                
            except Exception as conv_err:
                logger.error(f"Error converting alternative {alt.code}: {str(conv_err)}")
                continue
        
        logger.info(f"Successfully created {len(result)} alternative recommendations")
        return result
                
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error processing product alternatives: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to find product alternatives: {str(e)}"
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
) -> models.HealthAssessment:
    """
    Get a comprehensive health assessment for a product with AI insights.
    
    Args:
        code: Product barcode/code
        user_preferences: Optional JSON string of user health preferences
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        HealthAssessment: Detailed health assessment
    """
    try:
        logger.info(f"Generating health assessment for product {code}")
        
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
        
        # Create ProductStructured object as expected by the health assessment service
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
        
        # Build structured response for the health assessment service
        structured_product = models.ProductStructured(
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
        
        # Generate health assessment using the service
        assessment = generate_health_assessment(structured_product, db)
        
        if not assessment:
            raise HTTPException(
                status_code=500,
                detail="Health assessment service unavailable"
            )
        
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

@router.get("/{code}/health-assessment-with-citations", response_model=models.HealthAssessment)
def get_product_health_assessment_with_citations(
    code: str,
    include_citations: bool = Query(default=True, description="Include real scientific citations"),
    user_preferences: Optional[str] = Query(
        None, 
        description="JSON string of user health preferences"
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user)
) -> models.HealthAssessment:
    """
    Get health assessment for a product with real scientific citations.
    
    This endpoint provides enhanced health assessments backed by real scientific
    citations from PubMed and CrossRef databases, eliminating fake citation hallucination.
    
    Args:
        code: Product barcode/identifier
        include_citations: Whether to include real scientific citations (default: True)
        user_preferences: JSON string of user health preferences
        db: Database session
        current_user: Current active user
        
    Returns:
        models.HealthAssessment: Enhanced health assessment with real citations
    """
    try:
        logger.info(f"Getting citation-enhanced health assessment for product {code} (user: {current_user.id})")
        
        # Get product from database
        product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
        if not product:
            logger.warning(f"Product not found: {code}")
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Convert to structured format
        structured_product = helpers.convert_to_structured_product(product)
        
        # Parse user preferences if provided
        parsed_preferences = None
        if user_preferences:
            try:
                parsed_preferences = json.loads(user_preferences)
                logger.info(f"Parsed user preferences: {parsed_preferences}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in user preferences: {user_preferences}")
                # Continue without preferences rather than failing
        
        # Generate assessment with citation option
        assessment = generate_health_assessment_with_citations_option(
            structured_product, 
            db=db, 
            include_citations=include_citations
        )
        
        if not assessment:
            logger.error(f"Failed to generate health assessment for product {code}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to generate health assessment"
            )
        
        # Apply user preferences if provided
        if parsed_preferences:
            assessment = apply_user_preferences(assessment, parsed_preferences)
        
        logger.info(f"Successfully generated citation-enhanced health assessment for product {code}")
        return assessment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in citation-enhanced health assessment for {code}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error generating health assessment"
        )

