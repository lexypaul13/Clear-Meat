"""Main application module."""

import sys
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

try:
    from app.core.config import settings
except ValueError as e:
    print(f"Error loading application settings: {e}", file=sys.stderr)
    print("Please set required environment variables. See .env.example for reference.", file=sys.stderr)
    sys.exit(1)

from app.routers import api_router
from app.middleware.security import add_security_middleware
from app.middleware.validation import add_validation_middleware
from app.middleware.caching import add_caching_middleware
from app.db.session import close_db_connections

# Configure logger
logger = logging.getLogger(__name__)

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
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
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
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/health/db", tags=["Health"])
async def db_health_check():
    """Database connection health check."""
    try:
        # Import here to avoid circular imports
        from app.db.session import get_db
        
        # Get database session and test connection
        db = next(get_db())
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"}
        )

# Register shutdown event handler
@app.on_event("shutdown")
def shutdown_event():
    """Handle graceful shutdown."""
    logger.info("Application shutting down...")
    close_db_connections()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 