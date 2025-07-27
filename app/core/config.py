"""Settings module for the MeatWise API."""

import logging
import os
import secrets
import sys
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

# Update the imports for pydantic v2
from pydantic import AnyHttpUrl, field_validator, model_validator, FieldValidationInfo, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class for the MeatWise API."""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MeatWise API"
    PROJECT_VERSION: str = "0.1.0"
    
    # Debug mode - default to False for production safety
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours (reduced from 7 days)
    ALGORITHM: str = "HS256"  # Algorithm for JWT encoding
    
    # Auth bypass - MUST be False in production
    ENABLE_AUTH_BYPASS: bool = os.getenv("ENABLE_AUTH_BYPASS", "false").lower() == "true"
    
    @field_validator("ENABLE_AUTH_BYPASS", mode="before")
    def validate_auth_bypass(cls, v: bool, info: FieldValidationInfo) -> bool:
        """Ensure auth bypass is not enabled in production."""
        is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
        if v and is_production:
            logging.error("ENABLE_AUTH_BYPASS cannot be true in production!")
            print("ERROR: ENABLE_AUTH_BYPASS cannot be true in production!", file=sys.stderr)
            raise ValueError("Auth bypass is not allowed in production")
        return v
    
    @field_validator("SECRET_KEY", mode="before")
    def validate_secret_key(cls, v: Optional[str]) -> str:
        """Validate the secret key."""
        if not v or len(v) < 32:
            if os.environ.get("ENVIRONMENT", "").lower() == "production":
                logging.error("SECRET_KEY must be set in production with at least 32 characters!")
                print("ERROR: SECRET_KEY must be set in production with at least 32 characters!", file=sys.stderr)
                raise ValueError("SECRET_KEY is required in production")
            else:
                # Warn that we're using a generated key
                logging.warning("No SECRET_KEY environment variable set! Using a randomly generated key.")
                logging.warning("This is insecure for production environments - set a SECRET_KEY environment variable.")
                print("WARNING: No SECRET_KEY environment variable set! Using a randomly generated key.", file=sys.stderr)
                print("This is insecure for production environments - set a SECRET_KEY environment variable.", file=sys.stderr)
            return secrets.token_urlsafe(32)
        return v
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_BY_IP: bool = os.getenv("RATE_LIMIT_BY_IP", "true").lower() == "true"
    
    # Redis Configuration
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    REDIS_TTL: int = int(os.getenv("REDIS_TTL", "3600"))  # Default TTL for cached items
    
    # CORS
    # Read CORS origins as a raw string first to avoid auto JSON parsing from environment
    BACKEND_CORS_ORIGINS_STR: Optional[str] = os.getenv("BACKEND_CORS_ORIGINS")

    @computed_field
    @property
    def parsed_cors_origins(self) -> List[AnyHttpUrl]:
        """Validate CORS origins."""
        origins: List[AnyHttpUrl] = []
        raw_value = self.BACKEND_CORS_ORIGINS_STR

        if not raw_value:
            # If neither env var nor .env setting exists, return empty list
            return []

        try:
            # Try parsing as comma-separated string first (common case)
            if isinstance(raw_value, str) and not raw_value.startswith('['):
                potential_origins = [item.strip() for item in raw_value.split(',')]
                # Validate each potential origin
                for origin_str in potential_origins:
                    if origin_str:
                        origins.append(AnyHttpUrl(origin_str))
            # Else try parsing as JSON list string (less common but supported)
            elif isinstance(raw_value, str) and raw_value.startswith('['):
                import json
                potential_origins = json.loads(raw_value)
                if isinstance(potential_origins, list):
                    for origin_str in potential_origins:
                        if origin_str:
                            origins.append(AnyHttpUrl(str(origin_str)))
                else:
                    raise ValueError("Parsed JSON for CORS origins is not a list")
            else:
                 # Should not happen if read from env/dotenv, but handle just in case
                raise ValueError(f"Invalid format for BACKEND_CORS_ORIGINS: {raw_value}")

        except (ValueError, TypeError, json.JSONDecodeError) as e:
            logging.warning(f"Failed to parse BACKEND_CORS_ORIGINS ('{raw_value}'). Error: {e}. Using empty list.")
            print(f"WARNING: Failed to parse BACKEND_CORS_ORIGINS ('{raw_value}'). Error: {e}. Using empty list.", file=sys.stderr)
            return [] # Return empty list on parsing failure

        return origins

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "")
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    
    # Get DATABASE_URL from env - use the one from .env file
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DATABASE_SSL_MODE: str = os.getenv("DATABASE_SSL_MODE", "prefer")  # disable, allow, prefer, require, verify-ca, verify-full

    @field_validator("DATABASE_URL", mode="before")
    def validate_database_url(cls, v: Optional[str]) -> Optional[str]:
        """Ensure database URL uses postgresql:// instead of postgres://."""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @model_validator(mode='after')
    def set_sqlalchemy_uri(self) -> 'Settings':
        """Set the database URI based on the database configuration."""
        if not self.SQLALCHEMY_DATABASE_URI:
            if self.DATABASE_URL:
                # Ensure we're using postgresql:// instead of postgres://
                db_url = self.DATABASE_URL
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                # Add SSL mode for production databases
                if self.DATABASE_SSL_MODE != "disable" and "localhost" not in db_url and "127.0.0.1" not in db_url:
                    # Add SSL mode parameter if not already present
                    if "sslmode=" not in db_url:
                        separator = "&" if "?" in db_url else "?"
                        db_url = f"{db_url}{separator}sslmode={self.DATABASE_SSL_MODE}"
                
                self.SQLALCHEMY_DATABASE_URI = db_url
            else:
                self.SQLALCHEMY_DATABASE_URI = (
                    f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                    f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB or ''}"
                )
        return self

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    @field_validator("SUPABASE_URL", "SUPABASE_KEY", mode="before")
    def warn_if_supabase_missing(cls, v: str, info: FieldValidationInfo) -> str:
        """Warn if Supabase URL or Key is not set."""
        env_var_name = info.field_name
        # Check if the value is missing (either None or empty string from os.getenv default)
        if not v:
            logging.warning(f"Environment variable '{env_var_name}' is not set. Supabase features may not work.")
            print(f"WARNING: Environment variable '{env_var_name}' is not set. Supabase features may not work.", file=sys.stderr)
        return v

    # OpenFoodFacts
    OPENFOODFACTS_USER_AGENT: str = os.getenv(
        "OPENFOODFACTS_USER_AGENT", "MeatWise - https://github.com/PPSpiderman/meat-products-api"
    )
    
    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    @field_validator("GEMINI_API_KEY", mode="before")
    def warn_if_gemini_missing(cls, v: str) -> str:
        """Warn if Gemini API Key is not set."""
        if not v:
            logging.warning("Environment variable 'GEMINI_API_KEY' is not set. Gemini features may not work.")
            print("WARNING: Environment variable 'GEMINI_API_KEY' is not set. Gemini features may not work.", file=sys.stderr)
        return v

    # Replace the Config inner class with model_config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",  # Allow extra fields to be set
    )


settings = Settings()