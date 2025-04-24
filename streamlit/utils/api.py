"""API utilities for the MeatWise Streamlit frontend."""

import requests
import json
from typing import Optional, Dict, Any
import streamlit as st
from app.db.supabase import get_supabase

# API base URL - using direct Supabase access instead of FastAPI
supabase = get_supabase()

def get_headers() -> Dict[str, str]:
    """Get headers with authentication token if available"""
    headers = {
        "Content-Type": "application/json"
    }
    
    if "user_data" in st.session_state and "token" in st.session_state.user_data:
        headers["Authorization"] = f"Bearer {st.session_state.user_data['token']}"
    
    return headers

def login(email: str, password: str) -> Dict[str, Any]:
    """Login user using Supabase auth"""
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        user = auth_response.user
        profile = supabase.table('profiles').select('*').eq('id', user.id).single().execute()
        
        return {
            "id": user.id,
            "name": profile.data["full_name"],
            "email": user.email,
            "token": auth_response.session.access_token,
            "preferences": profile.data.get("preferences", {})
        }
    except Exception as e:
        raise Exception(f"Login failed: {str(e)}")

def register(name: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user using Supabase auth"""
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        user = auth_response.user
        
        # Create profile
        profile = supabase.table('profiles').insert({
            "id": user.id,
            "email": email,
            "full_name": name,
            "preferences": {
                "dietary_preferences": [],
                "cooking_experience": "",
                "meat_preferences": []
            }
        }).execute()
        
        return {
            "id": user.id,
            "name": name,
            "email": email,
            "token": auth_response.session.access_token,
            "preferences": profile.data[0].get("preferences", {})
        }
    except Exception as e:
        raise Exception(f"Registration failed: {str(e)}")

def save_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Save user preferences to Supabase"""
    try:
        if "user_data" not in st.session_state:
            raise Exception("User not logged in")
            
        user_id = st.session_state.user_data["id"]
        
        response = supabase.table('profiles').update({
            "preferences": preferences
        }).eq('id', user_id).execute()
        
        return {"preferences": response.data[0]["preferences"]}
    except Exception as e:
        raise Exception(f"Failed to save preferences: {str(e)}")

def get_products(search_query: str = "", meat_type: str = "All", 
                min_price: float = 0, max_price: float = 50) -> list:
    """Get products from Supabase with filtering"""
    try:
        query = supabase.table('products').select('*')
        
        if search_query:
            query = query.ilike('name', f'%{search_query}%')
        if meat_type != "All":
            query = query.eq('meat_type', meat_type)
        if min_price > 0:
            query = query.gte('price', min_price)
        if max_price < 50:
            query = query.lte('price', max_price)
            
        response = query.execute()
        return response.data
    except Exception as e:
        raise Exception(f"Failed to fetch products: {str(e)}")

def get_product(product_id: int) -> Dict[str, Any]:
    """Get a single product by ID"""
    try:
        response = supabase.table('products').select('*').eq('id', product_id).single().execute()
        return response.data
    except Exception as e:
        raise Exception(f"Failed to fetch product: {str(e)}")

def get_recommendations() -> list:
    """Get personalized product recommendations"""
    try:
        if "user_data" not in st.session_state:
            return []
            
        user_id = st.session_state.user_data["id"]
        profile = supabase.table('profiles').select('preferences').eq('id', user_id).single().execute()
        preferences = profile.data.get("preferences", {})
        meat_preferences = preferences.get("meat_preferences", [])
        
        if meat_preferences:
            response = supabase.table('products').select('*').in_('meat_type', meat_preferences).limit(4).execute()
        else:
            response = supabase.table('products').select('*').limit(4).execute()
            
        return response.data
    except Exception as e:
        raise Exception(f"Failed to fetch recommendations: {str(e)}")

def get_user_history() -> list:
    """Get user's product viewing history"""
    try:
        if "user_data" not in st.session_state:
            return []
            
        user_id = st.session_state.user_data["id"]
        response = supabase.table('user_history').select(
            'products(*)'
        ).eq('user_id', user_id).order('viewed_at', desc=True).limit(5).execute()
        
        return [item["products"] for item in response.data]
    except Exception as e:
        raise Exception(f"Failed to fetch user history: {str(e)}")

def add_to_history(product_id: int) -> None:
    """Add a product to user's viewing history"""
    try:
        if "user_data" not in st.session_state:
            return
            
        user_id = st.session_state.user_data["id"]
        supabase.table('user_history').insert({
            "user_id": user_id,
            "product_id": product_id
        }).execute()
    except Exception as e:
        raise Exception(f"Failed to add to history: {str(e)}")

def get_ai_recommendations() -> list:
    """Get AI-powered recommendations based on user preferences and history"""
    try:
        if "user_data" not in st.session_state:
            return []
            
        user_id = st.session_state.user_data["id"]
        
        # Get user preferences and history
        profile = supabase.table('profiles').select('preferences').eq('id', user_id).single().execute()
        history = supabase.table('user_history').select(
            'products(meat_type)'
        ).eq('user_id', user_id).limit(10).execute()
        
        # Extract meat types from history
        meat_types = [item["products"]["meat_type"] for item in history.data]
        
        # Get recommendations based on most viewed meat types
        if meat_types:
            from collections import Counter
            most_common = Counter(meat_types).most_common(2)
            preferred_types = [meat_type for meat_type, _ in most_common]
            
            response = supabase.table('products').select('*').in_('meat_type', preferred_types).limit(4).execute()
            return response.data
            
        return get_recommendations()  # Fall back to preference-based recommendations
    except Exception as e:
        raise Exception(f"Failed to fetch AI recommendations: {str(e)}") 