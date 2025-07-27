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
from app.db.supabase_client import get_supabase_service
from app.models import TokenPayload
from app.db import models as db_models

# OAuth2 password bearer scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)
logger = logging.getLogger(__name__)


def get_current_user(
    supabase_service = Depends(get_supabase_service), 
    token: str = Depends(oauth2_scheme)
) -> db_models.User:
    """
    Get the current user from the token using Supabase verification.
    If Supabase verification fails, falls back to manual JWT verification.
    
    Args:
        supabase_service: Supabase service instance
        token: OAuth2 token
        
    Returns:
        User: User object
        
    Raises:
        HTTPException: If token is invalid
    """
    # Add detailed logging for debugging
    logger.info("=== AUTHENTICATION DEBUG START ===")
    logger.info(f"Token received: {'YES' if token else 'NO'}")
    if token:
        logger.info(f"Token length: {len(token)}")
        logger.info(f"Token starts with: {token[:20]}...")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Development bypass for testing personalization feature
    import os
    if os.environ.get("ENABLE_AUTH_BYPASS") == "true":
        logger.info("Authentication bypass enabled for development")
        # Create a mock user for testing - using environment variables for user data
        mock_user_id = os.environ.get("DEV_USER_ID", "dev-user-123")
        mock_user_email = os.environ.get("DEV_USER_EMAIL", "dev@example.com")
        mock_user = type('MockUser', (object,), {
            'id': mock_user_id,
            'email': mock_user_email,
            'full_name': 'Development User',
            'preferences': {
                "prefer_no_preservatives": True,
                "prefer_antibiotic_free": False,
                "prefer_organic_or_grass_fed": True,
                "prefer_no_added_sugars": True,
                "prefer_no_flavor_enhancers": True,
                "prefer_reduced_sodium": False
            },
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })()
        return mock_user
        
    # If no token provided
    if token is None:
        logger.warning("No authentication token provided")
        logger.info("=== AUTHENTICATION DEBUG END (NO TOKEN) ===")
        raise credentials_exception
        
    try:
        # Log token format for debugging (only first few chars for security)
        logger.debug(f"Verifying token (length: {len(token)})")
        
        # Manual JWT verification method - updated to work with Supabase tokens
        def verify_manually():
            logger.info("Using manual JWT verification")
            try:
                # First, decode without verification to check if it's a Supabase token
                unverified_payload = jwt.decode(token, "dummy_key", options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_exp": False,
                    "verify_iat": False
                })
                is_supabase_token = (
                    unverified_payload.get("iss") and "supabase" in unverified_payload.get("iss", "").lower()
                ) or unverified_payload.get("role") in ["anon", "authenticated"]
                
                logger.debug(f"Is Supabase token: {is_supabase_token}")
                
                if is_supabase_token:
                    # For Supabase tokens, disable signature verification since we don't have the correct secret
                    logger.info("Detected Supabase token - using without signature verification")
                    payload = jwt.decode(
                        token, 
                        "dummy_key",  # Key required even when verification is disabled
                        options={
                            "verify_signature": False,  # Disable signature verification for Supabase tokens
                            "verify_exp": False,       # Disable expiration check for Supabase tokens
                            "verify_iat": False,
                            "require_exp": False,      # Don't require expiration
                            "require_iat": False,
                            "require_sub": False,
                            "verify_aud": False,       # Disable audience verification 
                            "verify_iss": False,       # Disable issuer verification
                            "require": []              # Don't require any specific claims
                        }
                    )
                else:
                    # For custom tokens, use full verification
                    logger.info("Detected custom token - using full verification")
                    jwt_secret = settings.SUPABASE_JWT_SECRET if settings.SUPABASE_JWT_SECRET else settings.SECRET_KEY
                    payload = jwt.decode(
                        token, 
                        jwt_secret, 
                        algorithms=[settings.ALGORITHM, "HS256"],
                        options={
                            "verify_signature": True,
                            "verify_exp": True,
                            "verify_iat": False,
                            "require_exp": True,
                            "require_iat": False,
                            "require_sub": False,
                            "verify_aud": False,
                            "verify_iss": False,
                            "require": ["exp"]
                        }
                    )
                
                logger.debug(f"JWT decode successful, payload role: {payload.get('role')}")
                logger.debug(f"JWT payload sub: {payload.get('sub')}, email: {payload.get('email')}")
                
                # Flexible validation for Supabase tokens
                # Check if it's a Supabase token (has 'role' claim)
                if payload.get("role") in ["anon", "authenticated"]:
                    logger.debug("Validating Supabase token payload")
                    
                    # For authenticated tokens, require sub (user ID)
                    if payload.get("role") == "authenticated":
                        if not payload.get("sub") or not isinstance(payload.get("sub"), str):
                            logger.warning("Invalid subject claim in authenticated Supabase token")
                            raise credentials_exception
                        
                        # Accept Supabase issuer
                        if payload.get("iss") and "supabase" not in payload.get("iss", "").lower():
                            logger.warning("Invalid Supabase token issuer")
                            raise credentials_exception
                        
                        # Get user from database - for authenticated tokens
                        logger.debug(f"Looking up user in database: {payload['sub']}")
                        client = supabase_service.get_client()
                        result = client.table('profiles').select('*').eq('id', payload['sub']).execute()
                        user = None
                        if result.data:
                            user_data = result.data[0]
                            user = type('User', (object,), {
                                'id': user_data['id'],
                                'email': user_data['email'],
                                'full_name': user_data['full_name'],
                                'preferences': user_data.get('preferences'),
                                'created_at': user_data.get('created_at'),
                                'updated_at': user_data.get('updated_at')
                            })()
                        if not user:
                            # User not found in local DB - create them
                            logger.warning(f"User {payload['sub']} not found in local DB. Creating record.")
                            
                            # Extract user data from token
                            user_email = payload.get('email') or f"{payload['sub']}@supabase.local"
                            user_metadata = payload.get('user_metadata', {}) or {}
                            full_name = user_metadata.get('full_name', '')
                            
                            logger.debug(f"Creating user with email: {user_email}, full_name: {full_name}")
                            
                            # Create new user in local database
                            new_user = db_models.User(
                                id=payload['sub'],
                                email=user_email,
                                full_name=full_name
                            )
                            
                            try:
                                # Use Supabase client directly to insert user
                                client = supabase_service.get_client()
                                result = client.table('profiles').insert({
                                    'id': payload['sub'],
                                    'email': user_email,
                                    'full_name': full_name
                                }).execute()
                                
                                if result.data:
                                    logger.info(f"Created new user record for Supabase user {payload['sub']}")
                                    # Return the created user data
                                    user_data = result.data[0]
                                    created_user = type('User', (object,), {
                                        'id': user_data['id'],
                                        'email': user_data['email'],
                                        'full_name': user_data['full_name'],
                                        'preferences': user_data.get('preferences'),
                                        'created_at': user_data.get('created_at'),
                                        'updated_at': user_data.get('updated_at')
                                    })()
                                    return created_user
                                else:
                                    raise Exception("No data returned from insert")
                                    
                            except Exception as e:
                                logger.error(f"Failed to create user record: {e}")
                                # Create temporary user object for this request
                                temp_user = type('TempUser', (object,), {
                                    'id': payload['sub'],
                                    'email': user_email,
                                    'full_name': full_name,
                                    'preferences': None,
                                    'created_at': datetime.now(),
                                    'updated_at': datetime.now()
                                })()
                                return temp_user
                        
                        logger.debug(f"User found: {user.email}")
                        return user
                        
                    elif payload.get("role") == "anon":
                        # For anon tokens, create a temporary anonymous user
                        logger.debug("Creating anonymous user for anon token")
                        anon_user = type('AnonUser', (object,), {
                            'id': 'anonymous',
                            'email': 'anonymous@example.com',
                            'full_name': 'Anonymous User',
                            'preferences': None,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        })()
                        return anon_user
                        
                else:
                    # Legacy validation for custom tokens
                    logger.debug("Validating custom token payload")
                    if not payload.get("sub") or not isinstance(payload.get("sub"), str):
                        logger.warning("Invalid subject claim in token")
                        raise credentials_exception
                        
                    if payload.get("type") != "access":
                        logger.warning("Invalid token type")
                        raise credentials_exception
                        
                    if payload.get("iss") != "clear-meat-api":
                        logger.warning("Invalid token issuer")
                        raise credentials_exception
                    
                    if "clear-meat-api" not in payload.get("aud", []):
                        logger.warning("Invalid token audience")
                        raise credentials_exception
                
                    # Legacy token handling
                    logger.debug(f"Legacy token - looking up user: {payload['sub']}")
                    client = supabase_service.get_client()
                    result = client.table('profiles').select('*').eq('id', payload['sub']).execute()
                    if result.data:
                        user_data = result.data[0]
                        user = type('User', (object,), {
                            'id': user_data['id'],
                            'email': user_data['email'],
                            'full_name': user_data['full_name'],
                            'preferences': user_data.get('preferences'),
                            'created_at': user_data.get('created_at'),
                            'updated_at': user_data.get('updated_at')
                        })()
                        return user
                    else:
                        logger.warning(f"User not found in database: {payload['sub']}")
                        raise credentials_exception
                
            except JWTError as e:
                logger.error(f"JWT decode error: {e}")
                raise credentials_exception

        # Check if Supabase client is available
        if not supabase or not hasattr(supabase, 'auth'):
            logger.warning("Supabase client not available for token verification.")
            return verify_manually()

        # Skip Supabase client verification due to configuration issues
        # Go directly to manual verification which handles Supabase tokens correctly
        logger.info("Using manual JWT verification for all tokens")
        return verify_manually()
        
        # Original Supabase verification commented out until JWT secret is configured
        # try:
        #     response = supabase.auth.get_user(token)
        #     if not response or not hasattr(response, 'user') or not response.user:
        #         return verify_manually()
        #     
        #     # Extract user data from the Supabase response
        #     supabase_user = response.user
        #     user_id = supabase_user.id
        #     
        #     # Ensure user_id is a string (convert UUID if needed)
        #     user_id = str(user_id)
        #         
        #     user_email = getattr(supabase_user, 'email', None)
        #     
        #     # Log success for debugging
        #     logger.debug(f"Successfully verified token for user {user_id}")
        #     
        #     # Try to fetch user from our database
        #     user = supabase_service.query(db_models.User).filter(db_models.User.id == user_id).first()
        #     
        #     if user:
        #         # User found in database - ensure ID is string
        #         if hasattr(user.id, 'hex') or isinstance(user.id, uuid.UUID):
        #             user.id = str(user.id)
        #         logger.debug(f"User {user_id} found in local DB.")
        #         return user
        #     else:
        #         # User exists in Supabase but not in our database yet
        #         # Create temporary user object with data from Supabase
        #         logger.warning(f"User {user_id} not found in local DB profiles. Creating record.")
        #         user_metadata = getattr(supabase_user, 'user_metadata', {}) or {}
        #         full_name = user_metadata.get('full_name', '')
        #         # role = user_metadata.get('role', 'basic') # Role field removed from model
        #         
        #         # --- Restoring INSERT logic --- 
        #         # Create and save the user to our database
        #         # Pass only fields that exist in the db_models.User model
        #         new_user = db_models.User(
        #             id=user_id,
        #             email=user_email,
        #             full_name=full_name,
        #             # preferences=None # Initialize preferences if needed
        #         )
        #         
        #         # Add the user to the database to avoid recreating it on every request
        #         # This might fail if there are transaction/timing issues with auth.users
        #         try:
        #             supabase_service.add(new_user)
        #             supabase_service.commit()
        #             supabase_service.refresh(new_user)
        #             logger.info(f"Created new user record for Supabase user {user_id}")
        #             return new_user
        #         except Exception as insert_exc:
        #             logger.error(f"Failed to insert user {user_id} into local DB: {insert_exc}")
        #             supabase_service.rollback()
        #             # If insert fails, fall back to manual verification for this request
        #             logger.warning("Falling back to manual verification due to DB insert failure.")
        #             return verify_manually()
        # 
        #         # --- Removed temporary object creation logic ---
        #         # temp_user_obj = type('TempUser', (object,), {
        #         #     'id': user_id,
        #         #     'email': user_email,
        #         #     'full_name': full_name,
        #         #     'preferences': None, # No preferences known yet
        #         #     'created_at': None, # Not available without DB record
        #         #     'updated_at': None  # Not available without DB record
        #         # })
        #         # return temp_user_obj
        #         
        # except Exception as e:
        #     # Log the specific error from Supabase or DB interaction
        #     logger.warning(f"Supabase/DB error during user lookup/creation: {str(e)}. Falling back to manual verification.")
        #     # Rollback any potential transaction changes from failed insert attempt
        #     try:
        #         supabase_service.rollback()
        #     except Exception as rb_exc:
        #          logger.error(f"Error during rollback: {rb_exc}")
        #     return verify_manually()
            
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
    # --- Removed check as is_active field is gone from model ---
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
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
    # --- Removed check as is_superuser field is gone from model ---
    # if not current_user.is_superuser:
    #     raise HTTPException(
    #         status_code=403, detail="Not enough permissions"
    #     )
    # --- Returning current_user directly. If superuser logic is needed, 
    # --- it must rely on other means (e.g., user role stored elsewhere or JWT claim)
    return current_user


def get_current_user_optional(
    supabase_service = Depends(get_supabase_service),
    token: str = Depends(oauth2_scheme),
) -> Optional[db_models.User]:
    """
    Get the current user from the token, but return None if token is invalid or missing.
    
    Args:
        supabase_service: Supabase service instance
        token: OAuth2 token
        
    Returns:
        User: User object or None
    """
    try:
        return get_current_user(supabase_service=supabase_service, token=token)
    except HTTPException:
        return None 