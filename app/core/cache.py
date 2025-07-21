"""Unified caching service for the Clear-Meat API."""

import json
import time
import hashlib
import logging
from typing import Any, Optional, Union
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Unified caching service with Redis support and in-memory fallback."""
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600):
        """
        Initialize cache service.
        
        Args:
            redis_url: Optional Redis URL for distributed caching
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.redis_client = None
        self.default_ttl = default_ttl
        
        # Set up Redis - required for caching
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Connected to Redis for caching")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        else:
            logger.warning("Redis not configured - caching disabled")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        # Only use Redis - no fallback
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # No cache available - return None to force fresh generation
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        ttl = ttl or self.default_ttl
        
        # Store in Redis only
        if self.redis_client:
            try:
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                return False
        
        # No cache available
        return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        # Delete from Redis only
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
                return False
        
        return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "search:*")
            
        Returns:
            Number of keys deleted
        """
        count = 0
        
        # Clear from Redis only
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis clear pattern error: {e}")
        
        return count
    
    
    def cache_html_structure(self, url: str, parsed_data: dict, ttl: int = 3600) -> bool:
        """Cache parsed HTML structure to avoid re-parsing the same page."""
        cache_key = f"html_structure:{hashlib.md5(url.encode()).hexdigest()}"
        return self.set(cache_key, parsed_data, ttl)
    
    def get_cached_html_structure(self, url: str) -> Optional[dict]:
        """Get cached HTML structure if available."""
        cache_key = f"html_structure:{hashlib.md5(url.encode()).hexdigest()}"
        return self.get(cache_key)
    
    @staticmethod
    def generate_key(*args, prefix: str = "cache") -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Arguments to include in key
            prefix: Key prefix
            
        Returns:
            Generated cache key
        """
        # Create a string representation of all arguments
        key_parts = [str(arg) for arg in args]
        key_string = ":".join(key_parts)
        
        # For long keys, use a hash
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return f"{prefix}:{key_string}"


# Global cache instance
cache = CacheService(
    redis_url=settings.REDIS_URL,
    default_ttl=settings.REDIS_TTL
) 