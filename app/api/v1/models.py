"""Pydantic models for the MeatWise API."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, EmailStr


# Product models
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
    
    # Image fields
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
    # Removed ingredients field

    class Config:
        """Pydantic config."""
        from_attributes = True


class ProductAlternative(BaseModel):
    """Product alternative model."""
    product_code: str
    alternative_code: str
    similarity_score: float
    reason: Optional[str] = None
    alternative: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# User models
class UserBase(BaseModel):
    """Base User model."""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserUpdate(UserBase):
    """User update model."""
    password: Optional[str] = None


class User(UserBase):
    """User response model."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""
        from_attributes = True


# Token models
class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str
    message: Optional[str] = None


class TokenPayload(BaseModel):
    """Token payload model."""
    sub: Optional[str] = None


# Scan history models
class ScanHistoryBase(BaseModel):
    """Base Scan History model."""
    product_code: str
    location: Optional[Dict[str, Any]] = None
    device_info: Optional[str] = None


class ScanHistoryCreate(ScanHistoryBase):
    """Scan History creation model."""
    pass


class ScanHistory(ScanHistoryBase):
    """Scan History response model."""
    id: str
    user_id: str
    scanned_at: datetime
    product: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# User favorite models
class UserFavoriteBase(BaseModel):
    """Base User Favorite model."""
    product_code: str
    notes: Optional[str] = None


class UserFavoriteCreate(UserFavoriteBase):
    """User Favorite creation model."""
    pass


class UserFavorite(UserFavoriteBase):
    """User Favorite response model."""
    user_id: str
    added_at: datetime
    product: Optional[Product] = None

    class Config:
        """Pydantic config."""
        from_attributes = True


# Structured product response models
class ProductNutrition(BaseModel):
    """Nutrition information model."""
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrates: Optional[float] = None
    salt: Optional[float] = None


class AdditiveInfo(BaseModel):
    """Additive information model."""
    name: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    concerns: Optional[List[str]] = None
    alternatives: Optional[List[str]] = None


class ProductCriteria(BaseModel):
    """Product criteria model."""
    risk_rating: Optional[str] = None
    additives: Optional[List[AdditiveInfo]] = None


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


class ProductStructured(BaseModel):
    """Structured product response model."""
    product: ProductInfo
    criteria: ProductCriteria
    health: ProductHealth
    environment: ProductEnvironment
    metadata: ProductMetadata


# Problem report models
class ProductProblemReport(BaseModel):
    """Product problem report model."""
    problem_type: str = Field(..., description="Type of problem (incorrect_info, missing_info, other)")
    description: str = Field(..., description="Description of the problem")
    reporter_email: Optional[EmailStr] = Field(None, description="Email of the person reporting the problem")
    want_feedback: Optional[bool] = Field(False, description="Whether the reporter wants to be contacted about the resolution")
    report_id: Optional[str] = None 


class ProductMatch(BaseModel):
    """Details about why a product matches user preferences."""
    matches: List[str] = Field(
        default_factory=list,
        description="List of ways the product matches user preferences"
    )
    concerns: List[str] = Field(
        default_factory=list,
        description="List of concerns or non-matches with user preferences"
    )


class RecommendedProduct(BaseModel):
    """Product with recommendation details."""
    product: Product
    match_details: ProductMatch
    match_score: Optional[float] = Field(
        None,
        description="Numerical score representing how well this product matches preferences"
    )


class RecommendationResponse(BaseModel):
    """Response model for product recommendations."""
    recommendations: List[RecommendedProduct]
    total_matches: int = Field(
        ...,
        description="Total number of products that match the criteria (before pagination)"
    )


# Health Assessment Models
class RiskSummary(BaseModel):
    """Risk summary model for health assessment."""
    grade: str
    color: str


class WorksCited(BaseModel):
    """Works cited entry for health assessment."""
    id: int
    citation: str


class IngredientReport(BaseModel):
    """Detailed report for a specific ingredient."""
    title: str
    summary: str
    health_concerns: List[str] = Field(default_factory=list)
    common_uses: str
    citations: Dict[str, str] = Field(default_factory=dict)


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
    nutrition_labels: List[str] = Field(default_factory=list)
    ingredients_assessment: IngredientAssessment
    ingredient_reports: Dict[str, IngredientReport] = Field(default_factory=dict)
    works_cited: List[WorksCited] = Field(default_factory=list)
    recommendations: List[ProductRecommendation] = Field(default_factory=list)
    source_disclaimer: Optional[str] = None
    real_citations: Optional[Dict[str, str]] = Field(default_factory=dict)


class Citation(BaseModel):
    """Scientific citation model."""
    id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    source: str
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None
    formatted: Optional[str] = None


class EnhancedHealthAssessment(BaseModel):
    """Enhanced health assessment with richer citation data."""
    summary: str
    risk_summary: RiskSummary
    nutrition_labels: List[str] = Field(default_factory=list)
    ingredients_assessment: IngredientAssessment
    citations: List[Citation] = Field(default_factory=list)
    healthier_alternatives: List[ProductRecommendation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Social Authentication Models
class SocialAuthRequest(BaseModel):
    """Social authentication request model."""
    provider: str = Field(..., description="OAuth provider (google, facebook, apple, twitter)")
    redirect_url: Optional[str] = Field(None, description="URL to redirect to after authentication")


class PhoneAuthRequest(BaseModel):
    """Phone authentication request model."""
    phone: str = Field(..., description="Phone number in international format (+1234567890)")


class PhoneVerifyRequest(BaseModel):
    """Phone verification request model."""
    phone: str = Field(..., description="Phone number in international format")
    token: str = Field(..., description="OTP token received via SMS")


class SocialAuthResponse(BaseModel):
    """Social authentication response model."""
    auth_url: str = Field(..., description="URL to redirect user for OAuth authentication")
    provider: str = Field(..., description="OAuth provider name") 