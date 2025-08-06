"""
Ingredient analysis endpoints for detailed health information and citations.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.services.ingredient_analysis_service import IngredientAnalysisService
from app.internal.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize service
ingredient_service = IngredientAnalysisService()


@router.get("/{ingredient_name}/analysis")
async def get_ingredient_analysis(
    ingredient_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive analysis of a food ingredient including health effects and citations.
    
    This endpoint provides:
    - AI-generated health analysis
    - Specific health concerns and mechanisms
    - Multi-source citations (academic + health authorities)
    - Risk assessment and recommendations
    
    Args:
        ingredient_name: Name of the ingredient to analyze (e.g., "sodium phosphates")
        current_user: Authenticated user
        
    Returns:
        Comprehensive ingredient analysis with citations
        
    Example:
        GET /api/v1/ingredients/sodium%20phosphates/analysis
    """
    try:
        # Clean and validate ingredient name
        ingredient_clean = ingredient_name.strip().replace("%20", " ").replace("+", " ")
        
        if not ingredient_clean:
            raise HTTPException(
                status_code=400, 
                detail="Ingredient name is required"
            )
        
        if len(ingredient_clean) > 100:
            raise HTTPException(
                status_code=400, 
                detail="Ingredient name too long (max 100 characters)"
            )
        
        logger.info(f"[Ingredient Analysis API] User {current_user.id} requesting analysis for: {ingredient_clean}")
        
        # Generate analysis
        result = await ingredient_service.analyze_ingredient(ingredient_clean)
        
        if "error" in result:
            logger.error(f"Ingredient analysis failed: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail="Failed to analyze ingredient. Please try again."
            )
        
        # Log success
        citation_count = result.get("citations", {}).get("total_found", 0)
        logger.info(f"[Ingredient Analysis API] Successfully analyzed {ingredient_clean} with {citation_count} citations")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ingredient analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during ingredient analysis"
        )


@router.get("/{ingredient_name}/quick-info")
async def get_ingredient_quick_info(
    ingredient_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get quick ingredient information without full analysis (faster response).
    
    Returns basic risk level and primary concerns only.
    Use this for ingredient list previews before full analysis.
    
    Args:
        ingredient_name: Name of the ingredient
        current_user: Authenticated user
        
    Returns:
        Quick ingredient info with basic risk assessment
    """
    try:
        ingredient_clean = ingredient_name.strip().replace("%20", " ").replace("+", " ")
        
        if not ingredient_clean:
            raise HTTPException(status_code=400, detail="Ingredient name is required")
        
        logger.info(f"[Quick Ingredient Info] User {current_user.id} requesting quick info for: {ingredient_clean}")
        
        # Get basic categorization without full analysis
        quick_info = await _get_quick_ingredient_info(ingredient_clean)
        
        return {
            "ingredient": ingredient_clean,
            "risk_level": quick_info["risk_level"],
            "primary_concern": quick_info["primary_concern"],
            "category": quick_info["category"],
            "requires_full_analysis": True,
            "metadata": {
                "response_type": "quick_info",
                "timestamp": "2025-01-31"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick ingredient info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get ingredient information"
        )


async def _get_quick_ingredient_info(ingredient: str) -> Dict[str, str]:
    """Get quick ingredient categorization without full AI analysis."""
    ingredient_lower = ingredient.lower()
    
    # Quick pattern-based categorization
    if any(term in ingredient_lower for term in ['phosphate', 'nitrite', 'nitrate']):
        return {
            "risk_level": "moderate",
            "primary_concern": "Preservative with potential health effects",
            "category": "preservative"
        }
    
    elif any(term in ingredient_lower for term in ['bha', 'bht', 'tbhq']):
        return {
            "risk_level": "high", 
            "primary_concern": "Antioxidant preservative with safety concerns",
            "category": "antioxidant"
        }
    
    elif any(term in ingredient_lower for term in ['artificial color', 'red 40', 'yellow 6', 'blue 1']):
        return {
            "risk_level": "moderate",
            "primary_concern": "Artificial coloring with behavioral concerns",
            "category": "colorant"
        }
    
    elif 'msg' in ingredient_lower or 'monosodium glutamate' in ingredient_lower:
        return {
            "risk_level": "moderate",
            "primary_concern": "Flavor enhancer with sensitivity concerns",
            "category": "flavor_enhancer"
        }
    
    elif any(term in ingredient_lower for term in ['syrup', 'sugar', 'dextrose', 'fructose']):
        return {
            "risk_level": "moderate",
            "primary_concern": "Added sugar contributing to health issues",
            "category": "sweetener"
        }
    
    else:
        return {
            "risk_level": "unknown",
            "primary_concern": "Requires detailed analysis",
            "category": "other"
        }


# Health check endpoint for the ingredients service
@router.get("/health")
async def ingredients_health_check():
    """Health check for ingredients analysis service."""
    try:
        # Test basic service functionality
        test_result = await ingredient_service._generate_ingredient_analysis("water")
        
        return {
            "status": "healthy",
            "service": "ingredient_analysis",
            "ai_service": "available" if test_result else "unavailable",
            "citation_service": "available",
            "timestamp": "2025-01-31"
        }
    except Exception as e:
        logger.error(f"Ingredients service health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-01-31"
        }