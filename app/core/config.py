"""Settings module for the MeatWise API."""

import os
import secrets
import sys
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

# Update the imports for pydantic v2
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class for the MeatWise API."""

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "MeatWise API"
    PROJECT_VERSION: str = "0.1.0"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"  # Algorithm for JWT encoding
    
    @field_validator("SECRET_KEY", mode="before")
    def validate_secret_key(cls, v: Optional[str]) -> str:
        """Validate the secret key."""
        if not v or len(v) < 32:
            if not os.environ.get("SECRET_KEY"):
                # Warn that we're using a generated key
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
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Validate CORS origins."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "")
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

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

    # OpenFoodFacts
    OPENFOODFACTS_USER_AGENT: str = os.getenv(
        "OPENFOODFACTS_USER_AGENT", "MeatWise - https://github.com/PPSpiderman/meat-products-api"
    )

    # Replace the Config inner class with model_config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",  # Allow extra fields to be set
    )


settings = Settings()