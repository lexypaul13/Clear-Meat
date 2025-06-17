"""Database session management for the MeatWise application."""

import logging
import os
import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Configure logging with a more structured approach
logger = logging.getLogger(__name__)
# Don't set logging level here - let it be configured centrally

# Use environment variable or default to postgres database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is required")

# Log the database URL (with password masked)
if database_url:
    parsed_url = urlparse(database_url)
    masked_url = database_url.replace(parsed_url.password, "****") if parsed_url.password else database_url
    logger.info(f"Using database connection: {masked_url}")
    
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
else:
    logger.critical("No DATABASE_URL found and no default could be set")
    raise ValueError("DATABASE_URL must be set")

# Create SQLAlchemy engine
try:
    # Convert postgres:// to postgresql:// if needed
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        logger.debug("Converted postgres:// to postgresql:// in DATABASE_URL")

    engine = create_engine(
        database_url,
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