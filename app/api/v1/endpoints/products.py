"""Product endpoints for the MeatWise API."""

from typing import Any, List, Optional, Dict, Tuple, Union
import logging
import os
import json
import html
import re
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import uuid

from app.api.v1 import models
from app.db import models as db_models
from app.db.supabase_client import get_supabase_service
from app.db.session import get_db
from app.utils import helpers
from app.internal.dependencies import get_current_active_user
from app.services.recommendation_service import (
    get_personalized_recommendations, analyze_product_match
)
from app.services.health_assessment_mcp_service import HealthAssessmentMCPService
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
    supabase_service = Depends(get_supabase_service),
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
        
        # Perform the search using Supabase service
        results = supabase_service.search_products(sanitized_query, limit=limit, offset=skip)
        
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
        raise HTTPException(
            status_code=500,
            detail="An error occurred while searching products"  # Generic error message
        )

@router.get("/count", response_model=Dict[str, int])
def get_product_count(
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Dict[str, int]:
    """Get total count of products in database."""
    try:
        total = supabase_service.count_products()
        return {"total": total}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.get("/", response_model=List[models.Product])
def get_products(
    supabase_service = Depends(get_supabase_service),
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
        # Get products from Supabase
        products_data = supabase_service.get_products(limit=limit, offset=skip)
        
        # Apply risk rating filter if provided
        if risk_rating is not None:
            risk_rating = risk_rating.strip()
            if risk_rating in ["Green", "Yellow", "Red"]:
                products_data = [p for p in products_data if p.get('risk_rating') == risk_rating]
            
        # Convert to Pydantic models
        result = []
        for product_dict in products_data:
            try:
                product_model = models.Product(
                    code=product_dict.get('code', ''),
                    name=product_dict.get('name', ''),
                    brand=product_dict.get('brand', ''),
                    description=product_dict.get('description', ''),
                    ingredients_text=product_dict.get('ingredients_text', ''),
                    calories=product_dict.get('calories'),
                    protein=product_dict.get('protein'),
                    fat=product_dict.get('fat'),
                    carbohydrates=product_dict.get('carbohydrates'),
                    salt=product_dict.get('salt'),
                    meat_type=product_dict.get('meat_type', ''),
                    risk_rating=product_dict.get('risk_rating', ''),
                    image_url=product_dict.get('image_url', ''),
                    image_data=product_dict.get('image_data', ''),
                    last_updated=product_dict.get('last_updated'),
                    created_at=product_dict.get('created_at')
                )
                result.append(product_model)
            except Exception as e:
                continue
                
        return result
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve products: {str(e)}"
        )

@router.get("/recommendations", response_model=models.RecommendationResponse)
def get_product_recommendations(
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
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
        # Get user preferences
        preferences = getattr(current_user, "preferences", {}) or {}
        if not preferences:
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
                preferences = {
                    "nutrition_focus": "protein",
                    "avoid_preservatives": True,
                    "meat_preferences": ["chicken", "beef", "pork"]
                }
        
        # Get personalized recommendations
        recommended_products = get_personalized_recommendations(db, preferences, limit)
        
        if not recommended_products:
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
                continue
        
        return models.RecommendationResponse(
            recommendations=result,
            total_matches=len(result)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.get("/{code}")
def get_product(
    code: str,
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
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
        # Query the product from Supabase
        product_data = supabase_service.get_product_by_code(code)
        
        if not product_data:
            raise HTTPException(status_code=404, detail="Product not found")
            
        # Extract additives from ingredients text
        additives = helpers.extract_additives_from_text(product_data.get('ingredients_text', '') or "")
        
        # Assess health concerns based on data
        health_concerns = []
        protein = product_data.get('protein')
        fat = product_data.get('fat')
        salt = product_data.get('salt')
        
        if protein and protein < 10:
            health_concerns.append("Low protein content")
        if fat and fat > 25:
            health_concerns.append("High fat content")
        if salt and salt > 1.5:
            health_concerns.append("High salt content")
            
        # Create basic environmental impact assessment
        env_impact = {
            "impact": "Moderate",
            "details": "Based on default meat product environmental impact assessment",
            "sustainability_practices": ["Unknown"]
        }
        
        meat_type = product_data.get('meat_type')
        if meat_type == "beef":
            env_impact["impact"] = "High"
            env_impact["details"] = "Beef production typically has higher environmental impact"
        elif meat_type in ["chicken", "turkey"]:
            env_impact["impact"] = "Lower"
            env_impact["details"] = "Poultry typically has lower environmental impact compared to red meat"
        
        # Build structured response
        structured_response = models.ProductStructured(
            product=models.ProductInfo(
                code=product_data.get('code', ''),
                name=product_data.get('name', ''),
                brand=product_data.get('brand', ''),
                description=product_data.get('description', ''),
                ingredients_text=product_data.get('ingredients_text', ''),
                image_url=product_data.get('image_url', ''),
                image_data=product_data.get('image_data', ''),
                meat_type=product_data.get('meat_type', '')
            ),
            criteria=models.ProductCriteria(
                risk_rating=product_data.get('risk_rating', ''),
                additives=additives
            ),
            health=models.ProductHealth(
                nutrition=models.ProductNutrition(
                    calories=product_data.get('calories'),
                    protein=product_data.get('protein'),
                    fat=product_data.get('fat'),
                    carbohydrates=product_data.get('carbohydrates'),
                    salt=product_data.get('salt')
                ),
                health_concerns=health_concerns
            ),
            environment=models.ProductEnvironment(
                impact=env_impact["impact"],
                details=env_impact["details"],
                sustainability_practices=env_impact["sustainability_practices"]
            ),
            metadata=models.ProductMetadata(
                last_updated=product_data.get('last_updated'),
                created_at=product_data.get('created_at')
            )
        )
        
        return structured_response
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving product: {str(e)}"
        )


@router.get("/{code}/alternatives", response_model=List[models.ProductAlternative])
def get_product_alternatives(
    code: str,
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
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
        # Check if product exists
        product = db.query(db_models.Product).filter(db_models.Product.code == code).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
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
                continue
        
        return result
                
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching alternatives for product {code}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch product alternatives")

@router.get("/{code}/health-assessment-mcp")
async def get_product_health_assessment_mcp(
    code: str,
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Union[models.HealthAssessment, Dict[str, Any]]:
    """
    Generate an evidence-based health assessment using MCP (Model Context Protocol).
    
    This endpoint uses real scientific research to generate micro-reports for ingredients,
    providing evidence-based health assessments instead of hardcoded templates.
    
    Args:
        code: The product's barcode
        supabase_service: Supabase client
        current_user: Currently authenticated user
        
    Returns:
        Evidence-based health assessment with real scientific citations
    """
    logger.info(f"Starting MCP health assessment for product {code}")
    try:
        # Step 1: Fetch product data
        logger.info("Step 1: Fetching product data from Supabase")
        product_data = supabase_service.get_product_by_code(code)
        if not product_data:
            logger.warning(f"Product with code '{code}' not found")
            raise HTTPException(status_code=404, detail=f"Product with code '{code}' not found")
        logger.info("Step 1: Product data fetched successfully")

        # Step 2: Structure product data
        logger.info("Step 2: Structuring product data")
        structured_product = helpers.structure_product_data(product_data)
        if not structured_product:
            logger.error("Failed to structure product data")
            raise HTTPException(status_code=500, detail="Failed to structure product data for assessment")
        logger.info("Step 2: Product data structured successfully")

        # Step 3: Generate MCP-based evidence assessment
        logger.info("Step 3: Generating evidence-based assessment using MCP")
        mcp_service = HealthAssessmentMCPService()
        assessment = await mcp_service.generate_health_assessment_with_real_evidence(structured_product)
        
        if not assessment:
            logger.error("Failed to generate MCP health assessment")
            raise HTTPException(status_code=500, detail="Failed to generate evidence-based health assessment")
        
        logger.info("Step 3: MCP health assessment generated successfully")
        return assessment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in MCP health assessment: {e.__class__.__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during evidence-based assessment")

@router.get("/{code}/debug-mcp")
async def debug_mcp_health_assessment(
    code: str,
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service)
) -> Dict[str, Any]:
    """
    DEBUG ENDPOINT: Shows detailed error information for MCP health assessment.
    TEMPORARY - Will be removed after fixing the main endpoint.
    """
    debug_info = {
        "step": "starting",
        "product_code": code,
        "errors": [],
        "success": False
    }
    
    try:
        # Step 1: Test product data fetch
        debug_info["step"] = "fetching_product_data"
        product_data = supabase_service.get_product_by_code(code)
        if not product_data:
            debug_info["errors"].append(f"Product with code '{code}' not found")
            return debug_info
        debug_info["product_found"] = True
        debug_info["product_name"] = product_data.get('name', 'Unknown')
        
        # Step 2: Test product structuring
        debug_info["step"] = "structuring_product_data"
        structured_product = helpers.structure_product_data(product_data)
        if not structured_product:
            debug_info["errors"].append("Failed to structure product data")
            return debug_info
        debug_info["product_structured"] = True
        debug_info["ingredients"] = structured_product.product.ingredients_text[:100] + "..." if structured_product.product.ingredients_text else "None"
        
        # Step 3: Test MCP service initialization
        debug_info["step"] = "initializing_mcp_service"
        from app.services.health_assessment_mcp_service import HealthAssessmentMCPService
        mcp_service = HealthAssessmentMCPService()
        debug_info["mcp_service_initialized"] = True
        
        # Step 4: Test ingredient categorization
        debug_info["step"] = "categorizing_ingredients"
        basic_categorization = await mcp_service._categorize_ingredients_with_gemini(structured_product)
        if not basic_categorization:
            debug_info["errors"].append("Failed to categorize ingredients")
            return debug_info
        debug_info["categorization_success"] = True
        debug_info["high_risk_ingredients"] = basic_categorization.get('high_risk_ingredients', [])
        debug_info["moderate_risk_ingredients"] = basic_categorization.get('moderate_risk_ingredients', [])
        
        # Step 5: Test assessment generation
        debug_info["step"] = "generating_assessment"
        assessment_result = await mcp_service._generate_evidence_based_assessment(
            structured_product, 
            basic_categorization.get('high_risk_ingredients', []),
            basic_categorization.get('moderate_risk_ingredients', [])
        )
        
        if assessment_result:
            debug_info["assessment_generated"] = True
            debug_info["assessment_summary"] = assessment_result.summary[:100] + "..."
            debug_info["assessment_grade"] = assessment_result.risk_summary.grade
            debug_info["success"] = True
        else:
            debug_info["errors"].append("Assessment generation returned None")
            
        debug_info["step"] = "completed"
        return debug_info
        
    except Exception as e:
        debug_info["errors"].append(f"Exception in step '{debug_info['step']}': {str(e)}")
        debug_info["exception_type"] = e.__class__.__name__
        import traceback
        debug_info["traceback"] = traceback.format_exc()
        return debug_info


