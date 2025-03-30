"""Security middleware for the MeatWise API."""

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List, Optional
import time
import json
from datetime import datetime
from starlette.datastructures import Headers
from starlette.types import ASGIApp
from app.core.config import settings
from fastapi.responses import JSONResponse

# Redis imports - will be conditionally used
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""
    
    def __init__(
        self,
        app: ASGIApp,
        content_security_policy: str = None,
        include_default_headers: bool = True,
    ):
        """Initialize with custom or default headers."""
        super().__init__(app)
        self.headers: Dict[str, str] = {}
        
        if include_default_headers:
            self.headers.update({
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
            })
        
        if content_security_policy:
            self.headers["Content-Security-Policy"] = content_security_policy
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)
        
        for header_key, header_value in self.headers.items():
            response.headers[header_key] = header_value
            
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis support for distributed deployments."""
    
    def __init__(
        self,
        app: ASGIApp,
        limit: int = 60,  # Default: 60 requests
        window: int = 60,  # Default: per minute
        by_ip: bool = True,
        redis_url: Optional[str] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            app: The ASGI app
            limit: Maximum number of requests allowed
            window: Time window in seconds
            by_ip: Whether to track by IP address
            redis_url: Optional Redis URL for distributed rate limiting
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.by_ip = by_ip
        self.requests: Dict[str, List[float]] = {}
        
        # Set up Redis connection if URL provided and Redis is available
        self.redis_client = None
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url)
                # Test connection
                self.redis_client.ping()
                print("Connected to Redis for distributed rate limiting")
            except Exception as e:
                print(f"Failed to connect to Redis: {str(e)}")
                self.redis_client = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting logic."""
        key = request.client.host if self.by_ip else "global"
        
        # Use Redis for distributed rate limiting if available
        if self.redis_client:
            redis_key = f"ratelimit:{key}"
            current_time = time.time()
            
            # Using Redis sorted set to track timestamps
            # Remove expired timestamps (older than window)
            self.redis_client.zremrangebyscore(redis_key, 0, current_time - self.window)
            
            # Count remaining valid timestamps
            request_count = self.redis_client.zcard(redis_key)
            
            # Check if rate limit exceeded
            if request_count >= self.limit:
                return JSONResponse(
                    content={"detail": "Rate limit exceeded. Please try again later."},
                    status_code=429,
                    headers={"Retry-After": str(self.window)}
                )
            
            # Add current request timestamp
            self.redis_client.zadd(redis_key, {str(current_time): current_time})
            # Set expiration on the key to auto-cleanup
            self.redis_client.expire(redis_key, self.window * 2)
        else:
            # Fallback to in-memory rate limiting
            now = time.time()
            if key in self.requests:
                self.requests[key] = [
                    timestamp for timestamp in self.requests[key]
                    if now - timestamp < self.window
                ]
            else:
                self.requests[key] = []
            
            # Check if rate limit exceeded
            if len(self.requests[key]) >= self.limit:
                return JSONResponse(
                    content={"detail": "Rate limit exceeded. Please try again later."},
                    status_code=429,
                    headers={"Retry-After": str(self.window)}
                )
            
            # Add current request timestamp
            self.requests[key].append(now)
        
        # Process the request
        return await call_next(request)


class JWTErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle JWT token errors gracefully."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle JWT token errors."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_detail = str(exc)
            status_code = 500
            
            # Check for common JWT errors
            if "expired" in error_detail.lower() and "token" in error_detail.lower():
                status_code = 401
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": "Authentication token has expired. Please log in again."}
                )
            elif "invalid" in error_detail.lower() and "token" in error_detail.lower():
                status_code = 401
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": "Invalid authentication token. Please log in again."}
                )
            
            # Re-raise other exceptions to be handled by FastAPI
            raise


def add_security_middleware(app: FastAPI) -> None:
    """Add all security middleware to the app."""
    # Add security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        content_security_policy="default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
    )
    
    # Add JWT error handler middleware
    app.add_middleware(JWTErrorHandlerMiddleware)
    
    # Add rate limiting middleware
    redis_url = getattr(settings, "REDIS_URL", None)
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.RATE_LIMIT_PER_MINUTE,
        window=60,  # per minute
        by_ip=settings.RATE_LIMIT_BY_IP,
        redis_url=redis_url
    ) 