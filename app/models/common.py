"""Common models shared across the application."""

from typing import Generic, TypeVar, List, Optional, Dict, Any
from pydantic import BaseModel, Field, conint

# Type for paginated model objects
T = TypeVar('T')


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    
    page: conint(ge=1) = Field(1, description="Page number, starting from 1")
    page_size: conint(ge=1, le=100) = Field(20, description="Number of items per page, max 100")
    

class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated response format."""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )


class StatusResponse(BaseModel):
    """Standard status response."""
    
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None 