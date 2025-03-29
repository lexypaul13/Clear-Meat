"""Common dependencies for the MeatWise API."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime

from app.core.config import settings
from app.core.supabase import supabase, admin_supabase
from app.db.session import get_db
from app.models import TokenPayload
from app.db import models as db_models

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
logger = logging.getLogger(__name__)


def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
) -> db_models.User:
    """
    Get the current user from the token using Supabase verification.
    
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
        
    try:
        # Check if Supabase client is available
        if not supabase or not hasattr(supabase, 'auth'):
            logger.error("Supabase client not available for token verification.")
            raise credentials_exception

        try:
            # Verify token directly with Supabase
            response = supabase.auth.get_user(token)
            
            if not response or not hasattr(response, 'user') or not response.user:
                logger.warning("Supabase token verification returned no user.")
                raise credentials_exception
            
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
            logger.error(f"Supabase token verification error: {str(e)}")
            raise credentials_exception
            
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


def get_current_active_admin(
    current_user: db_models.User = Depends(get_current_active_user),
) -> db_models.User:
    """
    Get the current active admin user.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: User object
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user 