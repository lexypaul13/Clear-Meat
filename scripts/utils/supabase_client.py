"""Utility module for accessing the Supabase client in scripts."""

import os
from dotenv import load_dotenv
from app.db.supabase import get_supabase

# Load environment variables
load_dotenv()

def get_script_supabase(url: str = None, key: str = None):
    """
    Get a Supabase client instance for scripts.
    
    Args:
        url: Optional Supabase URL override
        key: Optional Supabase key override
        
    Returns:
        Client: A Supabase client instance
    """
    if url:
        os.environ["SUPABASE_URL"] = url
    if key:
        os.environ["SUPABASE_KEY"] = key
        
    return get_supabase() 