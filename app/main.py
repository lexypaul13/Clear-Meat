"""
Main application module for the MeatWise API.
"""

import sys
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import os

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Enable DEBUG logging for httpx/httpcore to log API requests
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.DEBUG)

try:
    from app.core.config import settings
    
    # Add debug logging for environment variables
    logger.debug(f"Loaded settings from app.core.config")
    logger.debug(f"SUPABASE_URL (from settings): {settings.SUPABASE_URL}")
    logger.debug(f"SUPABASE_URL length: {len(settings.SUPABASE_URL) if settings.SUPABASE_URL else 0}")
    logger.debug(f"SUPABASE_KEY set: {'Yes (hidden)' if settings.SUPABASE_KEY else 'No'}")
    logger.debug(f"Env: SUPABASE_URL={os.environ.get('SUPABASE_URL', '(not set)')}")
    logger.debug(f"Env: SUPABASE_KEY={'(set but hidden)' if os.environ.get('SUPABASE_KEY') else '(not set)'}")
except ValueError as e:
    print(f"Error loading application settings: {e}", file=sys.stderr)
    print("Please set required environment variables. See .env.example for reference.", file=sys.stderr)
    sys.exit(1)

from app.routers import api_router
from app.middleware.security import add_security_middleware
from app.middleware.validation import add_validation_middleware
from app.middleware.caching import add_caching_middleware
from app.db.connection import close_db_connections, is_using_local_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API for the MeatWise application",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Add security middleware
add_security_middleware(app)

# Add validation middleware
add_validation_middleware(app)

# Add caching middleware
add_caching_middleware(app)

# Set all CORS enabled origins
if settings.parsed_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.parsed_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # If no origins are defined, allow all for local development or specific cases
    # WARNING: This might be too permissive for production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Add health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "timestamp": time.time(), "using_local_db": is_using_local_db()}

@app.get("/health/db", tags=["Health"])
async def db_health_check():
    """Database connection health check."""
    # Check if we're in testing mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    # In testing mode, skip the actual database check
    if is_testing:
        return {"status": "healthy", "database": "connected", "mode": "testing"}
        
    try:
        # Import here to avoid circular imports
        from app.db.supabase_client import get_supabase_service
        
        # Get Supabase service and test connection
        supabase_service = get_supabase_service()
        # Check if service is available
        if supabase_service:
            return {"status": "healthy", "database": "connected"}
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "database": "disconnected"}
            )
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"}
        )

# Add Supabase health check endpoint
@app.get("/health/supabase", tags=["Health"])
async def supabase_health_check():
    """Supabase connection health check."""
    try:
        # Import here to avoid circular imports
        from app.db.supabase_client import get_supabase
        
        # Test Supabase connection
        supabase = get_supabase()
        if not supabase:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "supabase": "client_init_failed"}
            )
            
        # Try a simple query that doesn't count all records
        try:
            # Use a faster query - select a single record instead of counting all
            test_response = supabase.table("products").select("code").limit(1).execute()
            return {
                "status": "healthy", 
                "supabase": "connected",
                "data": test_response.data if test_response.data else None
            }
        except Exception as query_err:
            logger.error(f"Supabase query failed: {str(query_err)}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "unhealthy", "supabase": "query_failed", "error": str(query_err)}
            )
    except Exception as e:
        logger.error(f"Supabase health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "supabase": "disconnected", "error": str(e)}
        )

# Register startup event handler
@app.on_event("startup")
def startup_event():
    """Handle application startup events."""
    logger.info("Application starting up...")
    
    # Log environment variables (sanitized)
    env_vars = {
        k: v if not k.endswith(("KEY", "SECRET", "PASSWORD", "TOKEN")) else "(hidden)"
        for k, v in os.environ.items()
        if k.startswith(("API_", "SUPABASE_", "DATABASE_", "TESTING"))
    }
    logger.debug(f"Environment variables: {env_vars}")
    
    # Test Supabase connection at startup
    try:
        # Import here to avoid circular imports
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()
        logger.info("Supabase client initialized successfully at startup")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client at startup: {str(e)}")
        # Don't fail startup, just log the error

# Register shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    """Handle graceful shutdown."""
    logger.info("Application shutting down...")
    close_db_connections()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 