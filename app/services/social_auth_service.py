"""Social authentication service using Supabase's built-in OAuth providers."""

import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

from app.core.supabase import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported OAuth providers (using Supabase's built-in providers)
SUPPORTED_PROVIDERS = {
    "google": "google",
    "facebook": "facebook", 
    "apple": "apple",
    "twitter": "twitter"
}

class SocialAuthService:
    """Service for handling social authentication using Supabase's built-in OAuth."""
    
    @staticmethod
    def get_oauth_url(provider: str, redirect_url: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate OAuth URL using Supabase's built-in OAuth endpoints.
        
        Args:
            provider: OAuth provider name (google, facebook, apple, twitter)
            redirect_url: Optional redirect URL after authentication
            
        Returns:
            Tuple[str, str]: (auth_url, provider_name)
            
        Raises:
            ValueError: If provider is not supported
        """
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}. Supported: {list(SUPPORTED_PROVIDERS.keys())}")
        
        if not settings.SUPABASE_URL:
            raise Exception("Supabase URL not configured")
        
        try:
            # Use Supabase's built-in OAuth URL
            base_url = f"{settings.SUPABASE_URL}/auth/v1/authorize"
            
            # Build query parameters
            params = {
                "provider": SUPPORTED_PROVIDERS[provider]
            }
            
            if redirect_url:
                params["redirect_to"] = redirect_url
            
            # Generate the OAuth URL
            auth_url = f"{base_url}?{urlencode(params)}"
            
            logger.info(f"Generated Supabase OAuth URL for {provider}")
            return auth_url, provider
            
        except Exception as e:
            logger.error(f"Error generating OAuth URL for {provider}: {str(e)}")
            raise Exception(f"Failed to generate OAuth URL for {provider}: {str(e)}")
    
    @staticmethod
    def send_phone_otp(phone: str) -> Dict[str, Any]:
        """
        Send OTP to phone number using Supabase's built-in SMS auth.
        
        Args:
            phone: Phone number in international format (+1234567890)
            
        Returns:
            Dict[str, Any]: Response from Supabase
            
        Raises:
            Exception: If Supabase client is not available or SMS sending fails
        """
        if not supabase:
            raise Exception("Supabase client not available")
        
        try:
            # Send OTP via Supabase's built-in SMS auth
            response = supabase.auth.sign_in_with_otp({
                "phone": phone
            })
            
            logger.info(f"OTP sent to phone number: {phone[:3]}***{phone[-4:]}")
            return {
                "success": True,
                "message": "OTP sent successfully",
                "phone": phone
            }
            
        except Exception as e:
            logger.error(f"Error sending OTP to {phone}: {str(e)}")
            raise Exception(f"Failed to send OTP: {str(e)}")
    
    @staticmethod
    def verify_phone_otp(phone: str, token: str) -> Dict[str, Any]:
        """
        Verify OTP token using Supabase's built-in SMS auth.
        
        Args:
            phone: Phone number in international format
            token: OTP token received via SMS
            
        Returns:
            Dict[str, Any]: Authentication response with user data and access token
            
        Raises:
            Exception: If verification fails
        """
        if not supabase:
            raise Exception("Supabase client not available")
        
        try:
            # Verify OTP with Supabase's built-in auth
            response = supabase.auth.verify_otp({
                "phone": phone,
                "token": token,
                "type": "sms"
            })
            
            if not response.user or not response.session:
                raise Exception("Invalid OTP or verification failed")
            
            logger.info(f"Phone verification successful for: {phone[:3]}***{phone[-4:]}")
            
            return {
                "access_token": response.session.access_token,
                "token_type": "bearer",
                "user": {
                    "id": response.user.id,
                    "phone": response.user.phone,
                    "email": response.user.email,
                    "created_at": response.user.created_at
                }
            }
            
        except Exception as e:
            logger.error(f"Error verifying OTP for {phone}: {str(e)}")
            raise Exception(f"OTP verification failed: {str(e)}")
    
    @staticmethod
    def get_supported_providers() -> Dict[str, Dict[str, Any]]:
        """
        Get list of supported OAuth providers with their configurations.
        
        Returns:
            Dict[str, Dict[str, Any]]: Provider configurations
        """
        return {
            "google": {
                "name": "Google",
                "icon": "google",
                "color": "#4285f4",
                "enabled": True,
                "auth_url": f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=google"
            },
            "facebook": {
                "name": "Facebook", 
                "icon": "facebook",
                "color": "#1877f2",
                "enabled": True,
                "auth_url": f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=facebook"
            },
            "apple": {
                "name": "Apple",
                "icon": "apple", 
                "color": "#000000",
                "enabled": True,
                "auth_url": f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=apple"
            },
            "twitter": {
                "name": "Twitter/X",
                "icon": "twitter",
                "color": "#1da1f2",
                "enabled": True,
                "auth_url": f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=twitter"
            }
        } 