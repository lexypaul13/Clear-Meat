"""Product count endpoint for the MeatWise API."""

from typing import Any, Dict
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.connection import get_db, is_using_local_db

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

@router.get("/count", response_model=Dict[str, int])
def get_product_count(
    db: Session = Depends(get_db),
) -> Any:
    """
    Get the total count of products in the database using a direct SQL query.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, int]: Total count of products
    """
    try:
        logger.info(f"Getting product count (using local DB: {is_using_local_db()})")
        
        # Use a direct SQL query to avoid ORM issues
        query = text("SELECT COUNT(*) FROM products")
        result = db.execute(query).scalar()
        
        return {"count": result or 0}
    except Exception as e:
        logger.error(f"Error getting product count: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting product count: {str(e)}"
        ) 