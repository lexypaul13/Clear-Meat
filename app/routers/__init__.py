"""Routers package."""

from fastapi import APIRouter

from app.routers import users, auth
from app.api.v1.endpoints.products import router as products_router

# Create API router
api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
