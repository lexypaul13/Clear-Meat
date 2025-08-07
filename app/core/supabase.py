"""Supabase client for the MeatWise API."""

import logging
from supabase import create_client, Client
from typing import Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

def init_supabase_client(url: str, key: str, is_admin: bool = False) -> Tuple[Optional[Client], str]:
    """Initialize a Supabase client with proper error handling."""
    try:
        client: Client = create_client(url, key)
        
        # Test the connection - skip for admin client as it might not have table access
        if is_admin:
            # For admin client, just verify auth.admin exists
            if hasattr(client, 'auth') and hasattr(client.auth, 'admin'):
                return client, ""
            else:
                return None, "Admin auth module not available"
        else:
            # For regular client, test with a simple query
            try:
                client.table('products').select('*').limit(1).execute()
                return client, ""
            except Exception as test_e:
                error_msg = str(test_e)
                if "Invalid API key" in error_msg:
                    return None, f"Invalid anon API key"
                elif "does not exist" in error_msg:
                    # If table doesn't exist, that's okay - just check auth
                    if hasattr(client, 'auth'):
                        return client, ""
                return None, f"Connection test failed: {error_msg}"
            
    except Exception as e:
        return None, f"Failed to initialize client: {str(e)}"

# Initialize Supabase clients
supabase = None
admin_supabase = None

try:
    # Print debug information
    logger.info(f"Attempting to connect to Supabase with URL: {settings.SUPABASE_URL}")
    # Configuration validation removed for security
    
    # Initialize public client
    # Initializing public client
    supabase, error = init_supabase_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    if error:
        logger.error(f"Public client initialization failed: {error}")
    else:
        logger.info("Public client initialized successfully")
    
    # Initialize admin client if service role key is available
    if hasattr(settings, 'SUPABASE_SERVICE_KEY') and settings.SUPABASE_SERVICE_KEY:
        # Initializing admin client
        admin_supabase, error = init_supabase_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
            is_admin=True
        )
        if error:
            logger.error(f"Admin client initialization failed: {error}")
        else:
            logger.info("Admin client initialized successfully")
    else:
        logger.warning("SUPABASE_SERVICE_KEY not set - admin operations will not be available")
    
    # Final validation
    if not supabase and not admin_supabase:
        logger.error("Both public and admin clients failed to initialize!")
    elif not supabase:
        logger.error("Public client failed to initialize but admin client is available")
    elif not admin_supabase:
        logger.warning("Admin client not available but public client is working")
    else:
        logger.info("Both public and admin clients initialized successfully")
        
except Exception as e:
    logger.error(f"Unexpected error during Supabase initialization: {str(e)}")
    # Initialize as None to avoid errors when importing
    supabase = None
    admin_supabase = None 