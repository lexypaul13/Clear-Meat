"""User endpoints for the MeatWise API."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1 import models
from app.core import security
from app.db import models as db_models
from app.db.session import get_db

router = APIRouter()


@router.get("/me", response_model=models.User)
def get_current_user(
    db: Session = Depends(get_db),
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
) -> Any:
    """
    Get current user.
    
    Args:
        db: Database session
        current_user_id: Current user ID from auth dependency
        
    Returns:
        models.User: Current user details
        
    Raises:
        HTTPException: If user not found
    """
    user = db.query(db_models.User).filter(db_models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/me", response_model=models.User)
def update_current_user(
    user_in: models.UserUpdate,
    db: Session = Depends(get_db),
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
) -> Any:
    """
    Update current user.
    
    Args:
        user_in: Updated user data
        db: Database session
        current_user_id: Current user ID from auth dependency
        
    Returns:
        models.User: Updated user details
        
    Raises:
        HTTPException: If user not found
    """
    user = db.query(db_models.User).filter(db_models.User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = security.get_password_hash(update_data["password"])
        del update_data["password"]
    
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/history", response_model=List[models.ScanHistory])
def get_user_scan_history(
    db: Session = Depends(get_db),
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get current user's scan history.
    
    Args:
        db: Database session
        current_user_id: Current user ID from auth dependency
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[models.ScanHistory]: User's scan history
    """
    return (
        db.query(db_models.ScanHistory)
        .filter(db_models.ScanHistory.user_id == current_user_id)
        .order_by(db_models.ScanHistory.scanned_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/history", response_model=models.ScanHistory)
def add_scan_history(
    scan_in: models.ScanHistoryCreate,
    db: Session = Depends(get_db),
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
) -> Any:
    """
    Add a scan to user's history.
    
    Args:
        scan_in: Scan data
        db: Database session
        current_user_id: Current user ID from auth dependency
        
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
        user_id=current_user_id,
        **scan_in.model_dump(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/favorites", response_model=List[models.UserFavorite])
def get_user_favorites(
    db: Session = Depends(get_db),
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
) -> Any:
    """
    Get current user's favorite products.
    
    Args:
        db: Database session
        current_user_id: Current user ID from auth dependency
        
    Returns:
        List[models.UserFavorite]: User's favorite products
    """
    return (
        db.query(db_models.UserFavorite)
        .filter(db_models.UserFavorite.user_id == current_user_id)
        .all()
    )


@router.post("/favorites", response_model=models.UserFavorite)
def add_favorite(
    favorite_in: models.UserFavoriteCreate,
    db: Session = Depends(get_db),
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
) -> Any:
    """
    Add a product to user's favorites.
    
    Args:
        favorite_in: Favorite data
        db: Database session
        current_user_id: Current user ID from auth dependency
        
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
            db_models.UserFavorite.user_id == current_user_id,
            db_models.UserFavorite.product_code == favorite_in.product_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Product already in favorites")
    
    favorite = db_models.UserFavorite(
        user_id=current_user_id,
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
    # TODO: Implement proper authentication dependency
    current_user_id: str = "current_user_id",
) -> Any:
    """
    Remove a product from user's favorites.
    
    Args:
        product_code: Product barcode
        db: Database session
        current_user_id: Current user ID from auth dependency
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If favorite not found
    """
    favorite = (
        db.query(db_models.UserFavorite)
        .filter(
            db_models.UserFavorite.user_id == current_user_id,
            db_models.UserFavorite.product_code == product_code,
        )
        .first()
    )
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    db.delete(favorite)
    db.commit()
    return {"message": "Favorite removed successfully"} 