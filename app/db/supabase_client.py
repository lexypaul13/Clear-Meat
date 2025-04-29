"""Supabase client configuration and connection management for the MeatWise application.

This module provides centralized access to Supabase clients with proper caching,
error handling, and logging. It supports both anonymous and admin access.
"""

import logging
import os
from functools import lru_cache
from typing import Optional, Tuple, Dict, Any

from supabase import create_client, Client
from dotenv import load_dotenv

from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Hardcoded Supabase configuration fallbacks - Use these values when env variables aren't set
DEFAULT_SUPABASE_URL = "https://szswmlkhirkmozwvhpnc.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6c3dtbGtoaXJrbW96d3ZocG5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNjY5NTIsImV4cCI6MjA1Nzg0Mjk1Mn0.yc4eC9f7IAjdNlav0GfxfkaeJAKZp-w1hPGHB0lMqPs"

# Get Supabase configuration from settings or use defaults
SUPABASE_URL = settings.SUPABASE_URL or os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = settings.SUPABASE_KEY or os.getenv("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)
SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY or os.getenv("SUPABASE_SERVICE_KEY")

# Global client instances
_public_client: Optional[Client] = None
_admin_client: Optional[Client] = None


@lru_cache()
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
    
    try:
        # Log connection attempt
        key_info = SUPABASE_KEY[:4] if SUPABASE_KEY else 'None'
        logger.info(f"Initializing Supabase public client with URL: {SUPABASE_URL}")
        logger.debug(f"Using anon key (first 4 chars): {key_info}")
        
        # Create and cache the client
        _public_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test connection
        if _public_client and hasattr(_public_client, 'auth'):
            logger.info("Supabase public client initialized successfully")
        else:
            logger.error("Supabase public client initialized but auth attribute is missing")
            
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
    
    try:
        logger.debug(f"Creating custom Supabase client for URL: {final_url}")
        return create_client(final_url, final_key)
    except Exception as e:
        logger.error(f"Failed to create custom Supabase client: {str(e)}")
        raise 