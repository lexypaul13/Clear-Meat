"""Models package."""

# First import the basic models without circular dependencies
from app.models.ingredient import (
    AdditiveInfo,
    Ingredient,
    IngredientBase,
    IngredientCreate,
    IngredientUpdate,
)

# Then import models with possible references to the above
from app.models.product import (
    Product,
    ProductBase,
    ProductCreate,
    ProductCriteria,
    ProductEnvironment,
    ProductHealth,
    ProductInfo,
    ProductInDB,
    ProductMetadata,
    ProductNutrition,
    ProductStructured,
    ProductUpdate,
)

# Finally import models that reference both of the above
from app.models.user import (
    ScanHistory,
    ScanHistoryBase,
    ScanHistoryCreate,
    Token,
    TokenPayload,
    User,
    UserBase,
    UserCreate,
    UserFavorite,
    UserFavoriteBase,
    UserFavoriteCreate,
    UserUpdate,
)

# Update forward references after all models are imported
from app.models.product import Product
Product.model_rebuild()

from app.models.user import ScanHistory, UserFavorite
ScanHistory.model_rebuild()
UserFavorite.model_rebuild()
