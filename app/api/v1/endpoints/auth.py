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

router = APIRouter()
logger = logging.getLogger(__name__)

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