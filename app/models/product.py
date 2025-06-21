"""Product models for the MeatWise API."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

# Fix imports to directly import AdditiveInfo
from app.models.ingredient import AdditiveInfo


class ProductBase(BaseModel):
    """Base Product model."""
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    ingredients_text: Optional[str] = None
    
    # Nutritional information
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None
    
    # Meat-specific information
    meat_type: Optional[str] = None
    
    # Risk rating
    risk_rating: Optional[str] = None
    
    # Additional fields
    image_url: Optional[str] = None
    image_data: Optional[str] = None


class ProductCreate(ProductBase):
    """Product creation model."""
    code: str


class ProductUpdate(ProductBase):
    """Product update model."""
    pass


class ProductInDB(ProductBase):
    """Product database model."""
    code: str
    last_updated: datetime
    created_at: datetime


class Product(ProductInDB):
    """Product response model."""

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {
            # Handle SQLAlchemy UUID objects
            "UUID": lambda v: str(v),
        }
    }


class ProductNutrition(BaseModel):
    """Nutrition information model."""
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None


class ProductCriteria(BaseModel):
    """Product criteria model."""
    risk_rating: Optional[str] = None
    additives: Optional[List[AdditiveInfo]] = Field(default_factory=list)


class ProductHealth(BaseModel):
    """Product health model."""
    nutrition: Optional[ProductNutrition] = None
    health_concerns: Optional[List[str]] = None


class ProductEnvironment(BaseModel):
    """Product environment model."""
    impact: Optional[str] = None
    details: Optional[str] = None
    sustainability_practices: Optional[List[str]] = None


class ProductInfo(BaseModel):
    """Basic product information model."""
    code: str
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    ingredients_text: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[str] = None
    meat_type: Optional[str] = None


class ProductMetadata(BaseModel):
    """Product metadata model."""
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None


class PersonalizedInsight(BaseModel):
    """Personalized insights for a product based on user preferences."""
    health_risks: List[Dict[str, str]] = Field(default_factory=list)
    flagged_ingredients: List[Dict[str, str]] = Field(default_factory=list)
    alternatives: List[Dict[str, str]] = Field(default_factory=list)


class ProductStructured(BaseModel):
    """Structured product response model."""
    product: ProductInfo
    criteria: ProductCriteria
    health: ProductHealth
    environment: ProductEnvironment
    metadata: ProductMetadata
    personalized_insights: Optional[PersonalizedInsight] = None


# Health Assessment Models
class RiskSummary(BaseModel):
    """Risk summary model for health assessment."""
    grade: str
    color: str


class Citation(BaseModel):
    """Citation entry for health assessment."""
    id: int
    title: str
    source: str
    year: str


class NutritionInsight(BaseModel):
    """Nutrition insight for a specific nutrient."""
    nutrient: str
    amount_per_serving: str
    evaluation: str  # "high", "moderate", "low"
    ai_commentary: str  # ≤160 characters


class IngredientAssessment(BaseModel):
    """Assessment model for categorizing ingredients by risk level."""
    high_risk: List[Dict[str, Any]] = Field(default_factory=list)
    moderate_risk: List[Dict[str, Any]] = Field(default_factory=list)
    low_risk: List[Dict[str, Any]] = Field(default_factory=list)


class ProductRecommendation(BaseModel):
    """Product recommendation model for healthier alternatives."""
    code: str
    name: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    summary: str
    nutrition_highlights: List[str] = Field(default_factory=list)
    risk_rating: str


class HealthAssessment(BaseModel):
    """Complete health assessment for a product."""
    summary: str
    risk_summary: RiskSummary
    ingredients_assessment: IngredientAssessment
    nutrition_insights: List[NutritionInsight] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)