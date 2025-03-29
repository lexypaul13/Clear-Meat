"""User router for the MeatWise API."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import User, UserUpdate, ScanHistory, ScanHistoryCreate, UserFavorite, UserFavoriteCreate
from app.core import security
from app.db import models as db_models
from app.db.session import get_db
from app.internal.dependencies import get_current_active_user

router = APIRouter()


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
        "id": str(current_user.id),
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
        "id": str(current_user.id),
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
        List[ScanHistory]: User's scan history
    """
    return (
        db.query(db_models.ScanHistory)
        .filter(db_models.ScanHistory.user_id == current_user.id)
        .order_by(db_models.ScanHistory.scanned_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/history", response_model=ScanHistory)
def add_scan_history(
    scan_in: ScanHistoryCreate,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_active_user),
) -> Any:
    """
    Add a scan to user's history.
    
    Args:
        scan_in: Scan data
        db: Database session
        current_user: Current user from auth dependency
        
    Returns:
        ScanHistory: Created scan history entry
        
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


@router.get("/favorites", response_model=List[UserFavorite])
def get_user_favorites(
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
    return (
        db.query(db_models.UserFavorite)
        .filter(db_models.UserFavorite.user_id == current_user.id)
        .all()
    )


@router.post("/favorites", response_model=UserFavorite)
def add_favorite(
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
        current_user: Current user from auth dependency
        
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