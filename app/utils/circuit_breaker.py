"""Circuit breaker utility for preventing cascade failures."""
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict

from app import models

logger = logging.getLogger(__name__)


def with_circuit_breaker(timeout: float = 25.0, fallback_response: Any = None):
    """
    Circuit breaker decorator to prevent 502 gateway timeouts.
    
    Args:
        timeout: Maximum execution time in seconds (default 25s for Railway's 30s limit)
        fallback_response: Response to return on failure (default empty recommendations)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Execute with timeout protection
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                
                # Log successful execution time
                duration = asyncio.get_event_loop().time() - start_time
                logger.info(f"[Circuit Breaker] {func.__name__} completed in {duration:.2f}s")
                
                return result
                
            except asyncio.TimeoutError:
                duration = asyncio.get_event_loop().time() - start_time
                logger.error(f"[Circuit Breaker] {func.__name__} timed out after {duration:.2f}s")
                
                # Return fallback response instead of 502
                if fallback_response is not None:
                    return fallback_response
                else:
                    return models.RecommendationResponse(
                        recommendations=[],
                        total_matches=0
                    )
                    
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                logger.error(f"[Circuit Breaker] {func.__name__} failed after {duration:.2f}s: {e}")
                
                # Return fallback response instead of 500
                if fallback_response is not None:
                    return fallback_response
                else:
                    return models.RecommendationResponse(
                        recommendations=[],
                        total_matches=0
                    )
        
        return wrapper
    return decorator


def with_db_timeout(timeout: float = 10.0):
    """
    Database operation timeout decorator.
    
    Args:
        timeout: Maximum database operation time in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                logger.error(f"[DB Timeout] {func.__name__} timed out after {timeout}s")
                raise
        return wrapper
    return decorator
