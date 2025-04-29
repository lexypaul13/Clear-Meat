"""Supabase client configuration for the MeatWise application."""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from functools import lru_cache

# Load environment variables
load_dotenv()

# Hardcoded Supabase configuration - Use these values when env variables aren't set
DEFAULT_SUPABASE_URL = "https://szswmlkhirkmozwvhpnc.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN6c3dtbGtoaXJrbW96d3ZocG5jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNjY5NTIsImV4cCI6MjA1Nzg0Mjk1Mn0.yc4eC9f7IAjdNlav0GfxfkaeJAKZp-w1hPGHB0lMqPs"

# Get Supabase configuration from env or use defaults
SUPABASE_URL = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = os.getenv("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)

@lru_cache()
def get_supabase() -> Client:
    """
    Get a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance
        
    Note:
        This function is cached to reuse the same client instance
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY) 