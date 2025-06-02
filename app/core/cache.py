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
        self.local_cache = {}  # Fallback in-memory cache
        
        # Set up Redis if available
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Connected to Redis for caching")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        # Try Redis first
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to local cache
        if key in self.local_cache:
            entry = self.local_cache[key]
            if entry['expires_at'] > time.time():
                return entry['data']
            else:
                # Clean up expired entry
                del self.local_cache[key]
        
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
        
        # Store in Redis if available
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
        
        # Always store in local cache as fallback
        self.local_cache[key] = {
            'data': value,
            'expires_at': time.time() + ttl
        }
        
        # Clean up old entries periodically
        if len(self.local_cache) > 1000:
            self._cleanup_local_cache()
        
        return True
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        success = False
        
        # Delete from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                success = True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        # Delete from local cache
        if key in self.local_cache:
            del self.local_cache[key]
            success = True
        
        return success
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "search:*")
            
        Returns:
            Number of keys deleted
        """
        count = 0
        
        # Clear from Redis
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count += self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis clear pattern error: {e}")
        
        # Clear from local cache
        keys_to_delete = [k for k in self.local_cache.keys() if self._match_pattern(k, pattern)]
        for key in keys_to_delete:
            del self.local_cache[key]
            count += 1
        
        return count
    
    def _cleanup_local_cache(self):
        """Remove expired entries from local cache."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.local_cache.items()
            if v['expires_at'] <= current_time
        ]
        for key in expired_keys:
            del self.local_cache[key]
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for local cache."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
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