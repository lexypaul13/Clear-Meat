"""Supabase client configuration for the MeatWise application."""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import lru_cache

# Load environment variables
load_dotenv()

# Get Supabase configuration from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@lru_cache()
def get_supabase() -> Client:
    """
    Get a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance
        
    Raises:
        ValueError: If required environment variables are not set
        
    Note:
        This function is cached to reuse the same client instance
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
        )
    
    return create_client(SUPABASE_URL, SUPABASE_KEY) 