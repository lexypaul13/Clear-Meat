"""Ingredient router for the MeatWise API."""

from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models import Ingredient, IngredientCreate
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
    
    return query.offset(skip).limit(limit).all()


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
    ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return ingredient


@router.post("/", response_model=Ingredient)
def create_ingredient(
    ingredient_in: IngredientCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Create a new ingredient.
    
    Args:
        ingredient_in: Ingredient data
        db: Database session
        
    Returns:
        Ingredient: Created ingredient
        
    Raises:
        HTTPException: If ingredient already exists
    """
    # Check if ingredient with same name already exists
    db_ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.name == ingredient_in.name).first()
    if db_ingredient:
        raise HTTPException(
            status_code=400,
            detail="Ingredient with this name already exists"
        )
    
    # Create new ingredient
    from uuid import uuid4
    from datetime import datetime
    
    db_ingredient = db_models.Ingredient(
        id=str(uuid4()),
        name=ingredient_in.name,
        description=ingredient_in.description,
        category=ingredient_in.category,
        risk_level=ingredient_in.risk_level,
        concerns=ingredient_in.concerns,
        alternatives=ingredient_in.alternatives,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    
    return db_ingredient


@router.put("/{ingredient_id}", response_model=Ingredient)
def update_ingredient(
    ingredient_id: str,
    ingredient_in: IngredientCreate,
    db: Session = Depends(get_db),
) -> Any:
    """
    Update an ingredient.
    
    Args:
        ingredient_id: Ingredient ID
        ingredient_in: Updated ingredient data
        db: Database session
        
    Returns:
        Ingredient: Updated ingredient
        
    Raises:
        HTTPException: If ingredient not found or if there's a conflict
    """
    # Get the ingredient
    db_ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not db_ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Check if trying to update to a name that already exists
    if ingredient_in.name != db_ingredient.name:
        existing = db.query(db_models.Ingredient).filter(db_models.Ingredient.name == ingredient_in.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Ingredient with this name already exists"
            )
    
    # Update ingredient
    from datetime import datetime
    
    db_ingredient.name = ingredient_in.name
    db_ingredient.description = ingredient_in.description
    db_ingredient.category = ingredient_in.category
    db_ingredient.risk_level = ingredient_in.risk_level
    db_ingredient.concerns = ingredient_in.concerns
    db_ingredient.alternatives = ingredient_in.alternatives
    db_ingredient.updated_at = datetime.now()
    
    db.commit()
    db.refresh(db_ingredient)
    
    return db_ingredient


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
    # Get the ingredient
    db_ingredient = db.query(db_models.Ingredient).filter(db_models.Ingredient.id == ingredient_id).first()
    if not db_ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    # Check if ingredient is used in any products
    product_ingredients = db.query(db_models.ProductIngredient).filter(
        db_models.ProductIngredient.ingredient_id == ingredient_id
    ).first()
    
    if product_ingredients:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete ingredient that is used in products"
        )
    
    # Delete ingredient
    db.delete(db_ingredient)
    db.commit()
    
    return {"message": "Ingredient deleted successfully"} 