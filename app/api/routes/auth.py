from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get JWT secret from environment or use a default for development
JWT_SECRET = os.getenv("JWT_SECRET", "development_secret_key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24  # 24 hours

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
    id: int
    name: str
    email: str
    token: str
    preferences: Optional[Dict[str, Any]] = None

# Mock user database for demonstration
mock_users = {
    "demo@example.com": {
        "id": 1,
        "name": "Demo User",
        "email": "demo@example.com",
        "password": "password",  # In a real app, this would be hashed
        "preferences": {
            "dietary_preferences": ["Low Carb", "Low Sodium"],
            "cooking_experience": "Intermediate",
            "meat_preferences": ["Beef", "Poultry", "Pork"]
        }
    }
}

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=UserResponse)
async def login(user_data: UserLogin):
    """Login endpoint"""
    # Check if user exists
    if user_data.email not in mock_users:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check password
    user = mock_users[user_data.email]
    if user["password"] != user_data.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    token = create_access_token({"sub": user_data.email})
    
    # Return user data with token
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "token": token,
        "preferences": user.get("preferences", {})
    }

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """Register endpoint"""
    # Check if user already exists
    if user_data.email in mock_users:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user (in a real app, this would add to the database)
    user_id = len(mock_users) + 1
    mock_users[user_data.email] = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": user_data.password,  # In a real app, this would be hashed
        "preferences": {
            "dietary_preferences": [],
            "cooking_experience": "",
            "meat_preferences": []
        }
    }
    
    # Create access token
    token = create_access_token({"sub": user_data.email})
    
    # Return user data with token
    return {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "token": token,
        "preferences": mock_users[user_data.email].get("preferences", {})
    } 