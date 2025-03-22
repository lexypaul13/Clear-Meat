"""Input validation middleware for the MeatWise API."""

import re
from fastapi import FastAPI, Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, List, Optional, Pattern, Set
import json
from starlette.types import ASGIApp


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate and sanitize incoming requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        blocked_patterns: Optional[List[str]] = None,
        content_types: Optional[Set[str]] = None,
        max_content_length: int = 1024 * 1024,  # 1MB default
    ):
        """
        Initialize with validation rules.
        
        Args:
            app: The ASGI app
            blocked_patterns: Regex patterns to block in request bodies
            content_types: Allowed content types
            max_content_length: Maximum content length in bytes
        """
        super().__init__(app)
        
        # Default blocked patterns for common injection attacks
        self.blocked_patterns: List[Pattern] = []
        default_patterns = [
            r"(?i)<script.*?>.*?</script.*?>",  # XSS
            r"(?i)javascript\s*:",              # JavaScript injection
            r"(?i)on\w+\s*=",                   # Event handlers
            r"(?i)select.*?from.*?;",           # SQL injection
            r"(?i)union.*?select",              # SQL injection
            r"(?i)insert.*?into",               # SQL injection
            r"(?i)drop.*?table",                # SQL injection
            r"(?i)delete.*?from",               # SQL injection
        ]
        
        # Combine default and custom patterns
        patterns_to_use = default_patterns + (blocked_patterns or [])
        for pattern in patterns_to_use:
            self.blocked_patterns.append(re.compile(pattern))
            
        # Content type validation
        self.content_types = content_types or {
            "application/json", 
            "multipart/form-data", 
            "application/x-www-form-urlencoded"
        }
        
        # Maximum content length
        self.max_content_length = max_content_length
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate and sanitize the request."""
        # Validate Content-Type
        content_type = request.headers.get("content-type", "").split(";")[0].lower()
        if content_type and content_type not in self.content_types:
            return Response(
                content=json.dumps({"detail": "Unsupported content type"}),
                status_code=415,
                media_type="application/json"
            )
        
        # Validate Content-Length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return Response(
                content=json.dumps({"detail": "Request body too large"}),
                status_code=413,
                media_type="application/json"
            )
        
        # Check for suspicious patterns in request body
        if content_type == "application/json":
            try:
                body = await request.json()
                body_str = json.dumps(body)
                
                for pattern in self.blocked_patterns:
                    if pattern.search(body_str):
                        return Response(
                            content=json.dumps({"detail": "Invalid input detected"}),
                            status_code=400,
                            media_type="application/json"
                        )
            except Exception:
                # If we can't parse the body, continue with the request
                pass
        
        # Process the request
        return await call_next(request)


class PathTraversalMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent path traversal attacks."""
    
    def __init__(self, app: ASGIApp):
        """Initialize the middleware."""
        super().__init__(app)
        self.path_traversal_pattern = re.compile(r"\.\.\/|\.\.\\")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check for path traversal attempts."""
        path = request.url.path
        
        # Check for path traversal
        if self.path_traversal_pattern.search(path):
            return Response(
                content=json.dumps({"detail": "Invalid path"}),
                status_code=400,
                media_type="application/json"
            )
        
        # Process the request
        return await call_next(request)


def add_validation_middleware(app: FastAPI) -> None:
    """Add all validation middleware to the app."""
    # Add request validation middleware
    app.add_middleware(RequestValidationMiddleware)
    
    # Add path traversal protection
    app.add_middleware(PathTraversalMiddleware) 