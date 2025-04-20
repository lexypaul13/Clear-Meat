"""Authentication router for the MeatWise API."""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models import Token, UserCreate
from app.core import security
from app.core.config import settings
from app.core.supabase import supabase, admin_supabase
from app.db import models as db_models
from app.db.session import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


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
    Register a new user.
    
    Args:
        user_in: User data
        
    Returns:
        Token: Access token
        
    Raises:
        HTTPException: If registration fails
    """
            
    try:
        # Use the admin API to create a user directly
        if not admin_supabase:
            logger.error("Admin Supabase client not available for user creation")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create user. Server configuration error."
            )
            
        admin_response = admin_supabase.auth.admin.create_user({
            "email": user_in.email,
            "password": user_in.password,
            "user_metadata": {
                "full_name": user_in.full_name,
                "role": "basic"
            },
            "email_confirm": True,
            "ban_duration": "none"
        })
        
        if hasattr(admin_response, 'error') and admin_response.error:
            error_message = getattr(admin_response.error, 'message', str(admin_response.error))
            logger.error(f"Admin user creation failed: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {error_message}",
            )
        
        # Now login the user to get a session using the public client
        login_response = supabase.auth.sign_in_with_password({
            "email": user_in.email,
            "password": user_in.password,
        })
        
        if hasattr(login_response, 'session') and login_response.session:
            return {
                "access_token": login_response.session.access_token,
                "token_type": "bearer",
                "message": "User registered successfully"
            }
        else:
            return {
                "access_token": "",
                "token_type": "bearer",
                "message": "User registered successfully. Please login."
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during registration: {str(e)}")
        
        # Check for specific error message patterns
        error_message = str(e).lower()
        
        # Check for duplicate user/email errors
        if "already been registered" in error_message or "already exists" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with this email address already exists. Please login or use a different email."
            )
        # Handle password strength errors
        elif "password" in error_message and ("weak" in error_message or "requirements" in error_message):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password does not meet requirements: {str(e)}"
            )
        # Handle email validation errors
        elif "email" in error_message and "valid" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email address: {str(e)}"
            )
        # For all other errors, return a generic message
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed due to an unexpected error. Please try again later."
            ) 