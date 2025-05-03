from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import os
from supabase import create_client, Client
from app.db.supabase import get_supabase
from app.core.config import settings

# Use settings for JWT parameters
JWT_ALGORITHM = settings.ALGORITHM
JWT_EXPIRATION_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Create router
router = APIRouter()

# Models
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    token: str
    preferences: Optional[Dict[str, Any]] = None

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    # Use settings.SECRET_KEY for encoding, as JWT_SECRET is not defined in Settings model
    # Alternatively, add JWT_SECRET to Settings model if it's different from SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=UserResponse)
async def login(user_data: UserLogin):
    """Login endpoint using Supabase Auth"""
    try:
        # Get Supabase client
        supabase: Client = get_supabase()
        
        # Sign in with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        # Get user data from profiles table
        user = auth_response.user
        profile = supabase.table('profiles').select('*').eq('id', user.id).single().execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Create access token
        token = create_access_token({"sub": user.id})
        
        # Return user data with token
        return {
            "id": user.id,
            "name": profile.data["full_name"],
            "email": user.email,
            "token": token,
            "preferences": profile.data.get("preferences", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """Register endpoint using Supabase Auth"""
    try:
        # Get Supabase client
        supabase: Client = get_supabase()
        
        # Sign up with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        
        user = auth_response.user
        
        # Create profile in profiles table
        profile = supabase.table('profiles').insert({
            "id": user.id,
            "email": user_data.email,
            "full_name": user_data.name,
            "preferences": {
                "dietary_preferences": [],
                "cooking_experience": "",
                "meat_preferences": []
            }
        }).execute()
        
        # Create access token
        token = create_access_token({"sub": user.id})
        
        # Return user data with token
        return {
            "id": user.id,
            "name": user_data.name,
            "email": user_data.email,
            "token": token,
            "preferences": profile.data[0].get("preferences", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 