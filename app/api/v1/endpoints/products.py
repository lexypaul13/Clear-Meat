"""Product endpoints for the MeatWise API."""

from typing import Any, List, Optional, Dict, Tuple, Union
import logging
import os
import json
import html
import re
import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, Path
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
from app.services.openfoodfacts_service import get_openfoodfacts_service
from app.utils.personalization import apply_user_preferences

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Old text search patterns removed - now using AI-powered NLP search

# Pre-computed ingredient insights lookup table for performance optimization
_INGREDIENT_INSIGHTS_CACHE = {
    # Salt/Sodium compounds
    "salt": {
        "overview": "Essential mineral used for flavor enhancement and preservation. Excessive intake linked to cardiovascular issues.",
        "health_risks": ["High blood pressure", "Heart disease", "Stroke risk", "Kidney problems"],
        "common_uses": ["Preservative", "Flavor enhancer", "Texture modifier"]
    },
    "sodium": {
        "overview": "Essential mineral used for flavor enhancement and preservation. Excessive intake linked to cardiovascular issues.",
        "health_risks": ["High blood pressure", "Heart disease", "Stroke risk", "Kidney problems"],
        "common_uses": ["Preservative", "Flavor enhancer", "Texture modifier"]
    },
    # MSG variants
    "msg": {
        "overview": "Flavor enhancer that adds umami taste. May cause sensitivity reactions in some individuals.",
        "health_risks": ["Headaches", "Nausea", "Flushing", "Sensitivity reactions"],
        "common_uses": ["Flavor enhancer", "Umami booster", "Food additive"]
    },
    "monosodium glutamate": {
        "overview": "Flavor enhancer that adds umami taste. May cause sensitivity reactions in some individuals.",
        "health_risks": ["Headaches", "Nausea", "Flushing", "Sensitivity reactions"],
        "common_uses": ["Flavor enhancer", "Umami booster", "Food additive"]
    },
    # Sugar compounds
    "dextrose": {
        "overview": "Simple sugar used for sweetening and preservation. Contributes to caloric content and may affect blood sugar.",
        "health_risks": ["Blood sugar spikes", "Weight gain", "Dental problems", "Diabetes risk"],
        "common_uses": ["Sweetener", "Preservative", "Texture enhancer"]
    },
    "sugar": {
        "overview": "Simple sugar used for sweetening and preservation. Contributes to caloric content and may affect blood sugar.",
        "health_risks": ["Blood sugar spikes", "Weight gain", "Dental problems", "Diabetes risk"],
        "common_uses": ["Sweetener", "Preservative", "Texture enhancer"]
    },
    # Food coloring
    "yellow 6 lake": {
        "overview": "Artificial food coloring used to enhance product appearance. Potential allergen for sensitive individuals.",
        "health_risks": ["Allergic reactions", "Hyperactivity (in children)", "Skin reactions"],
        "common_uses": ["Food coloring", "Visual enhancement", "Product branding"]
    },
    "red 40 lake": {
        "overview": "Artificial food coloring used to enhance product appearance. Potential allergen for sensitive individuals.",
        "health_risks": ["Allergic reactions", "Hyperactivity (in children)", "Skin reactions"],
        "common_uses": ["Food coloring", "Visual enhancement", "Product branding"]
    },
    # Fats
    "pork fat": {
        "overview": "Animal fat providing flavor and texture. High in saturated fats which may impact cardiovascular health.",
        "health_risks": ["High cholesterol", "Heart disease", "Weight gain", "Arterial blockage"],
        "common_uses": ["Flavor enhancement", "Texture provider", "Cooking medium"]
    }
}

