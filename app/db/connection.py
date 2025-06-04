"""Database connection management for the MeatWise application.

This module provides functions for connecting to either a local PostgreSQL database
or a Supabase database based on the current environment.
"""

import logging
import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from contextlib import contextmanager
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
TESTING = os.getenv("TESTING", "false").lower() == "true"

# Get database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Default local database URL if none is provided
DEFAULT_LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:54322/postgres"

# Determine which database to use
def get_database_url() -> str:
    """
    Determine which database URL to use based on environment.
    
    Returns:
        str: The database URL to use
    """
    if TESTING:
        logger.info("Running in test mode, using in-memory SQLite database")
        return "sqlite:///:memory:"
    
    if ENVIRONMENT == "production":
        if not DATABASE_URL:
            logger.warning("No DATABASE_URL found for production environment, falling back to Supabase")
            # In production, we should have a proper DATABASE_URL, but we can fallback to Supabase
            # if needed (though this is not ideal)
            return DEFAULT_LOCAL_DB_URL
        return DATABASE_URL
    
    # Development environment
    if not DATABASE_URL:
        logger.info(f"No DATABASE_URL found for development, using default: {DEFAULT_LOCAL_DB_URL}")
        return DEFAULT_LOCAL_DB_URL
    
    logger.info(f"Using DATABASE_URL from environment: {DATABASE_URL[:20]}...")
    return DATABASE_URL

# Get the actual database URL to use
active_db_url = get_database_url()

# Create SQLAlchemy engine
try:
    # Convert postgres:// to postgresql:// if needed
    if active_db_url.startswith('postgres://'):
        active_db_url = active_db_url.replace('postgres://', 'postgresql://', 1)
        logger.debug("Converted postgres:// to postgresql:// in DATABASE_URL")

    # Log database connection (with password masked)
    parsed_url = urlparse(active_db_url)
    masked_url = active_db_url.replace(parsed_url.password, "****") if parsed_url.password else active_db_url
    logger.info(f"Using database connection: {masked_url}")
    logger.info(f"Environment: {ENVIRONMENT}, Testing mode: {TESTING}")

    # Create engine with appropriate settings based on database type
    if TESTING or active_db_url.startswith('sqlite'):
        # SQLite doesn't support the same connection pool parameters
        engine = create_engine(
            active_db_url,
            echo=False,
        )
    else:
        # PostgreSQL can use full connection pooling
        engine = create_engine(
            active_db_url,
            pool_pre_ping=True,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=900
        )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.critical(f"Failed to create database engine: {str(e)}")
    raise

# Create SQLAlchemy session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Get a database session.
    
    Yields:
        Session: A SQLAlchemy session
        
    Note:
        This function is used as a dependency in FastAPI endpoints
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """
    Get a database session with context manager.
    
    Yields:
        Session: A SQLAlchemy session
        
    Example:
        with get_db_context() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Supabase client for when we need to use Supabase directly
@contextmanager
def get_supabase_client() -> Client:
    """
    Get a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance
        
    Note:
        This function is cached to reuse the same client instance
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        error_msg = "Supabase configuration missing - URL and Key must be provided via environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Log connection attempt
        logger.info(f"Initializing Supabase client with URL: {SUPABASE_URL}")
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        yield client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {str(e)}")
        raise

def close_db_connections():
    """Close database connections on application shutdown."""
    logger.info("Closing database connections...")
    if hasattr(engine, 'dispose'):
        engine.dispose()
        logger.info("Database connections closed")

def is_using_local_db() -> bool:
    """
    Check if the application is using a local database.
    
    Returns:
        bool: True if using local database, False if using Supabase
    """
    return "localhost" in active_db_url or "127.0.0.1" in active_db_url 