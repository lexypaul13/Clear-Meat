"""Ingredient endpoints for the MeatWise API."""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1 import models
from app.db import models as db_models
from app.db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[models.Ingredient])
def get_ingredients(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> Any:
    """
    Retrieve ingredients with optional filtering.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        category: Filter by category
        risk_level: Filter by risk level
        
    Returns:
        List[models.Ingredient]: List of ingredients
    """
    query = db.query(db_models.Ingredient)
    
    # Apply filters
    if category:
        query = query.filter(db_models.Ingredient.category == category)
    if risk_level:
        query = query.filter(db_models.Ingredient.risk_level == risk_level)
    
    return query.offset(skip).limit(limit).all()


@router.get("/{ingredient_id}", response_model=models.Ingredient)
def get_ingredient(
    ingredient_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific ingredient by ID.
    
    Args:
        ingredient_id: Ingredient ID
        db: Database session
        
    Returns:
        models.Ingredient: Ingredient details
        
    Raises:
        HTTPException: If ingredient not found
    """
    ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.post("/", response_model=models.Ingredient)
def create_ingredient(
    ingredient_in: models.IngredientCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Create a new ingredient.
    
    Args:
        ingredient_in: Ingredient data
        db: Database session
        
    Returns:
        models.Ingredient: Created ingredient
        
    Raises:
        HTTPException: If ingredient with same name already exists
    """
    ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.name == ingredient_in.name).first()
    if ingredient:
        raise HTTPException(status_code=400, detail="Ingredient with this name already exists")
    
    ingredient = db_models.Ingredient(**ingredient_in.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/{ingredient_id}", response_model=models.Ingredient)
def update_ingredient(
    ingredient_id: str,
    ingredient_in: models.IngredientCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Update an ingredient.
    
    Args:
        ingredient_id: Ingredient ID
        ingredient_in: Updated ingredient data
        db: Database session
        
    Returns:
        models.Ingredient: Updated ingredient
        
    Raises:
        HTTPException: If ingredient not found
    """
    ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Check if name is being changed and if it conflicts with existing ingredient
    if ingredient_in.name != ingredient.name:
        existing = db.query(db_models.Ingredient).filter(db_models.Ingredient.name == ingredient_in.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ingredient with this name already exists")
    
    update_data = ingredient_in.model_dump()
    for key, value in update_data.items():
        setattr(ingredient, key, value)
    
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/{ingredient_id}")
def delete_ingredient(
    ingredient_id: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Delete an ingredient.
    
    Args:
        ingredient_id: Ingredient ID
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If ingredient not found
    """
    ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    db.delete(ingredient)
    db.commit()
    return {"message": "Ingredient deleted successfully"} 