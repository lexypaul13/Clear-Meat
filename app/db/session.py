"""Database session management for the MeatWise application."""

import logging
import socket
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

# Create SQLAlchemy engine
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Enable connection health checks
        echo=True,  # Enable SQL query logging
        pool_size=5,  # Set a reasonable pool size
        max_overflow=10,  # Maximum number of connections to overflow
        pool_timeout=30  # Timeout for getting a connection from pool
    )
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