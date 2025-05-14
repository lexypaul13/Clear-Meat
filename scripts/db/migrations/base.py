#!/usr/bin/env python
"""
Base migration utility for the MeatWise application.
Provides common functionality used by all migration scripts.
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("migrations")

# Load environment variables
load_dotenv()

def get_supabase_credentials() -> Dict[str, str]:
    """Get Supabase credentials from environment variables."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials in .env file")
    
    return {
        "url": supabase_url,
        "key": supabase_key
    }

def log_migration_start(migration_name: str) -> None:
    """Log the start of a migration."""
    logger.info(f"Starting migration: {migration_name}")

def log_migration_end(migration_name: str, success: bool, details: Any = None) -> None:
    """Log the end of a migration."""
    if success:
        logger.info(f"Successfully completed migration: {migration_name}")
        if details:
            logger.info(f"Migration details: {details}")
    else:
        logger.error(f"Failed to complete migration: {migration_name}")
        if details:
            logger.error(f"Failure details: {details}")

def validate_migration_prerequisites(prerequisites: Dict[str, Any]) -> bool:
    """
    Validate that all prerequisites for a migration are met.
    
    Args:
        prerequisites: Dictionary of prerequisite checks and their results
        
    Returns:
        bool: True if all prerequisites are met, False otherwise
    """
    all_met = True
    for check, result in prerequisites.items():
        if not result:
            logger.error(f"Prerequisite check failed: {check}")
            all_met = False
    
    return all_met 