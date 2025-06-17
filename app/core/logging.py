"""Centralized logging configuration."""
import logging
import logging.config
import os
from typing import Dict, Any


def setup_logging() -> None:
    """Configure logging for the application."""
    
    # Get log level from environment
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    # Get environment
    environment = os.environ.get("ENVIRONMENT", "development")
    
    # In production, set stricter logging
    if environment == "production":
        log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "formatter": "standard" if environment == "production" else "detailed",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING" if environment == "production" else "INFO",
                "propagate": False,
            },
        },
    }
    
    logging.config.dictConfig(logging_config)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {environment} environment with level {log_level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)