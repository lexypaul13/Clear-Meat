"""Authentication endpoints for the MeatWise API."""

from typing import Any, Dict, Optional
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.v1 import models
from app.core import security
from app.core.config import settings
from app.core.supabase import supabase, admin_supabase
from app.db import models as db_models
from app.db.supabase_client import get_supabase_service
from app.services.social_auth_service import SocialAuthService
from app.models import Token, UserCreate
import re
import os
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_password_strength(password: str) -> None:
    """
    Validate password strength according to security requirements.
    
    Args:
        password: The password to validate
        
    Raises:
        HTTPException: If password doesn't meet requirements
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if len(password) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be no more than 128 characters long"
        )
    
    # Check for character variety (at least 3 of 4 types)
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password))
    
    variety_count = sum([has_upper, has_lower, has_digit, has_special])
    
    if variety_count < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 3 of the following: uppercase letters, lowercase letters, numbers, special characters"
        )
    
    # Check for common passwords (basic check)
    common_passwords = {
        'password', '12345678', 'qwerty123', 'abc123456', 'password123',
        '123456789', 'welcome123', 'admin123', 'user123', 'test123'
    }
    
    if password.lower() in common_passwords:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common. Please choose a more secure password."
        )

@router.get("/providers", 
    response_model=Dict[str, Any],
    summary="Get Authentication Providers",
    description="Returns a list of all supported authentication methods including social providers, email, and phone",
    responses={
        200: {
            "description": "List of available authentication providers",
            "content": {
                "application/json": {
                    "example": {
                        "providers": ["google", "apple", "facebook"],
                        "phone_auth_enabled": True,
                        "email_auth_enabled": True
                    }
                }
            }
        }
    },
    tags=["Authentication"]
)
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


@router.get("/oauth/{provider}",
    response_model=Dict[str, Any],
    summary="Initiate OAuth Login",
    description="Start OAuth authentication flow with the specified provider (Google, Apple, Facebook)",
    responses={
        200: {
            "description": "OAuth URL generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
                        "provider": "google",
                        "message": "Redirect to this URL to authenticate with Google"
                    }
                }
            }
        },
        400: {"description": "Invalid provider specified"},
        500: {"description": "Failed to initiate OAuth authentication"}
    },
    tags=["Authentication", "OAuth"]
)
async def initiate_oauth(
    provider: str = Path(..., description="OAuth provider name", enum=["google", "apple", "facebook"]),
    redirect_url: Optional[str] = Query(None, description="URL to redirect to after authentication", example="myapp://auth/callback")
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


@router.post("/login", 
    response_model=Token,
    summary="User Login",
    description="Login with email and password to receive an access token",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        401: {"description": "Invalid credentials"},
        503: {"description": "Authentication service unavailable"}
    },
    tags=["Authentication"]
)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    **Request body (x-www-form-urlencoded):**
    - username: User's email address
    - password: User's password
    
    Args:
        form_data: OAuth2 password request form
        
    Returns:
        Token: Access token for authenticated requests
        
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
        # Map network/DNS issues to service unavailable
        message = str(e)
        if isinstance(e, httpx.HTTPError) or "nodename nor servname" in message or "Name or service not known" in message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable. Please try again later.",
            )
        # Default to invalid credentials for other errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", 
    response_model=Token,
    summary="Register New User",
    description="Create a new user account with email and password",
    responses={
        200: {
            "description": "Registration successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer"
                    }
                }
            }
        },
        400: {"description": "Invalid user data or weak password"},
        409: {"description": "Email already registered"},
        503: {"description": "Registration service unavailable"}
    },
    tags=["Authentication"]
)
def register_user(
    user_in: UserCreate,
) -> Any:
    """
    Register a new user.
    
    **Password Requirements:**
    - At least 8 characters long
    - Maximum 128 characters
    - Must contain at least 3 of: uppercase, lowercase, number, special character
    - Cannot be a common password
    
    Args:
        user_in: User registration data (email, password, full_name)
        
    Returns:
        Token: Access token for immediate login
        
    Raises:
        HTTPException: If registration fails
    """
    # Log registration attempt
    logger.info(f"Registration attempt for email: {user_in.email}")
    
    # Validate password strength before proceeding
    validate_password_strength(user_in.password)
    # Password validation passed
    
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    logger.debug(f"Testing mode: {is_testing}")
            
    try:
        # Use the admin API to create a user directly
        if not admin_supabase:
            logger.error("Admin Supabase client not available for user creation")
            # Admin client configuration issue
            
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
            return {
                "access_token": login_response.session.access_token,
                "token_type": "bearer",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but login failed. Please try logging in manually."
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        message = str(e)
        # Return 503 when admin/public auth calls fail due to network/DNS
        if isinstance(e, httpx.HTTPError) or "nodename nor servname" in message or "Name or service not known" in message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Registration service unavailable. Please try again later.",
            )
        # Otherwise treat as bad input
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your information and try again."
        )


@router.post("/phone/send-otp",
    response_model=Dict[str, Any],
    summary="Send Phone OTP",
    description="Send a one-time password (OTP) to the specified phone number for authentication",
    responses={
        200: {
            "description": "OTP sent successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "OTP sent successfully",
                        "phone": "+1234567890"
                    }
                }
            }
        },
        400: {"description": "Invalid phone number format"},
        500: {"description": "Failed to send OTP"}
    },
    tags=["Authentication", "Phone Auth"]
)
def send_phone_otp(
    phone_request: models.PhoneAuthRequest
) -> Any:
    """
    Send OTP to phone number for authentication.
    
    Args:
        phone_request: Phone number in international format (+1234567890)
        
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


