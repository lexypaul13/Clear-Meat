"""Supabase client configuration and connection management for the MeatWise application.

This module provides centralized access to Supabase clients with proper caching,
error handling, and logging. It supports both anonymous and admin access.
"""

import logging
import os
import json
import httpx
from functools import lru_cache
from typing import Optional, Tuple, Dict, Any, List

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Remove the dotenv load and hardcoded defaults
# We'll use the settings module exclusively for configuration

# Get Supabase configuration directly from settings
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY

# Global client instances
_public_client: Optional[Client] = None
_admin_client: Optional[Client] = None


def get_supabase() -> Client:
    """
    Get a cached Supabase client instance with anonymous/public access.
    
    Returns:
        Client: A Supabase client instance
        
    Note:
        This function is cached to reuse the same client instance for better performance
    """
    global _public_client
    
    if _public_client is not None:
        return _public_client
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        error_msg = "Supabase configuration missing - URL and Key must be provided via environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Log connection attempt with more detailed info
        logger.info(f"Initializing Supabase public client with URL: {SUPABASE_URL}")
        logger.debug(f"Settings object contains SUPABASE_URL: {bool(settings.SUPABASE_URL)}")
        logger.debug(f"Environment contains SUPABASE_URL: {bool(os.environ.get('SUPABASE_URL'))}")
        
        # Test the network connection to the Supabase URL first
        try:
            # Test the connection to the Supabase host first
            parsed_url = httpx.URL(SUPABASE_URL)
            host = str(parsed_url.host)
            test_url = f"https://{host}/rest/v1/"
            
            logger.debug(f"Testing connection to Supabase host: {test_url}")
            
            # Increase timeout for the connection test
            with httpx.Client(timeout=30.0) as client:
                response = client.get(test_url, headers={"apikey": SUPABASE_KEY})
                logger.debug(f"Connection test response status: {response.status_code}")
                # Note: Not logging response headers as they may contain sensitive info
        except Exception as e:
            logger.error(f"Failed to connect to Supabase host: {str(e)}")
            # Continue with client creation despite connection test failure
        
        # Create client options with increased timeouts
        client_options = ClientOptions(
            postgrest_client_timeout=60,  # Increase from default 4s to 60s
            storage_client_timeout=30     # Increase storage timeout as well
        )
        
        # Create and cache the client
        logger.debug("Creating Supabase client instance with extended timeout")
        _public_client = create_client(SUPABASE_URL, SUPABASE_KEY, options=client_options)
        
        # Test the client with a lightweight query instead of counting all products
        logger.debug("Testing Supabase client with a lightweight query")
        try:
            # Use a faster query - limit to 1 record instead of counting all
            test_response = _public_client.table("products").select("code").limit(1).execute()
            logger.debug(f"Test query response: {json.dumps(test_response.dict())}")
            logger.info("Supabase public client initialized successfully")
        except Exception as e:
            logger.warning(f"Test query failed, but client initialization will continue: {str(e)}")
        
        return _public_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase public client: {str(e)}")
        # Return None or raise exception based on your error handling preference
        raise


@lru_cache()
def get_admin_supabase() -> Optional[Client]:
    """
    Get a cached Supabase client instance with admin/service-role access.
    
    Returns:
        Client: A Supabase client instance with admin privileges
        None: If service role key is not configured
        
    Note:
        This function is cached to reuse the same client instance for better performance
    """
    global _admin_client
    
    if _admin_client is not None:
        return _admin_client
    
    if not SUPABASE_URL:
        logger.error("Supabase URL is required for admin client")
        return None
    
    if not SUPABASE_SERVICE_KEY:
        logger.warning("No Supabase service role key configured, admin client not available")
        return None
    
    try:
        logger.info("Initializing Supabase admin client with service role key")
        
        # Create and cache the admin client
        _admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        
        # Test connection
        if _admin_client and hasattr(_admin_client, 'auth'):
            logger.info("Supabase admin client initialized successfully")
        else:
            logger.error("Supabase admin client initialized but auth attribute is missing")
            
        return _admin_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase admin client: {str(e)}")
        return None


def reset_clients() -> None:
    """
    Reset both public and admin Supabase clients.
    Useful for testing or when credentials change.
    """
    global _public_client, _admin_client
    _public_client = None
    _admin_client = None
    
    # Clear the cache
    get_supabase.cache_clear()
    get_admin_supabase.cache_clear()
    
    logger.info("Supabase clients reset")


def get_supabase_with_options(
    url: Optional[str] = None, 
    key: Optional[str] = None,
    admin: bool = False
) -> Client:
    """
    Get a Supabase client with custom URL and key options.
    Useful for scripts or when you need a fresh client with different credentials.
    
    Args:
        url: Optional Supabase URL override
        key: Optional Supabase key override
        admin: Whether to use admin credentials (if available)
        
    Returns:
        Client: A new Supabase client instance with the specified options
    """
    # Determine which credentials to use
    if admin and not key:
        key = SUPABASE_SERVICE_KEY
        if not key:
            logger.warning("Admin client requested but no service role key available")
            # Fall back to public key
            key = SUPABASE_KEY
    
    # Use provided values or fall back to defaults
    final_url = url or SUPABASE_URL
    final_key = key or SUPABASE_KEY
    
    if not final_url or not final_key:
        error_msg = "Supabase URL and key are required"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.debug(f"Creating custom Supabase client for URL: {final_url}")
        return create_client(final_url, final_key)
    except Exception as e:
        logger.error(f"Failed to create custom Supabase client: {str(e)}")
        raise 


class SupabaseService:
    """Centralized Supabase client service."""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Supabase client."""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
            
            self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            # Test connection
            response = self.client.table('products').select('code').limit(1).execute()
            logger.debug(f"Test query response: {response}")
            logger.info("Supabase public client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def get_client(self) -> Client:
        """Get the Supabase client."""
        if not self.client:
            self._initialize_client()
        return self.client
    
    # Product operations
    def get_product_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get a product by its code."""
        try:
            response = self.client.table('products').select('*').eq('code', code).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching product {code}: {e}")
            return None
    
    def get_products(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get products with pagination - excludes image_data to prevent massive response sizes."""
        try:
            # Exclude image_data to eliminate 50KB+ base64 data per product
            response = (self.client.table('products')
                       .select('code, name, brand, description, ingredients_text, calories, protein, fat, '
                              'carbohydrates, salt, meat_type, risk_rating, image_url, last_updated, created_at')
                       .range(offset, offset + limit - 1)
                       .execute())
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []
    
    def count_products(self) -> int:
        """Get total product count."""
        try:
            response = (self.client.table('products')
                       .select('code', count='exact')
                       .execute())
            return response.count or 0
        except Exception as e:
            logger.error(f"Error counting products: {e}")
            return 0
    
    # Old text search method removed - now using AI-powered NLP search service
    
    # User operations
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID."""
        try:
            response = self.client.table('profiles').select('*').eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def create_user_profile(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a user profile."""
        try:
            response = self.client.table('profiles').insert(user_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            return None
    
    def update_user_profile(self, user_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a user profile."""
        try:
            response = (self.client.table('profiles')
                       .update(user_data)
                       .eq('id', user_id)
                       .execute())
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating user profile {user_id}: {e}")
            return None

# Global instance
supabase_service = SupabaseService()

def get_supabase_service() -> SupabaseService:
    """Dependency to get Supabase service."""
    return supabase_service 