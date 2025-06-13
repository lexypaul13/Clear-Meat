"""Product count endpoint for the MeatWise API."""

from typing import Any, Dict
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.supabase_client import get_supabase_service

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

@router.get("/count", response_model=Dict[str, int])
def get_product_count(
    supabase_service = Depends(get_supabase_service),
) -> Any:
    """
    Get the total count of products in the database using Supabase.
    
    Args:
        supabase_service: Supabase service instance
        
    Returns:
        Dict[str, int]: Total count of products
    """
    try:
        logger.info("Getting product count from Supabase")
        
        # Use Supabase service to get count
        result = supabase_service.count_products()
        
        return {"count": result}
    except Exception as e:
        logger.error(f"Error getting product count: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting product count: {str(e)}"
        ) 