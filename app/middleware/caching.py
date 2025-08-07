"""Caching middleware for the MeatWise API."""

import json
import hashlib
import time
import logging
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List, Optional, Set
from starlette.types import ASGIApp
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis imports - will be conditionally used
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CachingMiddleware(BaseHTTPMiddleware):
    """Middleware to cache response data to improve performance."""
    
    def __init__(
        self,
        app: ASGIApp,
        cacheable_paths: Optional[List[str]] = None,
        ttl: int = 3600,  # Default: 1 hour
        redis_url: Optional[str] = None,
    ):
        """
        Initialize caching middleware.
        
        Args:
            app: The ASGI app
            cacheable_paths: List of path prefixes that should be cached
            ttl: Time-to-live for cached data in seconds
            redis_url: Optional Redis URL for distributed caching
        """
        super().__init__(app)
        self.cacheable_paths = cacheable_paths or [
            "/api/v1/products/", 
            "/api/v1/ingredients/"
        ]
        self.ttl = ttl
        self.local_cache: Dict[str, Dict] = {}
        
        # Set up Redis connection if URL provided and Redis is available
        self.redis_client = None
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url)
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis for response caching")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for caching: {str(e)}")
                self.redis_client = None
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate a unique cache key based on path and query parameters."""
        # Create a unique key based on path and query parameters
        key_parts = [
            request.method,
            request.url.path,
            str(sorted([(k, v) for k, v in request.query_params.items()]))
        ]
        
        # Add a hash of the path to make the key safer for storage
        key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
        return f"cache:{key}"
    
    def _is_cacheable(self, request: Request) -> bool:
        """Determine if the request should be cached."""
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Check if the path should be cached
        for path in self.cacheable_paths:
            if request.url.path.startswith(path):
                return True
                
        return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply caching logic."""
        # Check if request should be cached
        if not self._is_cacheable(request):
            return await call_next(request)
            
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        cached_response = None
        
        # Try Redis first if available
        if self.redis_client:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                try:
                    cached_response = json.loads(cached_data)
                except Exception:
                    # If we can't parse the cached data, ignore it
                    pass
        # Try local cache otherwise
        elif cache_key in self.local_cache:
            cached_entry = self.local_cache[cache_key]
            # Check if entry is still valid
            if time.time() < cached_entry.get("expires_at", 0):
                cached_response = cached_entry.get("data")
            else:
                # Remove expired entry
                del self.local_cache[cache_key]
                
        if cached_response:
            # Return cached response
            return Response(
                content=cached_response.get("content"),
                status_code=cached_response.get("status_code", 200),
                headers=cached_response.get("headers", {}),
                media_type=cached_response.get("media_type", "application/json")
            )
        
        # Process the request
        response = await call_next(request)
        
        # Cache successful responses
        if 200 <= response.status_code < 300:
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
                
            # Create a new response with the same body
            new_response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            # Cache response data
            response_data = {
                "content": response_body,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "media_type": response.media_type
            }
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        cache_key,
                        self.ttl,
                        json.dumps(response_data)
                    )
                except Exception as e:
                    logger.error(f"Failed to cache response in Redis: {str(e)}")
            # Store in local cache otherwise
            else:
                self.local_cache[cache_key] = {
                    "data": response_data,
                    "expires_at": time.time() + self.ttl
                }
                
            return new_response
        
        return response


def add_caching_middleware(app: FastAPI) -> None:
    """Add caching middleware to the app."""
    redis_url = getattr(settings, "REDIS_URL", None)
    ttl = getattr(settings, "REDIS_TTL", 3600)
    
    app.add_middleware(
        CachingMiddleware,
        ttl=ttl,
        redis_url=redis_url
    ) 