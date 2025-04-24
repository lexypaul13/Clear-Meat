from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import jwt
import os
from dotenv import load_dotenv
import random
from app.api.routes.products import mock_products

# Load environment variables
load_dotenv()

# Get JWT secret from environment or use a default for development
JWT_SECRET = os.getenv("JWT_SECRET", "development_secret_key")
JWT_ALGORITHM = "HS256"

# Create router
router = APIRouter()

# Mock user database reference (in a real app, this would be imported from a database module)
from app.api.routes.auth import mock_users

# Models
class Preferences(BaseModel):
    dietary_preferences: List[str] = []
    cooking_experience: str = ""
    meat_preferences: List[str] = []

class UserPreferencesResponse(BaseModel):
    preferences: Preferences

# Helper function to get user from token
def get_user_from_token(authorization: Optional[str] = Header(None)):
    """Get user from authorization token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        
        # Check if user exists
        if email not in mock_users:
            raise HTTPException(status_code=401, detail="User not found")
        
        return mock_users[email]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(user = Depends(get_user_from_token)):
    """Get user preferences"""
    return {"preferences": user.get("preferences", {})}

@router.post("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(preferences: Preferences, user = Depends(get_user_from_token)):
    """Update user preferences"""
    # In a real app, this would update the database
    mock_users[user["email"]]["preferences"] = preferences.dict()
    return {"preferences": mock_users[user["email"]]["preferences"]}

@router.get("/recommendations", response_model=List[Dict[str, Any]])
async def get_recommendations(user = Depends(get_user_from_token)):
    """Get personalized product recommendations"""
    user_prefs = user.get("preferences", {})
    meat_preferences = user_prefs.get("meat_preferences", [])
    
    # Filter products by user's meat preferences
    if meat_preferences:
        recommended_products = [p for p in mock_products if p["meat_type"] in meat_preferences]
    else:
        # If no preferences, return random products
        recommended_products = random.sample(mock_products, min(4, len(mock_products)))
    
    # Sort by recommendation relevance (mocked for demo)
    # In a real app, this would be based on a more sophisticated algorithm
    recommended_products = sorted(recommended_products, key=lambda p: random.random())
    
    # Return top 4 products
    return recommended_products[:4]

@router.get("/explore", response_model=List[Dict[str, Any]])
async def explore_products(user = Depends(get_user_from_token)):
    """Get AI-powered product exploration recommendations"""
    # In a real app, this would use Gemini AI to generate personalized recommendations
    
    # Mock exploration recommendations based on user preferences
    user_prefs = user.get("preferences", {})
    dietary_preferences = user_prefs.get("dietary_preferences", [])
    cooking_experience = user_prefs.get("cooking_experience", "Beginner")
    
    # Get all products
    all_products = mock_products.copy()
    
    # Sort by relevance to the user (mocked)
    # In a real app, this would use a sophisticated algorithm
    random.shuffle(all_products)
    
    # Add mock relevance score
    for product in all_products:
        product["relevance_score"] = random.uniform(0.5, 1.0)
    
    # Sort by relevance score
    all_products.sort(key=lambda p: p["relevance_score"], reverse=True)
    
    # Return top products
    return all_products[:6] 