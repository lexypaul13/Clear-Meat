"""User routes for the MeatWise API."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.db.supabase import get_supabase

router = APIRouter()

class UserPreferences(BaseModel):
    """User preferences model."""
    dietary_preferences: List[str]
    cooking_experience: str
    meat_preferences: List[str]

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
            "preferences": preferences.dict()
        }).eq('id', user.id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return {"preferences": response.data[0]["preferences"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations")
async def get_recommendations():
    """Get personalized product recommendations."""
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
        meat_preferences = preferences.get("meat_preferences", [])
        
        # Get recommended products based on preferences
        if meat_preferences:
            response = supabase.table('products').select('*').in_('meat_type', meat_preferences).limit(4).execute()
        else:
            response = supabase.table('products').select('*').limit(4).execute()
            
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
    """Get AI-powered recommendations based on user preferences and history."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Get user preferences and history
        profile = supabase.table('profiles').select('preferences').eq('id', user.id).single().execute()
        history = supabase.table('user_history').select(
            'products(meat_type)'
        ).eq('user_id', user.id).limit(10).execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        # Extract meat types from history
        meat_types = [item["products"]["meat_type"] for item in history.data]
        
        # Get recommendations based on most viewed meat types
        if meat_types:
            from collections import Counter
            most_common = Counter(meat_types).most_common(2)
            preferred_types = [meat_type for meat_type, _ in most_common]
            
            response = supabase.table('products').select('*').in_('meat_type', preferred_types).limit(4).execute()
            return response.data
            
        # Fall back to preference-based recommendations
        return await get_recommendations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 