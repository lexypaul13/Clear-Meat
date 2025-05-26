"""Authentication endpoints for the MeatWise API."""

from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.v1 import models
from app.core import security
from app.core.config import settings
from app.core.supabase import supabase, admin_supabase
from app.db import models as db_models
from app.db.session import get_db
from app.services.social_auth_service import SocialAuthService

router = APIRouter()
logger = logging.getLogger(__name__)

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