"""Security middleware for the MeatWise API."""

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List, Optional, Set, Tuple
import time
import json
import logging
from datetime import datetime
from starlette.datastructures import Headers
from starlette.types import ASGIApp
from app.core.config import settings
from fastapi.responses import JSONResponse

# Configure logger
logger = logging.getLogger(__name__)

# Redis imports - will be conditionally used
try:
    import redis
    REDIS_AVAILABLE = True
    logger.info("Redis package is installed. Distributed rate limiting is available.")
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis package not installed. Rate limiting will use in-memory storage.")


class RedisManager:
    """Manages Redis connections with fallback and reconnection support."""
    
    def __init__(self, redis_url: str):
        """Initialize Redis manager with the given URL."""
        self.redis_url = redis_url
        self.client = None
        self.last_error_time = 0
        self.error_count = 0
        self.max_errors = 3
        self.retry_interval = 10  # seconds
        self.connected = False
        self.initialize()
    
    def initialize(self) -> None:
        """Initialize the Redis client if Redis is available."""
        if not REDIS_AVAILABLE or not self.redis_url:
            logger.warning("Redis is not available or URL not provided. Using in-memory storage.")
            return
            
        try:
            logger.info(f"Connecting to Redis at {self.redis_url}")
            self.client = redis.from_url(
                self.redis_url,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            self.connected = True
            self.error_count = 0
            logger.info("Successfully connected to Redis")
        except Exception as e:
            self.connected = False
            self.error_count += 1
            self.last_error_time = time.time()
            logger.error(f"Failed to connect to Redis: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Redis is available for use."""
        # If Redis package is not installed, it's not available
        if not REDIS_AVAILABLE:
            return False
            
        # If we've had too many errors, check if we should retry
        if self.error_count >= self.max_errors:
            now = time.time()
            if now - self.last_error_time >= self.retry_interval:
                # Try to reconnect
                logger.info("Attempting to reconnect to Redis after errors")
                self.initialize()
            
        # Return current connection status
        return self.connected and self.client is not None
    
    def execute(self, operation: str, *args, **kwargs):
        """Execute a Redis operation with error handling and fallback."""
        if not self.is_available():
            return None
            
        try:
            # Get the operation method from the client
            method = getattr(self.client, operation)
            return method(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Redis operation {operation} failed: {str(e)}")
            self.connected = False
            self.error_count += 1
            self.last_error_time = time.time()
            return None


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
        redis_url: Optional[str] = None,
        exempt_patterns: Optional[List[str]] = None,
        exempt_ips: Optional[List[str]] = None,
        include_headers: bool = True,
        debug_mode: bool = False
    ):
        """
        Initialize rate limiter.
        
        Args:
            app: The ASGI app
            limit: Maximum number of requests allowed
            window: Time window in seconds
            by_ip: Whether to track by IP address
            redis_url: Optional Redis URL for distributed rate limiting
            exempt_patterns: URL patterns to exempt from rate limiting
            exempt_ips: IP addresses to exempt from rate limiting
            include_headers: Whether to include rate limit headers in responses
            debug_mode: Enable debug logging for rate limiting
        """
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.by_ip = by_ip
        self.requests: Dict[str, List[float]] = {}
        self.exempt_patterns = exempt_patterns or ["/health", "/docs", "/openapi.json"]
        self.exempt_ips = set(exempt_ips or [])  # Empty set - no exempt IPs for testing
        self.include_headers = include_headers
        self.debug_mode = debug_mode
        
        # Set up Redis connection if URL provided
        self.redis_manager = RedisManager(redis_url) if redis_url else None
        
        logger.info(f"Configuring rate limiting: {limit} requests per {window} seconds, by IP: {by_ip}, Redis: {redis_url or 'not available'}")
        
        # Debug counters for monitoring
        if self.debug_mode:
            self.total_requests = 0
            self.exempt_requests = 0
            self.rate_limited_requests = 0
    
    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug_mode:
            logger.debug(message)
    
    def _is_exempt(self, request: Request) -> bool:
        """Check if request is exempt from rate limiting."""
        # Check exempt patterns
        path = request.url.path
        for pattern in self.exempt_patterns:
            if pattern in path:
                self._log_debug(f"Request to {path} is exempt (matched pattern {pattern})")
                return True
                
        # Check exempt IPs
        client_host = request.client.host
        if client_host in self.exempt_ips:
            self._log_debug(f"Request from {client_host} is exempt (ip in exempt list)")
            return True
            
        return False
    
    def _get_rate_limit_info(self, key: str) -> Tuple[int, int]:
        """Get current rate limit info (requests_count, remaining)."""
        if self.redis_manager and self.redis_manager.is_available():
            redis_key = f"ratelimit:{key}"
            current_time = time.time()
            
            # Remove expired timestamps
            self.redis_manager.execute('zremrangebyscore', redis_key, 0, current_time - self.window)
            
            # Count remaining valid timestamps
            request_count = self.redis_manager.execute('zcard', redis_key) or 0
            remaining = max(0, self.limit - request_count)
            
            return request_count, remaining
        else:
            # In-memory storage
            now = time.time()
            if key not in self.requests:
                self.requests[key] = []
                return 0, self.limit
                
            # Filter out expired timestamps
            valid_requests = [
                timestamp for timestamp in self.requests[key]
                if now - timestamp < self.window
            ]
            
            # Update the requests list with only valid timestamps
            self.requests[key] = valid_requests
            
            return len(valid_requests), max(0, self.limit - len(valid_requests))
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting logic."""
        # Track request in debug mode
        if self.debug_mode:
            self.total_requests += 1
            self._log_debug(f"Processing request #{self.total_requests}: {request.method} {request.url.path}")
            
        # Skip rate limiting for exempt requests
        if self._is_exempt(request):
            if self.debug_mode:
                self.exempt_requests += 1
                self._log_debug(f"Request exempt from rate limiting. Total exempt: {self.exempt_requests}")
            return await call_next(request)
            
        # Get client identifier
        client_ip = request.client.host
        key = client_ip if self.by_ip else "global"
        
        # Log the request for debugging
        self._log_debug(f"Rate limit check for {key} (URL: {request.url.path})")
        
        # Check if rate limit exceeded
        request_count, remaining = self._get_rate_limit_info(key)
        
        # Add this request immediately to prevent race conditions
        now = time.time()
        if self.redis_manager and self.redis_manager.is_available():
            redis_key = f"ratelimit:{key}"
            # Add current request timestamp
            self.redis_manager.execute('zadd', redis_key, {str(now): now})
            # Set expiration on the key to auto-cleanup
            self.redis_manager.execute('expire', redis_key, self.window * 2)
            # Count is now one higher
            request_count += 1
            remaining = max(0, self.limit - request_count)
        else:
            # Fallback to in-memory rate limiting
            if key not in self.requests:
                self.requests[key] = []
            # Add current request timestamp
            self.requests[key].append(now)
            # Update count
            request_count += 1
            remaining = max(0, self.limit - request_count)
        
        # Time until the oldest request expires
        time_to_reset = int(self.window - (now - min(self.requests[key]))) if self.requests[key] else self.window
        reset_time = int(time.time() + time_to_reset)
        
        self._log_debug(f"Current request count for {key}: {request_count}/{self.limit}, remaining: {remaining}, reset in {time_to_reset}s")
        
        # Check if over limit
        if request_count > self.limit:
            if self.debug_mode:
                self.rate_limited_requests += 1
                self._log_debug(f"Rate limit exceeded for {key}. Total limited: {self.rate_limited_requests}")
                
            logger.warning(f"Rate limit exceeded for {key} ({request_count}/{self.limit} requests)")
            
            response = JSONResponse(
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "status": "error",
                    "code": "TOO_MANY_REQUESTS",
                    "retry_after": time_to_reset
                },
                status_code=429,
                headers={"Retry-After": str(time_to_reset)}
            )
            
            # Add rate limit headers
            if self.include_headers:
                response.headers["X-RateLimit-Limit"] = str(self.limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(reset_time)
                response.headers["X-RateLimit-Reset-After"] = str(time_to_reset)
                
            return response
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if self.include_headers:
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - request_count))
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            response.headers["X-RateLimit-Reset-After"] = str(time_to_reset)
        
        return response


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
    
    # Add rate limiting middleware - IMPORTANT: Add this BEFORE other middleware to ensure it's applied first
    redis_url = getattr(settings, "REDIS_URL", None)
    rate_limit = getattr(settings, "RATE_LIMIT_PER_MINUTE", 10)
    rate_limit_by_ip = getattr(settings, "RATE_LIMIT_BY_IP", True)
    
    # Print rate limit configuration for debugging
    logger.info(f"Configuring rate limiting: {rate_limit} requests per minute, by IP: {rate_limit_by_ip}, Redis: {redis_url}")
    
    app.add_middleware(
        RateLimitMiddleware,
        limit=rate_limit,
        window=60,  # per minute
        by_ip=rate_limit_by_ip,
        redis_url=redis_url,
        exempt_patterns=["/health", "/docs", "/openapi.json", "/redoc"],
        exempt_ips=[],  # No exempt IPs for testing
        include_headers=True,
        debug_mode=settings.DEBUG
    ) 