"""MeatWise API application package."""

from app.models import Product, Ingredient, AdditiveInfo

# Rebuild models to resolve circular dependencies
Ingredient.model_rebuild()
Product.model_rebuild()
AdditiveInfo.model_rebuild() 