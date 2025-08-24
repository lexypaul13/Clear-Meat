"""Rate limiting middleware for guest users."""

import time
from typing import Dict, Optional
from fastapi import HTTPException, Request, status
import logging

logger = logging.getLogger(__name__)

class SimpleRateLimiter:
    """Simple in-memory rate limiter for guest users."""
    
    def __init__(self):
        # Store: IP -> [(timestamp, count)]
        self._requests: Dict[str, list] = {}
        
    def is_allowed(self, ip: str, limit: int = 5, window_hours: int = 1) -> bool:
        """
        Check if IP is allowed to make a request.
        
        Args:
            ip: Client IP address
            limit: Maximum requests per window (default: 5)
            window_hours: Window size in hours (default: 1)
            
        Returns:
            bool: True if request is allowed
        """
        current_time = time.time()
        window_seconds = window_hours * 3600
        
        # Clean up old requests
        if ip in self._requests:
            self._requests[ip] = [
                req_time for req_time in self._requests[ip]
                if current_time - req_time < window_seconds
            ]
        else:
            self._requests[ip] = []
        
        # Check if limit exceeded
        if len(self._requests[ip]) >= limit:
            return False
        
        # Add current request
        self._requests[ip].append(current_time)
        return True
    
    def get_remaining_requests(self, ip: str, limit: int = 5) -> int:
        """Get remaining requests for IP."""
        if ip not in self._requests:
            return limit
        return max(0, limit - len(self._requests[ip]))
    
    def get_reset_time(self, ip: str, window_hours: int = 1) -> Optional[float]:
        """Get when the rate limit resets for this IP."""
        if ip not in self._requests or not self._requests[ip]:
            return None
        
        oldest_request = min(self._requests[ip])
        return oldest_request + (window_hours * 3600)

# Global rate limiter instance
rate_limiter = SimpleRateLimiter()

def check_guest_rate_limit(request: Request, user = None) -> None:
    """
    Check rate limit for guest users.
    
    Args:
        request: FastAPI request object
        user: Current user (None for guests)
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Skip rate limiting for authenticated users
    if user is not None:
        return
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check if real IP is in headers (for proxies)
    real_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For")
    if real_ip:
        client_ip = real_ip.split(",")[0].strip()
    
    logger.info(f"Checking rate limit for guest IP: {client_ip}")
    
    # Check rate limit (5 requests per hour)
    if not rate_limiter.is_allowed(client_ip, limit=5, window_hours=1):
        remaining = rate_limiter.get_remaining_requests(client_ip, limit=5)
        reset_time = rate_limiter.get_reset_time(client_ip, window_hours=1)
        
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        
        # Calculate minutes until reset
        reset_minutes = int((reset_time - time.time()) / 60) if reset_time else 60
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Guest users can scan 5 products per hour. Try again in {reset_minutes} minutes or create an account for unlimited scans.",
            headers={
                "X-RateLimit-Limit": "5",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(reset_time)) if reset_time else "",
            }
        )
    
    # Log successful rate limit check
    remaining = rate_limiter.get_remaining_requests(client_ip, limit=5)
    logger.info(f"Rate limit OK for IP: {client_ip}, remaining: {remaining}")