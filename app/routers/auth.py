"""Authentication router for the MeatWise API."""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models import Token, UserCreate
from app.core import security
from app.core.config import settings
from app.core.supabase import supabase
from app.db import models as db_models
from app.db.session import get_db

router = APIRouter()


@router.post("/login", response_model=Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    Args:
        form_data: OAuth2 password request form
        
    Returns:
        Token: Access token
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Check if Supabase client is initialized
        if not supabase or not hasattr(supabase, 'auth'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable. Please try again later.",
            )
            
        # Use Supabase to sign in with email and password
        response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password,
        })
        
        # Check for errors - response object structure depends on Supabase version
        if hasattr(response, 'error') and response.error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=response.error.message,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Ensure session exists before accessing it
        if not hasattr(response, 'session') or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "access_token": response.session.access_token,
            "token_type": "bearer",
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=Token)
def register_user(
    user_in: UserCreate,
) -> Any:
    """
    Register a new user and return an access token.
    
    Args:
        user_in: User creation data
        
    Returns:
        Token: Access token
        
    Raises:
        HTTPException: If user already exists or registration fails
    """
    try:
        # Check if Supabase client is initialized
        if not supabase or not hasattr(supabase, 'auth'):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Registration service unavailable. Please try again later.",
            )
            
        # Use Supabase to sign up with email and password
        response = supabase.auth.sign_up({
            "email": user_in.email,
            "password": user_in.password,
            "options": {
                "data": {
                    "full_name": user_in.full_name,
                    "role": "basic",
                }
            }
        })
        
        # Safer error checking - don't assume response structure
        # Check if there's an error dict or attribute in the response
        if hasattr(response, 'error') and response.error:
            error_message = getattr(response.error, 'message', str(response.error))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {error_message}",
            )
        
        # Check if the session is None, which means the user needs to confirm their email
        if hasattr(response, 'session'):
            if not response.session:
                return {
                    "access_token": "",
                    "token_type": "bearer",
                    "message": "Please confirm your email address to complete registration"
                }
            
            return {
                "access_token": response.session.access_token,
                "token_type": "bearer",
            }
        
        # If we can't determine the session state, return a generic success
        return {
            "access_token": "",
            "token_type": "bearer",
            "message": "Registration processed successfully. Please check your email for confirmation."
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        ) 