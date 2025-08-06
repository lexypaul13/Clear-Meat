"""API router for the MeatWise API."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, products, users, product_count, performance, ingredients

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(ingredients.router, prefix="/ingredients", tags=["ingredients"])
api_router.include_router(product_count.router, prefix="/stats", tags=["stats"]) 
api_router.include_router(performance.router, prefix="/performance", tags=["performance"]) 