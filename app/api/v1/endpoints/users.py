"""User endpoints for the MeatWise API."""

from typing import Any, List, Optional, Dict
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from sqlalchemy.orm import Session
from pydantic import EmailStr

from app.api.v1 import models
from app.core import security
from app.db import models as db_models
from app.db.session import get_db
from app.db.supabase_client import get_supabase_service
from app.internal.dependencies import get_current_active_user
from app.services.recommendation_service import (
    get_personalized_recommendations, analyze_product_match
)

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()


@router.get("/me", 
    response_model=models.User,
    summary="Get Current User Profile",
    description="Retrieve the profile information of the currently authenticated user",
    responses={
        200: {
            "description": "User profile retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_verified": True,
                        "created_at": "2024-01-15T10:30:00Z",
                        "preferences": {
                            "nutrition_focus": "protein",
                            "avoid_preservatives": True,
                            "meat_preferences": ["chicken", "turkey"]
                        }
                    }
                }
            }
        },
        401: {"description": "Not authenticated"}
    },
    tags=["Users", "Profile"]
)
def get_current_user(
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user.
    
    Args:
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        models.User: Current user details
    """
    return current_user


@router.put("/me", 
    response_model=models.User,
    summary="Update User Profile",
    description="Update the current user's profile information",
    responses={
        200: {
            "description": "Profile updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "full_name": "John Smith",
                        "preferences": {
                            "nutrition_focus": "low_sodium",
                            "avoid_preservatives": True,
                            "meat_preferences": ["chicken", "turkey", "fish"]
                        }
                    }
                }
            }
        },
        401: {"description": "Not authenticated"},
        500: {"description": "Failed to update profile"}
    },
    tags=["Users", "Profile"]
)
def update_current_user(
    user_in: models.UserUpdate = Body(..., example={
        "full_name": "John Smith",
        "preferences": {
            "nutrition_focus": "low_sodium",
            "avoid_preservatives": True,
            "meat_preferences": ["chicken", "turkey"]
        }
    }),
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Any:
    """
    Update current user.
    
    Args:
        user_in: Updated user data
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        models.User: Updated user details
    """
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = security.get_password_hash(update_data["password"])
        del update_data["password"]
    
    # Update user profile via Supabase
    updated_user = supabase_service.update_user_profile(current_user.id, update_data)
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update user profile")
    
    # Update the current_user object for return
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    return current_user


@router.get("/history", response_model=List[models.ScanHistory])
def get_user_scan_history(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get current user's scan history.
    
    Args:
        db: Database session
        current_user: Current user from auth dependency
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[models.ScanHistory]: User's scan history
    """
    return (
        db.query(db_models.ScanHistory)
        .filter(db_models.ScanHistory.user_id == current_user.id)
        .order_by(db_models.ScanHistory.scanned_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/history", response_model=models.ScanHistory)
def add_scan_history(
    scan_in: models.ScanHistoryCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Add a scan to user's history.
    
    Args:
        scan_in: Scan data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        models.ScanHistory: Created scan history entry
        
    Raises:
        HTTPException: If product not found
    """
    # Check if product exists
    product = db.query(db_models.Product).filter(db_models.Product.code == scan_in.product_code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    scan = db_models.ScanHistory(
        user_id=current_user.id,
        **scan_in.model_dump(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/favorites", 
    response_model=List[models.UserFavorite],
    summary="Get User Favorites",
    description="Retrieve all products marked as favorites by the current user",
    responses={
        200: {
            "description": "Favorites retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "1",
                            "user_id": "123e4567-e89b-12d3-a456-426614174000",
                            "product_code": "0002000003197",
                            "added_at": "2024-01-15T10:30:00Z",
                            "product": {
                                "code": "0002000003197",
                                "name": "Organic Chicken Breast",
                                "brand": "HealthyChoice",
                                "risk_rating": "Green"
                            }
                        }
                    ]
                }
            }
        },
        401: {"description": "Not authenticated"}
    },
    tags=["Users", "Favorites"]
)
def get_user_favorites(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user)
) -> Any:
    """
    Get current user's favorite products.
    
    Args:
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        List[models.UserFavorite]: User's favorite products
    """
    return (
        db.query(db_models.UserFavorite)
        .filter(db_models.UserFavorite.user_id == current_user.id)
        .all()
    )


@router.post("/favorites", response_model=models.UserFavorite)
def add_favorite(
    favorite_in: models.UserFavoriteCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Add a product to user's favorites.
    
    Args:
        favorite_in: Favorite data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        models.UserFavorite: Created favorite entry
        
    Raises:
        HTTPException: If product not found or already in favorites
    """
    # Check if product exists
    product = db.query(db_models.Product).filter(db_models.Product.code == favorite_in.product_code).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already in favorites
    existing = (
        db.query(db_models.UserFavorite)
        .filter(
            db_models.UserFavorite.user_id == current_user.id,
            db_models.UserFavorite.product_code == favorite_in.product_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Product already in favorites")
    
    favorite = db_models.UserFavorite(
        user_id=current_user.id,
        **favorite_in.model_dump(),
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.delete("/favorites/{product_code}")
def remove_favorite(
    product_code: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Remove a product from user's favorites.
    
    Args:
        product_code: Product barcode
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If favorite not found
    """
    favorite = (
        db.query(db_models.UserFavorite)
        .filter(
            db_models.UserFavorite.user_id == current_user.id,
            db_models.UserFavorite.product_code == product_code,
        )
        .first()
    )
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    db.delete(favorite)
    db.commit()
    return {"message": "Favorite removed successfully"} 


@router.get("/explore", 
    response_model=models.RecommendationResponse,
    summary="Get Explore Page Recommendations",
    description="Get personalized product recommendations optimized for discovery and exploration",
    responses={
        200: {
            "description": "Explore recommendations generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "recommendations": [
                            {
                                "product": {
                                    "code": "9876543210",
                                    "name": "Grass-Fed Bison Jerky",
                                    "brand": "Wild Harvest",
                                    "risk_rating": "Green",
                                    "protein": 30.0,
                                    "salt": 0.9
                                },
                                "match_details": {
                                    "matches": ["High protein content", "Grass-fed meat", "Low sodium"],
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
        401: {"description": "Not authenticated"},
        500: {"description": "Failed to generate recommendations"}
    },
    tags=["Users", "Recommendations"]
)
def get_explore_recommendations(
    db: Session = Depends(get_db),
    supabase_service = Depends(get_supabase_service),
    current_user: db_models.User = Depends(get_current_active_user),
    limit: int = Query(30, ge=1, le=100, description="Maximum number of recommendations to return", example=20),
) -> Any:
    """
    Get personalized product recommendations for the explore page.
    
    Similar to the product recommendations endpoint, but specifically designed for the explore
    user experience with potentially different weighting or presentation.
    
    Args:
        db: Database session
        supabase_service: Supabase service instance
        current_user: Current active user
        limit: Maximum number of recommendations to return (1-100, default 30)
        
    Returns:
        RecommendationResponse: List of recommended products with match details
    """
    try:
        logger.info(f"Generating explore recommendations for user {current_user.id}")
        
        # Get user preferences
        preferences = getattr(current_user, "preferences", {}) or {}
        if not preferences:
            logger.warning(f"User {current_user.id} has no preferences set for explore. Using defaults.")
            preferences = {
                # Default preferences if none are set
                "nutrition_focus": "protein",
                "avoid_preservatives": True,
                "prefer_organic_or_grass_fed": True,
                "meat_preferences": ["chicken", "beef", "pork"]
            }
            
        # Add a stronger diversity factor for explore page
        preferences["_explore_page"] = True
        
        # Get personalized recommendations
        recommended_products = get_personalized_recommendations(supabase_service, preferences, limit, 0)
        
        if not recommended_products:
            logger.warning("No explore recommendations found")
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
                product=models.Product.model_validate(product),
                match_details=models.ProductMatch(
                    matches=matches, 
                    concerns=concerns
                ),
                match_score=None  # We don't expose raw scores to clients
            )
            
            result.append(recommended_product)
        
        logger.info(f"Returning {len(result)} explore recommendations")
        
        return models.RecommendationResponse(
            recommendations=result,
            total_matches=len(result)
        )
    except Exception as e:
        logger.error(f"Error generating explore recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explore recommendations: {str(e)}"
        ) 