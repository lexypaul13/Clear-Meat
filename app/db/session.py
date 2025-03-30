"""Database session management for the MeatWise application."""

import logging
import os
import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from app.core.config import settings

# Environment detection
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# Configure logging with a more structured approach for production
logger = logging.getLogger(__name__)
if IS_PRODUCTION:
    # More structured logging for production
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
else:
    # More verbose logging for development
    logging.basicConfig(level=logging.DEBUG)

# Log the database URL (with password masked)
db_url = settings.DATABASE_URL
if db_url:
    parsed_url = urlparse(db_url)
    masked_url = db_url.replace(parsed_url.password, "****") if parsed_url.password else db_url
    logger.debug(f"Connecting to database: {masked_url}")
    
    # Try to resolve the hostname
    try:
        hostname = parsed_url.hostname
        if hostname:
            logger.debug(f"Attempting to resolve hostname: {hostname}")
            ip_address = socket.gethostbyname(hostname)
            logger.debug(f"Resolved {hostname} to {ip_address}")
    except socket.gaierror as e:
        logger.error(f"Failed to resolve hostname {hostname}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while resolving hostname: {str(e)}")

# Adjust pool settings based on environment
if IS_PRODUCTION:
    # Production settings with larger pool
    pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "300"))
else:
    # Development settings
    pool_size = 5
    max_overflow = 10
    pool_timeout = 30
    pool_recycle = 900  # 15 minutes

# Create SQLAlchemy engine
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Enable connection health checks
        echo=not IS_PRODUCTION,  # Enable SQL query logging in development
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle  # Recycle connections after this many seconds
    )
    logger.info(f"Database engine created with pool_size={pool_size}, max_overflow={max_overflow}")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

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

# Graceful shutdown handling
def close_db_connections():
    """Close database connections on application shutdown."""
    logger.info("Closing database connections...")
    if hasattr(engine, 'dispose'):
        engine.dispose()
        logger.info("Database connections closed") 