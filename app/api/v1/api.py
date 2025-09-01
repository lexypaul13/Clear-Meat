"""API router for the MeatWise API."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, products, users, product_count, ingredients
# Temporarily disabled performance endpoint due to import error
# from app.api.v1.endpoints import performance

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(ingredients.router, prefix="/ingredients", tags=["ingredients"])
api_router.include_router(product_count.router, prefix="/stats", tags=["stats"]) 
# Temporarily disabled due to import error: ModuleNotFoundError: No module named 'app.api.deps'
# api_router.include_router(performance.router, prefix="/performance", tags=["performance"]) 