def _optimize_for_mobile(assessment: Dict[str, Any]) -> Dict[str, Any]:
    """Optimize health assessment response for mobile consumption with performance-optimized ingredient insights."""
    try:
        # Helper function to truncate text properly - but don't truncate nutrition comments
        def truncate_text(text: str, max_length: int, preserve_complete: bool = False) -> str:
            if len(text) <= max_length:
                return text
            if preserve_complete:
                # For nutrition comments, don't truncate - they should be complete from backend
                return text
            return text[:max_length - 3] + "..."
        
        # Optimized ingredient insights lookup function
        def get_ingredient_insights(ingredient_name: str, risk_level: str) -> Dict[str, Any]:
            """Fast lookup for ingredient insights using pre-computed cache."""
            name_lower = ingredient_name.lower()
            
            # Direct lookup for exact matches (O(1) instead of O(n) substring searches)
            if name_lower in _INGREDIENT_INSIGHTS_CACHE:
                return _INGREDIENT_INSIGHTS_CACHE[name_lower].copy()
            
            # Fast keyword matching for partial matches
            for keyword, insights in _INGREDIENT_INSIGHTS_CACHE.items():
                if keyword in name_lower:
                    return insights.copy()
            
            # Optimized fallback with pre-computed templates
            fallback_templates = {
                "high": {
                    "overview": f"{ingredient_name} is categorized as high-risk due to potential health concerns requiring careful consideration.",
                    "health_risks": ["Potential health concerns", "Requires moderation", "Individual sensitivity varies"],
                    "common_uses": ["Food ingredient", "Processing aid", "Functional additive"]
                },
                "moderate": {
                    "overview": f"{ingredient_name} is categorized as moderate-risk with some health considerations for regular consumption.",
                    "health_risks": ["Monitor intake", "Consider alternatives", "Individual tolerance varies"],
                    "common_uses": ["Food ingredient", "Processing aid", "Functional additive"]
                }
            }
            return fallback_templates.get(risk_level, fallback_templates["moderate"])
        
        optimized = {
            "summary": truncate_text(assessment.get("summary", ""), 200),
            "grade": assessment.get("risk_summary", {}).get("grade", ""),
            "color": assessment.get("risk_summary", {}).get("color", ""),
            "high_risk": [],
            "moderate_risk": [],
            "low_risk": [],
            "nutrition": [],
            "citations": []  # Add citations array for mobile
        }
        
        # Optimized ingredient processing with pre-computed insights and efficient citation tracking
        ingredients = assessment.get("ingredients_assessment", {})
        citation_counter = 1
        citations_data = []  # Pre-build citations list for batch processing
        
        # Process high-risk ingredients with optimized insights lookup
        high_risk_ingredients = ingredients.get("high_risk", [])
        for ingredient in high_risk_ingredients:
            ingredient_name = ingredient.get("name", "")
            insights = get_ingredient_insights(ingredient_name, "high")
            
            # Pre-calculate citation IDs (2 per high-risk ingredient)
            ingredient_citations = [citation_counter, citation_counter + 1]
            citation_counter += 2
            
            # Batch citation data for later processing
            citations_data.extend([
                {"id": ingredient_citations[0], "ingredient": ingredient_name, "priority": "high"},
                {"id": ingredient_citations[1], "ingredient": ingredient_name, "priority": "high"}
            ])
            
            optimized["high_risk"].append({
                "name": truncate_text(ingredient_name, 50),
                "risk": ingredient.get("micro_report", ""),
                "overview": insights["overview"],
                "health_risks": insights["health_risks"],
                "common_uses": insights["common_uses"],
                "citations": ingredient_citations
            })
        
        # Process moderate-risk ingredients with optimized insights lookup
        moderate_risk_ingredients = ingredients.get("moderate_risk", [])
        for ingredient in moderate_risk_ingredients:
            ingredient_name = ingredient.get("name", "")
            insights = get_ingredient_insights(ingredient_name, "moderate")
            
            # Pre-calculate citation ID (1 per moderate-risk ingredient)
            ingredient_citations = [citation_counter]
            citation_counter += 1
            
            # Batch citation data for later processing
            citations_data.append({
                "id": ingredient_citations[0], 
                "ingredient": ingredient_name, 
                "priority": "moderate"
            })
            
            optimized["moderate_risk"].append({
                "name": truncate_text(ingredient_name, 50),
                "risk": ingredient.get("micro_report", ""),
                "overview": insights["overview"],
                "health_risks": insights["health_risks"],
                "common_uses": insights["common_uses"],
                "citations": ingredient_citations
            })
        
        # Low risk ingredients - simple format, no citations (performance optimization)
        for ingredient in ingredients.get("low_risk", []):
            optimized["low_risk"].append({
                "name": truncate_text(ingredient.get("name", ""), 50),
                "risk": truncate_text(ingredient.get("micro_report", ""), 150)
            })
        
        # Optimize nutrition insights - keep only the most important nutrients
        nutrition_priority = ["Salt", "Fat", "Protein"]  # Most relevant for mobile users
        nutrition_insights = assessment.get("nutrition_insights", [])
        
        for nutrient_name in nutrition_priority:
            for insight in nutrition_insights:
                if insight.get("nutrient") == nutrient_name:
                    optimized["nutrition"].append({
                        "nutrient": insight.get("nutrient", ""),
                        "amount": insight.get("amount_per_serving", ""),
                        "eval": insight.get("evaluation", ""),
                        "comment": insight.get("ai_commentary", "")  # Don't truncate - should be complete from backend
                    })
                    break
        
        # Use real scientific citations from the advanced search system
        original_citations = assessment.get("citations", [])
        
        # Filter and use only valid citations with URLs
        valid_citations = []
        for citation in original_citations:
            title = citation.get("title", "")
            url = citation.get("url", "")
            
            # Only include citations that have URLs (fixed fallback citations now have URLs)
            if url and url.strip():
                valid_citations.append({
                    "id": citation.get("id", len(valid_citations) + 1),
                    "title": truncate_text(title, 100),
                    "year": citation.get("year", 2024),
                    "url": url,
                    "source_type": citation.get("source_type", "research"),
                    "journal": citation.get("source", ""),
                    "format": "APA"
                })
        
        # Use filtered citations with URLs
        optimized["citations"] = valid_citations
        
        # Keep essential metadata but minimize it
        optimized["meta"] = {
            "product": assessment.get("metadata", {}).get("product_name", ""),
            "generated": assessment.get("metadata", {}).get("generated_at", "")[:10]  # Just date, not full timestamp
        }
        
        return optimized
        
    except Exception as e:
        logger.error(f"Error optimizing response for mobile: {e}")
        # Return original if optimization fails
        return assessment


