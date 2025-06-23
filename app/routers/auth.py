"""Authentication router for the MeatWise API."""

from datetime import timedelta
from typing import Any, Dict, Optional
import os
import re

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models import Token, UserCreate
from app.api.v1 import models
from app.core import security
from app.core.config import settings
from app.core.supabase import supabase, admin_supabase
from app.db import models as db_models
from app.db.supabase_client import get_supabase_service
from app.services.social_auth_service import SocialAuthService
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
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    try:
        # Check if Supabase client is initialized
        if not supabase or not hasattr(supabase, 'auth'):
            # In testing mode, return 503 immediately instead of trying other methods
            if is_testing:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable. Please try again later.",
                )
                
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


def validate_password_strength(password: str) -> None:
    """Validate password strength and raise HTTPException if weak"""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too long (maximum 128 characters)"
        )
    
    # Check for basic complexity requirements
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    requirements_met = sum([has_upper, has_lower, has_digit, has_special])
    
    if requirements_met < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 3 of: uppercase letter, lowercase letter, number, special character"
        )
    
    # Check for common weak passwords
    weak_passwords = {
        "123456789", "password", "admin", "test", "guest", "user", 
        "qwerty", "letmein", "welcome", "monkey", "dragon"
    }
    
    if password.lower() in weak_passwords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common. Please choose a more secure password"
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
    # Log registration attempt
    logger.info(f"Registration attempt for email: {user_in.email}")
    
    # Validate password strength before proceeding
    validate_password_strength(user_in.password)
    logger.debug("Password validation passed")
    
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    logger.debug(f"Testing mode: {is_testing}")
            
    try:
        # Use the admin API to create a user directly
        if not admin_supabase:
            logger.error("Admin Supabase client not available for user creation")
            logger.debug(f"admin_supabase object: {type(admin_supabase)}")
            logger.debug(f"SUPABASE_SERVICE_KEY set: {'Yes' if settings.SUPABASE_SERVICE_KEY else 'No'}")
            
            # In testing mode, return error immediately instead of trying alternatives
            if is_testing:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="User registration service unavailable in test mode."
                )
                
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create user. Server configuration error."
            )
            
        logger.info("Using admin API to create user")
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
        
        logger.info("User created successfully, attempting login")
        # Now login the user to get a session using the public client
        login_response = supabase.auth.sign_in_with_password({
            "email": user_in.email,
            "password": user_in.password,
        })
        
        if hasattr(login_response, 'session') and login_response.session:
            logger.info("Login successful, returning token")
            return {
                "access_token": login_response.session.access_token,
                "token_type": "bearer",
                "message": "User registered successfully"
            }
        else:
            logger.warning("Login after registration failed, user should login manually")
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


@router.get("/providers", response_model=Dict[str, Any])
def get_auth_providers() -> Any:
    """
    Get list of supported authentication providers.
    
    Returns:
        Dict[str, Any]: Available authentication providers with their configurations
    """
    return {
        "providers": SocialAuthService.get_supported_providers(),
        "phone_auth_enabled": True,
        "email_auth_enabled": True
    }


@router.get("/oauth/{provider}")
async def initiate_oauth(
    provider: str,
    redirect_url: Optional[str] = Query(None, description="URL to redirect to after authentication")
):
    """
    Initiate OAuth authentication with the specified provider.
    
    This endpoint returns the OAuth URL that the frontend should redirect to.
    Supabase handles the OAuth flow and redirects back to your application.
    """
    try:
        auth_url, provider_name = SocialAuthService.get_oauth_url(provider, redirect_url)
        
        return {
            "auth_url": auth_url,
            "provider": provider_name,
            "message": f"Redirect to this URL to authenticate with {provider_name}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"OAuth initiation failed for {provider}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth authentication")


@router.post("/phone/send-otp")
def send_phone_otp(
    phone_request: models.PhoneAuthRequest
) -> Any:
    """
    Send OTP to phone number for authentication.
    
    Args:
        phone_request: Phone number in international format
        
    Returns:
        Dict[str, Any]: Success message
        
    Raises:
        HTTPException: If OTP sending fails
    """
    try:
        response = SocialAuthService.send_phone_otp(phone_request.phone)
        return response
        
    except Exception as e:
        logger.error(f"Phone OTP sending failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please check your phone number and try again."
        )


@router.post("/phone/verify", response_model=models.Token)
def verify_phone_otp(
    verify_request: models.PhoneVerifyRequest
) -> Any:
    """
    Verify OTP token for phone authentication.
    
    Args:
        verify_request: Phone number and OTP token
        
    Returns:
        models.Token: Access token and user information
        
    Raises:
        HTTPException: If OTP verification fails
    """
    try:
        auth_response = SocialAuthService.verify_phone_otp(
            phone=verify_request.phone,
            token=verify_request.token
        )
        
        return models.Token(
            access_token=auth_response["access_token"],
            token_type=auth_response["token_type"]
        )
        
    except Exception as e:
        logger.error(f"Phone OTP verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP or verification failed. Please try again."
        ) 