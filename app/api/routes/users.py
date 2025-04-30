"""User routes for the MeatWise API."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.db.supabase import get_supabase

router = APIRouter()

class UserPreferences(BaseModel):
    """User preferences model with fields matching onboarding process."""
    # Screen 1: Nutrition Priorities
    nutrition_focus: Optional[str] = None  # "protein", "fat", "salt"
    
    # Screen 2: Additives and Preservatives
    avoid_preservatives: Optional[bool] = None  # True/False
    
    # Screen 3: Antibiotics and Hormones in Raising
    prefer_antibiotic_free: Optional[bool] = None  # True/False
    
    # Screen 4: Sourcing & Animal Diet
    prefer_grass_fed: Optional[bool] = None  # True/False
    
    # Screen 5: Typical Cooking Style
    cooking_style: Optional[str] = None  # "grilling", "pan_frying", "oven_slow_cooker"
    
    # Screen 6: Openness to Meat Alternatives
    open_to_alternatives: Optional[bool] = None  # True/False
    
    # Legacy fields (keeping for backward compatibility)
    dietary_preferences: Optional[List[str]] = None
    cooking_experience: Optional[str] = None
    meat_preferences: Optional[List[str]] = None

class UserHistory(BaseModel):
    """User history model."""
    product_id: int
    viewed_at: str

@router.get("/preferences")
async def get_preferences():
    """Get user preferences."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('profiles').select(
            'preferences'
        ).eq('id', user.id).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return {"preferences": response.data.get("preferences", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preferences")
async def save_preferences(preferences: UserPreferences):
    """Save user preferences."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('profiles').update({
            "preferences": preferences.model_dump(exclude_none=True)
        }).eq('id', user.id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return {"preferences": response.data[0]["preferences"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations")
async def get_recommendations():
    """Get personalized product recommendations based on new preference model."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Get user preferences
        profile = supabase.table('profiles').select(
            'preferences'
        ).eq('id', user.id).single().execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        preferences = profile.data.get("preferences", {})
        
        # Build query conditions based on new preferences model
        query = supabase.table('products').select('*')
        
        # Apply filters based on nutrition focus
        nutrition_focus = preferences.get("nutrition_focus")
        if nutrition_focus == "protein":
            query = query.order('protein', desc=True)
        elif nutrition_focus == "fat":
            query = query.order('fat')
        elif nutrition_focus == "salt":
            query = query.order('salt')
            
        # Apply filters for additives and preservatives
        if preferences.get("avoid_preservatives") is True:
            query = query.eq('contains_preservatives', False)
            
        # Apply filters for antibiotics/hormones
        if preferences.get("prefer_antibiotic_free") is True:
            query = query.eq('antibiotic_free', True)
            query = query.eq('hormone_free', True)
            
        # Apply filters for grass-fed/pasture-raised
        if preferences.get("prefer_grass_fed") is True:
            query = query.eq('pasture_raised', True)
            
        # Legacy: Consider meat preferences if no new preferences set
        meat_preferences = preferences.get("meat_preferences", [])
        if meat_preferences and not any([
            nutrition_focus, 
            preferences.get("avoid_preservatives"), 
            preferences.get("prefer_antibiotic_free"),
            preferences.get("prefer_grass_fed")
        ]):
            query = query.in_('meat_type', meat_preferences)
            
        # Get results
        response = query.limit(4).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history():
    """Get user's product viewing history."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('user_history').select(
            'products(*)'
        ).eq('user_id', user.id).order('viewed_at', desc=True).limit(5).execute()
        
        return [item["products"] for item in response.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/history")
async def add_to_history(history: UserHistory):
    """Add a product to user's viewing history."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('user_history').insert({
            "user_id": user.id,
            "product_id": history.product_id,
            "viewed_at": history.viewed_at
        }).execute()
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/explore")
async def get_ai_recommendations():
    """Get AI-powered recommendations based on updated user preferences."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Get user preferences and history
        profile = supabase.table('profiles').select('preferences').eq('id', user.id).single().execute()
        history = supabase.table('user_history').select(
            'products(meat_type, id, name, brand)'
        ).eq('user_id', user.id).limit(10).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        preferences = profile.data.get("preferences", {})
        
        # Extract meat types from history
        meat_types = [item["products"]["meat_type"] for item in history.data if "products" in item and item["products"]]
        
        # Create base query
        query = supabase.table('products').select('*')
        
        # Apply preference-based filters
        # Nutrition focus
        nutrition_focus = preferences.get("nutrition_focus")
        if nutrition_focus == "protein":
            query = query.order('protein', desc=True)
        elif nutrition_focus == "fat":
            query = query.order('fat')
        elif nutrition_focus == "salt":
            query = query.order('salt')
            
        # Cooking style preferences
        cooking_style = preferences.get("cooking_style")
        if cooking_style:
            # Recommend products that work well with their cooking style
            # This is a simplification - you could have a cooking_method field in your DB
            # or use a more sophisticated algorithm
            pass
            
        # Filter alternatives based on preference
        if preferences.get("open_to_alternatives") is False:
            # Filter out plant-based alternatives
            # This assumes you have fields to identify alternatives
            query = query.eq('is_plant_based', False)
            
        # Additives preferences
        if preferences.get("avoid_preservatives") is True:
            query = query.eq('contains_preservatives', False)
            
        # Animal welfare preferences
        if preferences.get("prefer_antibiotic_free") is True:
            query = query.eq('antibiotic_free', True)
            
        if preferences.get("prefer_grass_fed") is True:
            query = query.eq('pasture_raised', True)
        
        # Combine with history-based results
        if meat_types:
            from collections import Counter
            most_common = Counter(meat_types).most_common(2)
            preferred_types = [meat_type for meat_type, _ in most_common]
            
            # Get products matching preferences AND preferred meat types
            meat_query = query.in_('meat_type', preferred_types).limit(4).execute()
            
            # Also get some other recommendations for variety
            variety_query = query.not_.in_('meat_type', preferred_types).limit(2).execute()
            
            # Combine results
            combined_results = meat_query.data + variety_query.data
            return combined_results[:4]  # Return max 4 recommendations
            
        # If no history, just use preference filters
        response = query.limit(4).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 