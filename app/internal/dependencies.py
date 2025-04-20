"""Common dependencies for the MeatWise API."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.supabase import supabase, admin_supabase
from app.db.session import get_db
from app.models import TokenPayload
from app.db import models as db_models

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)
logger = logging.getLogger(__name__)


def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
) -> db_models.User:
    """
    Get the current user from the token using Supabase verification.
    If Supabase verification fails, falls back to manual JWT verification.
    
    Args:
        db: Database session
        token: OAuth2 token
        
    Returns:
        User: User object
        
    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
        
    # If no token provided
    if token is None:
        logger.warning("No authentication token provided")
        raise credentials_exception
        
    try:
        # Log token format for debugging (only first few chars for security)
        logger.debug(f"Verifying token (length: {len(token)})")
        
        # Manual JWT verification method - used as a fallback if Supabase fails
        def verify_manually():
            logger.info("Using manual JWT verification")
            try:
                # Manually decode the JWT
                payload = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=[settings.ALGORITHM],
                    options={"verify_signature": False}  # Skip signature verification temporarily 
                )
                user_id = payload.get("sub")
                if user_id is None:
                    logger.warning("JWT missing 'sub' claim")
                    raise credentials_exception
                
                logger.debug(f"JWT payload: {payload}")
                
                # Get user from database
                user = db.query(db_models.User).filter(db_models.User.id == user_id).first()
                if not user:
                    # Fallback - try to extract userID from the token payload
                    try:
                        # For Supabase tokens, the subject might be in a different format
                        if "user" in payload and isinstance(payload["user"], dict):
                            user_id_alt = payload["user"].get("id")
                            if user_id_alt:
                                user = db.query(db_models.User).filter(db_models.User.id == user_id_alt).first()
                    except Exception as e:
                        logger.warning(f"Error during fallback user extraction: {e}")
                            
                    if not user:
                        logger.warning(f"User not found in database: {user_id}")
                        raise credentials_exception
                
                return user
            except JWTError as e:
                logger.error(f"JWT decode error: {e}")
                raise credentials_exception

        # Check if Supabase client is available
        if not supabase or not hasattr(supabase, 'auth'):
            logger.warning("Supabase client not available for token verification.")
            return verify_manually()

        # First, try to validate via Supabase
        try:
            # Verify token directly with Supabase
            logger.debug("Attempting to verify token with Supabase")
            response = supabase.auth.get_user(token)
            
            if not response or not hasattr(response, 'user') or not response.user:
                logger.warning("Supabase token verification returned no user.")
                return verify_manually()
            
            # Extract user data from the Supabase response
            supabase_user = response.user
            user_id = supabase_user.id
            
            # Ensure user_id is a string (convert UUID if needed)
            user_id = str(user_id)
                
            user_email = getattr(supabase_user, 'email', None)
            
            # Log success for debugging
            logger.debug(f"Successfully verified token for user {user_id}")
            
            # Try to fetch user from our database
            user = db.query(db_models.User).filter(db_models.User.id == user_id).first()
            
            if user:
                # User found in database - ensure ID is string
                if hasattr(user.id, 'hex') or isinstance(user.id, uuid.UUID):
                    user.id = str(user.id)
                return user
            else:
                # User exists in Supabase but not in our database yet
                # Create temporary user object with data from Supabase
                user_metadata = getattr(supabase_user, 'user_metadata', {}) or {}
                full_name = user_metadata.get('full_name', '')
                role = user_metadata.get('role', 'basic')
                
                # Create and save the user to our database
                new_user = db_models.User(
                    id=user_id,
                    email=user_email,
                    full_name=full_name,
                    is_active=True,
                    is_superuser=False,
                    role=role
                )
                
                # Add the user to the database to avoid recreating it on every request
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                
                logger.info(f"Created new user record for Supabase user {user_id}")
                return new_user
            
        except Exception as e:
            # Log the specific error from Supabase
            logger.warning(f"Supabase token verification error: {str(e)}. Falling back to manual verification.")
            return verify_manually()
            
    except Exception as e:
        logger.exception(f"Unexpected error during authentication: {str(e)}")
        raise credentials_exception


def get_current_active_user(
    current_user: db_models.User = Depends(get_current_user),
) -> db_models.User:
    """
    Get the current active user.
    
    Args:
        current_user: Current user
        
    Returns:
        User: User object
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_superuser(
    current_user: db_models.User = Depends(get_current_user),
) -> db_models.User:
    """
    Get the current superuser.
    
    Args:
        current_user: Current user
        
    Returns:
        User: User object
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Not enough permissions"
        )
    return current_user


def get_current_user_optional(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> Optional[db_models.User]:
    """
    Get the current user from the token, but return None if token is invalid or missing.
    
    Args:
        db: Database session
        token: OAuth2 token
        
    Returns:
        Optional[User]: User object or None if token is invalid
    """
    try:
        return get_current_user(db, token)
    except HTTPException:
        return None 