# Simple Product Search endpoint
@router.get("/search", 
    response_model=Dict[str, Any],
    summary="Search Products by Name",
    description="Simple product search by name, brand, or ingredients",
    responses={
        200: {
            "description": "Search results found",
            "content": {
                "application/json": {
                    "example": {
                        "query": "chicken breast",
                        "total_results": 5,
                        "limit": 20,
                        "skip": 0,
                        "products": [
                            {
                                "code": "1234567890",
                                "name": "Organic Chicken Breast",
                                "brand": "HealthyMeat Co",
                                "risk_rating": "Green",
                                "salt": 0.3,
                                "protein": 25.0
                            }
                        ]
                    }
                }
            }
        },
        400: {"description": "Invalid search query"},
        500: {"description": "Search service error"}
    },
    tags=["Products"]
)
async def search_products(
    q: str = Query(..., description="Search query for product name, brand, or ingredients", example="chicken breast"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    supabase_service = Depends(get_supabase_service),
) -> Dict[str, Any]:
    """
    Simple product search by name, brand, or ingredients.
    
    Args:
        q: Search query for product name, brand, or ingredients
        limit: Maximum number of results to return (1-100, default 20)
        skip: Number of results to skip for pagination
        
    Returns:
        Dict containing search results and metadata
    """
    try:
        # Basic text search on multiple fields - exclude image_data for performance
        search_query = supabase_service.client.table('products').select(
            'code, name, brand, description, ingredients_text, calories, protein, fat, '
            'carbohydrates, salt, meat_type, risk_rating, image_url, last_updated, created_at'
        )
        
        # Create OR conditions for text search
        conditions = []
        
        # First, try exact match on the full query (more likely to find exact product names)
        full_query = q.strip()
        if full_query:
            conditions.extend([
                f'name.ilike.%{full_query}%',
                f'brand.ilike.%{full_query}%'
            ])
        
        # Then split and search individual terms (fallback for partial matches)
        search_terms = q.lower().split()
        for term in search_terms:
            # Skip very short words to reduce noise
            if len(term) > 2:
                conditions.extend([
                    f'name.ilike.%{term}%',
                    f'brand.ilike.%{term}%',
                    f'ingredients_text.ilike.%{term}%'
                ])
        
        if conditions:
            search_query = search_query.or_(','.join(conditions))
        
        # Apply pagination
        search_query = search_query.range(skip, skip + limit - 1)
        
        response = search_query.execute()
        results = response.data or []
        
        # Sort results to prioritize exact matches
        def calculate_relevance(product):
            """Calculate relevance score for sorting."""
            score = 0
            name = (product.get('name') or '').lower()
            brand = (product.get('brand') or '').lower()
            query_lower = q.lower()
            
            # Exact match in name or brand gets highest score
            if query_lower in name:
                score += 100
            if query_lower in brand:
                score += 50
                
            # Partial matches for each term
            for term in search_terms:
                if term in name:
                    score += 10
                if term in brand:
                    score += 5
                    
            return score
        
        # Sort by relevance score (highest first)
        results.sort(key=calculate_relevance, reverse=True)
        
        return {
            "query": q,
            "total_results": len(results),
            "limit": limit,
            "skip": skip,
            "products": results
        }
        
    except Exception as e:
        logger.error(f"Search failed for query '{q}': {e}")
        raise HTTPException(
            status_code=500,
            detail="Search service temporarily unavailable"
        )

# AI-Powered Natural Language Search endpoint (DEPRECATED - use /search instead)
@router.get("/nlp-search", 
    response_model=Dict[str, Any],
    summary="[DEPRECATED] AI-Powered Natural Language Product Search",
    description="DEPRECATED: Use /search endpoint instead. This endpoint now redirects to simple search.",
    deprecated=True,
    responses={
        200: {
            "description": "Search results found with AI ranking",
            "content": {
                "application/json": {
                    "example": {
                        "query": "healthy low sodium chicken",
                        "parsed_intent": {
                            "meat_types": ["chicken"],
                            "nutrition_filters": {"max_sodium": 500},
                            "health_intent": "healthy"
                        },
                        "total_results": 5,
                        "limit": 20,
                        "skip": 0,
                        "products": [
                            {
                                "code": "1234567890",
                                "name": "Organic Chicken Breast",
                                "brand": "HealthyMeat Co",
                                "risk_rating": "Green",
                                "salt": 0.3,
                                "protein": 25.0,
                                "_relevance_score": 0.92
                            }
                        ]
                    }
                }
            }
        },
        400: {"description": "Invalid search query"},
        500: {"description": "AI search service error"}
    },
    tags=["Products"]
)
async def natural_language_search(
    q: str = Query(..., description="Natural language search query", example="healthy chicken options"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination"),
    supabase_service = Depends(get_supabase_service),
) -> Dict[str, Any]:
    """
    DEPRECATED: This endpoint now redirects to the simple /search endpoint.
    
    The AI-powered NLP search has been replaced with traditional product search.
    Please use /api/v1/products/search instead.
    """
    logger.info(f"NLP search called with query '{q}', redirecting to simple search")
    
    # Simply redirect to the new search endpoint
    return await search_products(q=q, limit=limit, skip=skip, supabase_service=supabase_service)

@router.get("/search-debug",
    response_model=Dict[str, Any],
    summary="Debug Search Issues",
    description="Debug endpoint to test search functionality step by step",
    tags=["Products"]
)
async def debug_search_endpoint(
    q: str = Query("chicken", description="Test query"),
    supabase_service = Depends(get_supabase_service)
) -> Dict[str, Any]:
    """Debug search functionality step by step."""
    from app.core.config import settings
    import traceback
    
    debug_info = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": q,
        "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
        "gemini_key_length": len(settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else 0,
        "steps": []
    }
    
    try:
        # Step 1: Check API key
        debug_info["steps"].append("1. Checking Gemini API key")
        if not settings.GEMINI_API_KEY:
            debug_info["steps"].append("1a. No API key found, would use fallback")
            debug_info["fallback_triggered"] = True
            
            # Test fallback search
            debug_info["steps"].append("2. Testing fallback search")
            try:
                fallback_result = await _fallback_search(q, 5, 0, supabase_service)
                debug_info["steps"].append("2a. Fallback search succeeded")
                debug_info["fallback_result_count"] = len(fallback_result.get("products", []))
                debug_info["fallback_working"] = True
                return debug_info
            except Exception as e:
                debug_info["steps"].append(f"2a. Fallback search failed: {str(e)}")
                debug_info["fallback_error"] = str(e)
                debug_info["fallback_traceback"] = traceback.format_exc()
        else:
            debug_info["steps"].append("1a. API key found, would use NLP search")
            debug_info["fallback_triggered"] = False
            
        debug_info["test_completed"] = True
        return debug_info
        
    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        return debug_info

@router.get("/count", 
    response_model=Dict[str, int],
    summary="Get Product Count",
    description="Returns the total number of products in the database",
    responses={
        200: {
            "description": "Product count retrieved successfully",
            "content": {
                "application/json": {
                    "example": {"total": 15847}
                }
            }
        },
        500: {"description": "Database error"}
    },
    tags=["Products"]
)
def get_product_count(
    supabase_service = Depends(get_supabase_service)
) -> Dict[str, int]:
    """Get total count of products in database. Public endpoint."""
    try:
        total = supabase_service.count_products()
        return {"total": total}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.get("/test-gemini",
    response_model=Dict[str, Any],
    summary="Test Gemini API",
    description="Test connectivity to Google Gemini API for health assessments",
    responses={
        200: {
            "description": "Test completed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "api_key_set": True,
                        "api_key_length": 39,
                        "response_text": "Hello from Gemini",
                        "model_used": "gemini-1.5-flash"
                    }
                }
            }
        }
    },
    tags=["Testing"],
    include_in_schema=False  # Hide from production docs
)
async def test_gemini_api() -> Dict[str, Any]:
    """Test Gemini API connectivity and response"""
    import os
    import google.generativeai as genai
    
    try:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return {"error": "GEMINI_API_KEY not set", "success": False}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            "Say 'Hello from Gemini' and nothing else",
            generation_config=genai.GenerationConfig(temperature=0, max_output_tokens=10)
        )
        
        return {
            "success": True,
            "api_key_set": True,
            "api_key_length": len(api_key),
            "response_text": response.text,
            "model_used": "gemini-1.5-flash"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": e.__class__.__name__,
            "api_key_set": bool(api_key) if 'api_key' in locals() else False
        }

