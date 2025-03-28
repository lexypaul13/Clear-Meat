"""Supabase client for the MeatWise API."""

import logging
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase = None

try:
    # Print debug information
    logger.info(f"Attempting to connect to Supabase with URL: {settings.SUPABASE_URL}")
    logger.info(f"Using API key (first 4 chars): {settings.SUPABASE_KEY[:4] if settings.SUPABASE_KEY else 'None'}")
    
    # Create the client
    supabase: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    
    # Test connection with a simpler approach
    logger.info("Testing Supabase connection...")
    if supabase and hasattr(supabase, 'auth'):
        logger.info("Supabase client initialized successfully with auth attribute")
    else:
        logger.error("Supabase client initialized but auth attribute is missing!")
        
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    # Initialize a None client to avoid errors when importing
    supabase = None 