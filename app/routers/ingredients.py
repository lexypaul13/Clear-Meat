"""Ingredient router for the MeatWise API (BACKUP BEFORE DELETION).

This file is being kept as a backup only and should be deleted after 
confirming the migration was successful. 

Original endpoint functionality:
- GET /api/v1/ingredients/ - List all ingredients with filtering
- GET /api/v1/ingredients/{ingredient_id} - Get specific ingredient details
"""

from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models import Ingredient
from app.db import models as db_models
from app.db.session import get_db

router = APIRouter()


@router.get("/", response_model=List[Ingredient])
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
        List[Ingredient]: List of ingredients
    """
    query = db.query(db_models.Ingredient)
    
    # Apply filters
    if category:
        query = query.filter(db_models.Ingredient.category == category)
    if risk_level:
        query = query.filter(db_models.Ingredient.risk_level == risk_level)
    
    # Get ingredients from database
    db_ingredients = query.offset(skip).limit(limit).all()
    
    # Manually create Pydantic models to ensure UUID is converted to string
    result = []
    for db_ingredient in db_ingredients:
        ingredient = Ingredient(
            id=str(db_ingredient.id),
            name=db_ingredient.name,
            description=db_ingredient.description,
            category=db_ingredient.category,
            risk_level=db_ingredient.risk_level,
            concerns=db_ingredient.concerns,
            alternatives=db_ingredient.alternatives,
            created_at=db_ingredient.created_at,
            updated_at=db_ingredient.updated_at
        )
        result.append(ingredient)
    
    return result


@router.get("/{ingredient_id}", response_model=Ingredient)
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
        Ingredient: Ingredient details
        
    Raises:
        HTTPException: If ingredient not found
    """
    db_ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not db_ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Manually create Pydantic model to ensure UUID is converted to string
    ingredient = Ingredient(
        id=str(db_ingredient.id),
        name=db_ingredient.name,
        description=db_ingredient.description,
        category=db_ingredient.category,
        risk_level=db_ingredient.risk_level,
        concerns=db_ingredient.concerns,
        alternatives=db_ingredient.alternatives,
        created_at=db_ingredient.created_at,
        updated_at=db_ingredient.updated_at
    )
    
    return ingredient 