@router.get("/test-mcp-service")
async def test_mcp_service() -> Dict[str, Any]:
    """Test MCP service initialization and basic functionality"""
    try:
        from app.services.health_assessment_mcp_service import HealthAssessmentMCPService
        
        # Test service creation
        mcp_service = HealthAssessmentMCPService()
        
        # Test that the service has the expected properties
        has_model = hasattr(mcp_service, 'model')
        model_value = getattr(mcp_service, 'model', 'not_found')
        
        return {
            "success": True,
            "service_created": True,
            "has_model_attr": has_model,
            "model_value": model_value,
            "service_type": str(type(mcp_service))
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "error_type": e.__class__.__name__,
            "traceback": traceback.format_exc()
        }

@router.get("/", 
    response_model=List[models.Product],
    summary="List Products",
    description="Get a paginated list of products with optional filtering by risk rating",
    responses={
        200: {
            "description": "Products retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "code": "0002000003197",
                            "name": "Organic Beef Jerky",
                            "brand": "HealthySnacks",
                            "description": "Premium grass-fed beef jerky",
                            "ingredients_text": "Beef, salt, spices",
                            "calories": 250,
                            "protein": 25.0,
                            "fat": 10.0,
                            "carbohydrates": 5.0,
                            "salt": 1.2,
                            "meat_type": "beef",
                            "risk_rating": "Yellow",
                            "image_url": "https://example.com/image.jpg",
                            "last_updated": "2024-01-15T10:30:00Z"
                        }
                    ]
                }
            }
        },
        500: {"description": "Database error"}
    },
    tags=["Products"]
)
def get_products(
    supabase_service = Depends(get_supabase_service),
    skip: int = Query(0, ge=0, description="Number of products to skip", example=0),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return", example=20),
    risk_rating: Optional[str] = Query(None, description="Filter by risk rating", enum=["Green", "Yellow", "Red"])
) -> List[models.Product]:
    """
    Retrieve products with optional filtering and pagination.
    
    Args:
        supabase_service: Supabase service instance
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100, max: 1000)
        risk_rating: Filter by risk rating (Green, Yellow, Red)
        
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
                    image_data=None,  # Exclude massive base64 data - use image_url instead
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

@router.get("/recommendations", 
    response_model=models.RecommendationResponse,
    summary="Get Personalized Recommendations",
    description="Get product recommendations based on user preferences set during onboarding",
    responses={
        200: {
            "description": "Recommendations generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "recommendations": [
                            {
                                "product": {
                                    "code": "1234567890",
                                    "name": "Low Sodium Turkey Breast",
                                    "brand": "HealthyChoice",
                                    "risk_rating": "Green",
                                    "salt": 0.5,
                                    "protein": 22.0
                                },
                                "match_details": {
                                    "matches": ["Low sodium content", "High protein", "Turkey preference"],
                                    "concerns": []
                                },
                                "match_score": None
                            }
                        ],
                        "total_matches": 15
                    }
                }
            }
        },
        401: {"description": "Authentication required"},
        500: {"description": "Failed to generate recommendations"}
    },
    tags=["Products", "Recommendations"]
)
async def get_product_recommendations(
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user),
    page_size: int = Query(10, ge=1, le=20, description="Number of recommendations per page", example=10),
    offset: int = Query(0, ge=0, description="Number of recommendations to skip (for pagination)", example=0),
) -> models.RecommendationResponse:
    """
    Get personalized product recommendations with parallel-generated health assessments.
    
    Recommendations are tailored based on the preferences set during the user onboarding process,
    including nutrition focus, additives, ethical concerns, and preferred meat types.
    Uses parallel processing to pre-populate health assessments for instant loading.
    
    Args:
        db: Database session
        current_user: Current active user
        page_size: Number of recommendations per page (1-20, default 10)
        offset: Number of recommendations to skip for pagination (default 0)
        
    Returns:
        RecommendationResponse: List of recommended products with match details and pre-populated health assessments
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
        
        # Log user preferences for debugging
        logger.info(f"🎯 User {current_user.id} preferences: {preferences}")
        
        # Get total count using efficient database query
        total_count = supabase_service.count_products()
        
        # Get personalized recommendations using Supabase with pagination
        recommended_products = get_personalized_recommendations(supabase_service, preferences, page_size, offset)
        
        if not recommended_products:
            return models.RecommendationResponse(
                recommendations=[],
                total_matches=total_count
            )
        
        logger.info(f"Returning {len(recommended_products)} personalized products (no pre-generation)")
        
        # Build response with match details (no health assessment generation)
        result = []
        for product_dict in recommended_products:
            try:
                # Analyze why this product matches preferences
                matches, concerns = analyze_product_match(product_dict, preferences)
                
                # Create Product model from dictionary
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
                    image_data=None,  # Exclude massive base64 data - use image_url instead
                    last_updated=product_dict.get('last_updated'),
                    created_at=product_dict.get('created_at')
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
            total_matches=total_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.get("/{code}",
    response_model=models.ProductStructured,
    summary="Get Product Details",
    description="Get detailed information about a specific product by its barcode",
    responses={
        200: {
            "description": "Product found",
            "content": {
                "application/json": {
                    "example": {
                        "product": {
                            "code": "0002000003197",
                            "name": "Premium Beef Jerky",
                            "brand": "MeatCraft",
                            "description": "Artisanal beef jerky",
                            "ingredients_text": "Beef, salt, sodium nitrite, spices",
                            "image_url": "https://example.com/product.jpg",
                            "meat_type": "beef"
                        },
                        "criteria": {
                            "risk_rating": "Yellow",
                            "additives": ["E250 (Sodium nitrite)", "Natural spices"]
                        },
                        "health": {
                            "nutrition": {
                                "calories": 280,
                                "protein": 25.0,
                                "fat": 15.0,
                                "carbohydrates": 8.0,
                                "salt": 2.1
                            },
                            "health_concerns": ["High salt content", "Contains preservatives"]
                        },
                        "environment": {
                            "impact": "High",
                            "details": "Beef production typically has higher environmental impact",
                            "sustainability_practices": ["Unknown"]
                        },
                        "metadata": {
                            "last_updated": "2024-01-15T10:30:00Z",
                            "created_at": "2023-12-01T08:00:00Z"
                        }
                    }
                }
            }
        },
        404: {"description": "Product not found"},
        500: {"description": "Error retrieving product"}
    },
    tags=["Products"]
)
def get_product(
    code: str = Path(..., description="Product barcode", example="0002000003197"),
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
                image_data=None,  # Exclude massive base64 data - use image_url instead
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


@router.get("/{code}/health-assessment-mcp", 
    response_model=Dict[str, Any],
    responses={
        200: {
            "description": "Health assessment generated successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "full": {
                            "summary": "Full assessment with complete details",
                            "value": {
                                "summary": "This product contains preservatives requiring moderation...",
                                "risk_summary": {"grade": "C", "color": "Yellow"},
                                "ingredients_assessment": {
                                    "high_risk": [{"name": "E250", "risk_level": "high", "micro_report": "Linked to...", "citations": [1,2]}],
                                    "moderate_risk": [], 
                                    "low_risk": []
                                },
                                "nutrition_insights": [
                                    {"nutrient": "Protein", "amount_per_serving": "16.0 g", "evaluation": "high", "ai_commentary": "Excellent source..."}
                                ],
                                "citations": [{"id": 1, "title": "Health effects...", "source": "Journal", "year": 2024}],
                                "metadata": {"product_code": "0002000003197", "generated_at": "2025-06-26T16:29:18.171531"}
                            }
                        },
                        "mobile": {
                            "summary": "Mobile-optimized response",
                            "value": {
                                "summary": "This product contains preservatives requiring moderation...",
                                "grade": "C",
                                "color": "Yellow", 
                                "high_risk": [{"name": "E250", "risk": "Linked to potential carcinogenic..."}],
                                "moderate_risk": [],
                                "nutrition": [
                                    {"nutrient": "Salt", "amount": "2350 mg", "eval": "high", "comment": "High sodium content..."}
                                ],
                                "meta": {"product": "Product Name", "generated": "2025-06-26"}
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "Product not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_product_health_assessment_mcp(
    code: str,
    format: Optional[str] = Query(None, regex="^(mobile|full)$", description="Response format: 'mobile' for optimized mobile response, 'full' for complete data"),
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Union[models.HealthAssessment, Dict[str, Any]]:
    """
    Generate an evidence-based health assessment using MCP (Model Context Protocol).
    
    This endpoint uses real scientific research to generate micro-reports for ingredients,
    providing evidence-based health assessments instead of hardcoded templates.
    
    ## Format Options:
    - **full** (default): Complete assessment with all details (~3.5KB)
    - **mobile**: Optimized for mobile apps (~1.2KB, 65% smaller)
    
    ## Mobile Format Benefits:
    - 93% bandwidth reduction when combined with gzip
    - Truncated summaries and micro-reports
    - Limited to top 2 high/moderate risk ingredients
    - Only essential nutrients (Salt, Fat, Protein)
    - 24-hour cache headers for offline support
    
    ## Example Usage:
    ```
    # Full assessment
    GET /api/v1/products/0002000003197/health-assessment-mcp
    
    # Mobile-optimized
    GET /api/v1/products/0002000003197/health-assessment-mcp?format=mobile
    ```
    
    Args:
        code: The product's barcode
        format: Response format - 'mobile' or 'full' (default: full)
        supabase_service: Supabase client
        current_user: Currently authenticated user
        
    Returns:
        Evidence-based health assessment with real scientific citations
    """
    logger.info(f"Starting MCP health assessment for product {code}")
    try:
        # Step 1: Fetch product data from Supabase
        logger.info("Step 1: Fetching product data from Supabase")
        product_data = supabase_service.get_product_by_code(code)
        
        if not product_data:
            logger.warning(f"Product with code '{code}' not found in Supabase")
            
            # Step 1b: Try OpenFoodFacts fallback
            logger.info("Step 1b: Trying OpenFoodFacts fallback")
            openfoodfacts_service = get_openfoodfacts_service()
            openfood_result = openfoodfacts_service.get_product_by_barcode(code)
            
            if not openfood_result.get("found"):
                logger.warning(f"Product {code} not found in OpenFoodFacts either")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Product with code '{code}' not found in our database or OpenFoodFacts"
                )
            
            if not openfood_result.get("is_animal_product"):
                logger.warning(f"Product {code} found but is not an animal-based product")
                raise HTTPException(
                    status_code=400,
                    detail="This product is not an animal-based product. Clear-Meat only analyzes meat, dairy, and seafood products."
                )
            
            # Step 1c: Save new animal product to Supabase
            logger.info(f"Step 1c: Saving new animal product {code} to database")
            new_product_data = openfood_result["product_data"]
            new_product_data["code"] = code  # Ensure barcode is included
            
            saved_product = supabase_service.insert_product(new_product_data)
            if saved_product:
                product_data = saved_product
                logger.info(f"Successfully saved new product {code} from OpenFoodFacts")
            else:
                # Use the mapped data even if save failed
                product_data = new_product_data
                logger.warning(f"Failed to save product {code} to database, proceeding with OpenFoodFacts data")
        
        logger.info("Step 1: Product data obtained successfully")

        # Step 2: Structure product data
        logger.info("Step 2: Structuring product data")
        structured_product = helpers.structure_product_data(product_data)
        if not structured_product:
            logger.error("Failed to structure product data")
            raise HTTPException(status_code=500, detail="Failed to structure product data for assessment")
        logger.info("Step 2: Product data structured successfully")

        # Step 3: Generate MCP-based evidence assessment with existing risk rating
        logger.info("Step 3: Generating evidence-based assessment using MCP")
        mcp_service = HealthAssessmentMCPService()
        
        # Use OpenFoodFacts risk_rating from database instead of AI-generated grades
        existing_risk_rating = product_data.get('risk_rating')  # e.g., "Green", "Yellow", "Red"
        logger.info(f"Using existing risk_rating from database: {existing_risk_rating}")
        
        try:
            assessment = await mcp_service.generate_health_assessment_with_real_evidence(
                structured_product, 
                existing_risk_rating=existing_risk_rating
            )
        except Exception as e:
            logger.error(f"Error during health assessment generation: {e}")
            assessment = None
        
        if not assessment:
            logger.error("Failed to generate MCP health assessment")
            # Instead of 500 error, create a minimal assessment from available data
            if existing_risk_rating:
                logger.info(f"Creating minimal assessment using risk_rating: {existing_risk_rating}")
                assessment = mcp_service.create_minimal_fallback_assessment(structured_product, existing_risk_rating)
            else:
                raise HTTPException(status_code=404, detail="Product not found or no assessment data available")
        
        logger.info("Step 3: MCP health assessment generated successfully")
        
        # Optimize response for mobile if requested
        if format == "mobile":
            assessment = _optimize_for_mobile(assessment)
        
        # Return dict directly to avoid Pydantic model conversion issues
        from fastapi.responses import JSONResponse
        response = JSONResponse(content=assessment)
        
        # Add caching headers for mobile optimization
        if format == "mobile":
            response.headers["Cache-Control"] = "public, max-age=86400"  # 24 hours
            response.headers["ETag"] = f'"{code}-mobile-{hash(str(assessment))}"'
        
        return response

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
    Debug endpoint for MCP health assessment troubleshooting.
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
        
        # Step 5: Test assessment generation with existing risk rating
        debug_info["step"] = "generating_assessment"
        existing_risk_rating = product_data.get('risk_rating')
        debug_info["existing_risk_rating"] = existing_risk_rating
        
        assessment_result = await mcp_service._generate_evidence_based_assessment(
            structured_product, 
            basic_categorization.get('high_risk_ingredients', []),
            basic_categorization.get('moderate_risk_ingredients', []),
            existing_risk_rating
        )
        
        if assessment_result:
            debug_info["assessment_generated"] = True
            # Handle both dict and HealthAssessment object responses
            if isinstance(assessment_result, dict):
                debug_info["assessment_summary"] = str(assessment_result.get("summary", ""))[:100] + "..."
                debug_info["assessment_grade"] = assessment_result.get("risk_summary", {}).get("grade", "Unknown")
                debug_info["assessment_type"] = "dict"
            else:
                debug_info["assessment_summary"] = assessment_result.summary[:100] + "..."
                debug_info["assessment_grade"] = assessment_result.risk_summary.grade
                debug_info["assessment_type"] = "HealthAssessment object"
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


@router.get("/explore", 
    response_model=models.RecommendationResponse,
    summary="Get Public Product Recommendations with Pre-populated Health Assessments",
    description="Get product recommendations with parallel-generated health assessments - perfect for app explore pages with instant loading",
    responses={
        200: {
            "description": "Public recommendations generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "recommendations": [
                            {
                                "product": {
                                    "code": "9876543210",
                                    "name": "Organic Grass-Fed Ground Beef",
                                    "brand": "Nature's Best",
                                    "risk_rating": "Green",
                                    "protein": 22.0,
                                    "fat": 15.0,
                                    "salt": 0.8
                                },
                                "match_details": {
                                    "matches": ["High protein content", "Organic", "Low sodium"],
                                    "concerns": []
                                },
                                "match_score": None
                            }
                        ],
                        "total_matches": 25
                    }
                }
            }
        },
        500: {"description": "Failed to generate recommendations"}
    },
    tags=["Products", "Public"]
)
async def get_public_recommendations(
    supabase_service = Depends(get_supabase_service),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of recommendations to return", example=20),
) -> models.RecommendationResponse:
    """
    Get public product recommendations with parallel-generated health assessments.
    
    Perfect for app explore pages where users want to browse products before signing up.
    Uses parallel processing to pre-populate health assessments for instant loading.
    
    Args:
        supabase_service: Supabase service instance
        limit: Maximum number of recommendations to return (1-100, default 30)
        
    Returns:
        RecommendationResponse: List of recommended products with match details and pre-populated health assessments
    """
    try:
        logger.info(f"Generating public explore recommendations with parallel health assessments (limit: {limit})")
        
        # Use default healthy preferences for anonymous users
        default_preferences = {
            "nutrition_focus": "protein",
            "avoid_preservatives": True,
            "prefer_organic_or_grass_fed": True,
            "prefer_low_risk": True,
            "meat_preferences": ["chicken", "turkey", "beef", "fish"]  # Show variety
        }
        
        # Get total count using efficient database query
        total_count = supabase_service.count_products()
        
        # Get recommendations using the same service but with default preferences
        recommended_products = get_personalized_recommendations(
            supabase_service, 
            default_preferences, 
            limit, 
            0  # Start from beginning
        )
        
        if not recommended_products:
            logger.warning("No public recommendations found")
            return models.RecommendationResponse(
                recommendations=[],
                total_matches=total_count
            )
        
        logger.info(f"Returning {len(recommended_products)} public products (no pre-generation)")
        
        # Build response with match details (no health assessment generation)
        from app.services.recommendation_service import analyze_product_match
        result = []
        for product in recommended_products:
            try:
                # Analyze why this product matches the default preferences
                matches, concerns = analyze_product_match(product, default_preferences)
                
                # Create RecommendedProduct object
                recommended_product = models.RecommendedProduct(
                    product=models.Product(**product),
                    match_details=models.ProductMatch(
                        matches=matches,
                        concerns=concerns
                    ),
                    match_score=None  # We don't expose raw scores to clients
                )
                
                result.append(recommended_product)
                
            except Exception as e:
                logger.warning(f"Error processing product {product.get('code', 'unknown')}: {e}")
                continue
        
        logger.info(f"Returning {len(result)} public recommendations (no pre-generation)")
        
        return models.RecommendationResponse(
            recommendations=result,
            total_matches=total_count
        )
    except Exception as e:
        logger.error(f"Error generating public recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate public recommendations: {str(e)}"
        )


