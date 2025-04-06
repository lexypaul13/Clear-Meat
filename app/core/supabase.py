"""Supabase client for the MeatWise API."""

import logging
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Supabase clients
supabase = None
admin_supabase = None

try:
    # Print debug information
    logger.info(f"Attempting to connect to Supabase with URL: {settings.SUPABASE_URL}")
    
    # Create client with anon key for token verification & user operations
    key_info = settings.SUPABASE_KEY[:4] if settings.SUPABASE_KEY else 'None'
    logger.info(f"Initializing public client with anon key (first 4 chars): {key_info}")
    
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    
    # Create admin client with service role key for privileged operations
    if hasattr(settings, 'SUPABASE_SERVICE_KEY') and settings.SUPABASE_SERVICE_KEY:
        logger.info("Initializing admin client with service role key")
        admin_supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    # Test connection with a simpler approach
    logger.info("Testing Supabase connection...")
    if supabase and hasattr(supabase, 'auth'):
        logger.info("Supabase client initialized successfully with auth attribute")
    else:
        logger.error("Supabase client initialized but auth attribute is missing!")
        
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    # Initialize as None to avoid errors when importing
    supabase = None
    admin_supabase = None 