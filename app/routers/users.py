"""User router for the MeatWise API."""

from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
import json
from datetime import datetime
import uuid

from app.models import (
    User, UserUpdate, 
    ScanHistory, ScanHistoryCreate, 
    UserFavorite, UserFavoriteCreate
)
from app.core import security
from app.db import models as db_models
from app.db.session import get_db
from app.internal.dependencies import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _convert_uuid_to_str(obj_id):
    """Helper to convert UUID objects to strings."""
    if hasattr(obj_id, 'hex'):
        return str(obj_id)
    return obj_id


@router.get("/me", response_model=User)
def get_current_user(
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user.
    
    Args:
        current_user: Current user from auth dependency
        
    Returns:
        User: Current user details
    """
    # Convert UUID fields to strings to ensure compatibility
    user_dict = {
        "id": _convert_uuid_to_str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "role": current_user.role,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }
    
    return user_dict


@router.put("/me", response_model=User)
def update_current_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Update current user.
    
    Args:
        user_in: Updated user data
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        User: Updated user details
    """
    update_data = user_in.model_dump(exclude_unset=True, exclude_none=True)
    
    # Hash password if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = security.get_password_hash(update_data["password"])
        del update_data["password"]
    
    # Only superusers can change is_superuser and role
    if not current_user.is_superuser:
        update_data.pop("is_superuser", None)
        update_data.pop("role", None)
    
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    # Convert UUID fields to strings to ensure compatibility
    user_dict = {
        "id": _convert_uuid_to_str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "role": current_user.role,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }
    
    return user_dict


@router.get("/history", response_model=List[ScanHistory])
async def get_user_scan_history(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Get scan history for the current user.
    
    Args:
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        List[ScanHistory]: List of scan history entries for the user
    """
    try:
        scan_history = (
            db.query(db_models.ScanHistory)
            .filter(db_models.ScanHistory.user_id == current_user.id)
            .order_by(db_models.ScanHistory.scanned_at.desc())
            .all()
        )
        
        # Load products for each scan history entry
        result = []
        for scan in scan_history:
            product = db.query(db_models.Product).filter(db_models.Product.code == scan.product_code).first()
            
            # Create a dict with all necessary fields converted properly
            scan_dict = {
                "id": _convert_uuid_to_str(scan.id),
                "user_id": _convert_uuid_to_str(scan.user_id),
                "product_code": scan.product_code,
                "location": json.loads(scan.location) if scan.location and isinstance(scan.location, str) else scan.location,
                "device_info": scan.device_info,
                "scanned_at": scan.scanned_at,
                "product": product
            }
            result.append(scan_dict)
                
        return result
    except Exception as e:
        logger.error(f"Error getting user scan history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scan history: {str(e)}")


@router.post("/history", response_model=ScanHistory)
async def add_scan_history(
    scan_data: ScanHistoryCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
):
    """
    Add an item to user's scan history.
    
    Args:
        scan_data: Scan history data to add
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        ScanHistory: Created scan history entry
        
    Raises:
        HTTPException: If product not found or error occurs
    """
    try:
        # Check if product exists
        product = db.query(db_models.Product).filter(db_models.Product.code == scan_data.product_code).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Ensure location is a string for database storage
        location_data = None
        if scan_data.location:
            if isinstance(scan_data.location, dict):
                location_data = json.dumps(scan_data.location)
            else:
                location_data = scan_data.location
                
        # Generate UUID as string to avoid conversion issues
        scan_id = str(uuid.uuid4())
        user_id = _convert_uuid_to_str(current_user.id)
            
        # Create scan history entry
        scan_history = db_models.ScanHistory(
            id=scan_id,
            product_code=scan_data.product_code,
            user_id=user_id,
            location=location_data,
            device_info=scan_data.device_info,
            scanned_at=datetime.now()
        )
        
        db.add(scan_history)
        db.commit()
        db.refresh(scan_history)
        
        # Make a dict to return with the proper data types
        response_dict = {
            "id": scan_id,
            "user_id": user_id,
            "product_code": scan_data.product_code,
            "location": scan_data.location,
            "device_info": scan_data.device_info,
            "scanned_at": scan_history.scanned_at,
            "product": product
        }
            
        return response_dict
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding scan history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add scan history: {str(e)}")


@router.get("/favorites", response_model=List[UserFavorite])
async def get_user_favorites(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user's favorite products.
    
    Args:
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        List[UserFavorite]: User's favorite products
    """
    try:
        favorites = (
            db.query(db_models.UserFavorite)
            .filter(db_models.UserFavorite.user_id == current_user.id)
            .all()
        )
        
        # Load product details for each favorite
        result = []
        for favorite in favorites:
            # Get the product data
            product = db.query(db_models.Product).filter(db_models.Product.code == favorite.product_code).first()
            
            # Create a dict with all necessary fields converted properly
            favorite_dict = {
                "product_code": favorite.product_code,
                "notes": favorite.notes,
                "user_id": _convert_uuid_to_str(favorite.user_id),
                "added_at": favorite.added_at,
                "product": product
            }
            result.append(favorite_dict)
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve favorites: {str(e)}")


@router.post("/favorites", response_model=UserFavorite)
async def add_favorite(
    favorite_in: UserFavoriteCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Add a product to user's favorites.
    
    Args:
        favorite_in: Favorite data
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        UserFavorite: Created favorite entry
        
    Raises:
        HTTPException: If product not found or already in favorites
    """
    try:
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
        
        # Convert user_id to string
        user_id = _convert_uuid_to_str(current_user.id)
        
        favorite = db_models.UserFavorite(
            user_id=user_id,
            **favorite_in.model_dump(),
        )
        
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        
        # Create a response dictionary with properly formatted fields
        response = {
            "product_code": favorite.product_code,
            "notes": favorite.notes,
            "user_id": user_id,
            "added_at": favorite.added_at,
            "product": product
        }
        
        return response
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add favorite: {str(e)}")


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
        current_user: Current user from auth dependency
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If favorite not found
    """
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove favorite: {str(e)}") 