@router.post("/logout",
    response_model=Dict[str, Any],
    summary="Logout Current User",
    description="Logout the current authenticated user by invalidating their session",
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Logout successful",
                        "logged_out_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        401: {"description": "Not authenticated"}
    },
    tags=["Authentication"]
)
async def logout_user(
    supabase_service = Depends(get_supabase_service)
) -> Any:
    """
    Logout current user by invalidating their session.
    
    This endpoint signs out the user from Supabase and invalidates their session.
    The client should also clear any stored tokens.
    
    Returns:
        Dict[str, Any]: Logout confirmation message
    """
    try:
        # Sign out from Supabase (invalidates the session server-side)
        auth_response = supabase_service.client.auth.sign_out()
        
        return {
            "message": "Logout successful",
            "logged_out_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        return {
            "message": "Logout completed (client should clear tokens)",
            "logged_out_at": datetime.now().isoformat()
        }


@router.delete("/account",
    response_model=Dict[str, Any], 
    summary="Delete User Account",
    description="Permanently delete the current user's account and all associated data",
    responses={
        200: {
            "description": "Account deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Account deleted successfully",
                        "deleted_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        401: {"description": "Not authenticated"},
        500: {"description": "Failed to delete account"}
    },
    tags=["Authentication", "Account Management"]
)
async def delete_account(
    supabase_service = Depends(get_supabase_service)
) -> Any:
    """
    Permanently delete the current user's account and all associated data.
    
    This action is irreversible and will:
    - Delete the user's account from Supabase Auth
    - Remove all user-generated data (scan history, preferences, etc.)
    - Sign out the user immediately
    
    Returns:
        Dict[str, Any]: Account deletion confirmation
        
    Raises:
        HTTPException: If account deletion fails
    """
    try:
        # Get current user to ensure they're authenticated
        user_response = supabase_service.client.auth.get_user()
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        user_id = user_response.user.id
        
        # Delete user's data from database tables (cascade should handle this)
        # Note: Supabase RLS policies should prevent unauthorized access
        
        # Delete the user account from Supabase Auth
        # This will automatically sign them out
        admin_response = admin_supabase.auth.admin.delete_user(user_id)
        
        logger.info(f"Successfully deleted user account: {user_id}")
        
        return {
            "message": "Account deleted successfully",
            "deleted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please contact support."
        )
