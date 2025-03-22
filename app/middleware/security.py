"""Security middleware for the MeatWise API."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List
import time
from starlette.datastructures import Headers
from starlette.types import ASGIApp
from app.core.config import settings


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
    """Simple rate limiting middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        limit: int = 60,  # Default: 60 requests
        window: int = 60,  # Default: per minute
        by_ip: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            app: The ASGI app
            limit: Maximum number of requests allowed
            window: Time window in seconds
            by_ip: Whether to track by IP address
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.by_ip = by_ip
        self.requests: Dict[str, List[float]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting logic."""
        key = request.client.host if self.by_ip else "global"
        
        # Clean up old timestamps
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
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": str(self.window)}
            )
        
        # Add current request timestamp
        self.requests[key].append(now)
        
        # Process the request
        return await call_next(request)


def add_security_middleware(app: FastAPI) -> None:
    """Add all security middleware to the app."""
    # Add security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        content_security_policy="default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        limit=settings.RATE_LIMIT_PER_MINUTE,  # Use configured rate limit
        window=60,  # per minute
        by_ip=settings.RATE_LIMIT_BY_IP  # Use configured setting
    ) 