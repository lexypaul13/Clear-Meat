"""Permissions module for granular RBAC in the MeatWise API."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from app.db.supabase_client import get_supabase_service
from app.internal.dependencies import get_current_user
from app.db import models as db_models


class UserRole(str, Enum):
    """User roles for permission checks."""
    
    BASIC = "basic"          # Regular user
    CONTRIBUTOR = "contributor"  # Can contribute data
    MODERATOR = "moderator"  # Can moderate content
    ADMIN = "admin"          # Full admin access


class Permission(str, Enum):
    """Permissions for actions in the system."""
    
    # User management
    MANAGE_USERS = "manage_users"
    VIEW_ALL_USERS = "view_all_users"
    
    # Products
    CREATE_PRODUCT = "create_product"
    EDIT_PRODUCT = "edit_product"
    DELETE_PRODUCT = "delete_product"
    VERIFY_PRODUCT = "verify_product"
    
    # Ingredients
    CREATE_INGREDIENT = "create_ingredient"
    EDIT_INGREDIENT = "edit_ingredient"
    DELETE_INGREDIENT = "delete_ingredient"
    
    # Reports
    MANAGE_REPORTS = "manage_reports"
    

# Role-Permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.BASIC: set(),  # Basic users have no special permissions
    
    UserRole.CONTRIBUTOR: {
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.CREATE_INGREDIENT,
        Permission.EDIT_INGREDIENT,
    },
    
    UserRole.MODERATOR: {
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.VERIFY_PRODUCT,
        Permission.CREATE_INGREDIENT,
        Permission.EDIT_INGREDIENT,
        Permission.MANAGE_REPORTS,
    },
    
    UserRole.ADMIN: {
        Permission.MANAGE_USERS,
        Permission.VIEW_ALL_USERS,
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.DELETE_PRODUCT,
        Permission.VERIFY_PRODUCT,
        Permission.CREATE_INGREDIENT,
        Permission.EDIT_INGREDIENT,
        Permission.DELETE_INGREDIENT,
        Permission.MANAGE_REPORTS,
    }
}


def get_user_role(user: db_models.User) -> UserRole:
    """
    Get the role of a user.
    
    Args:
        user: User object
        
    Returns:
        UserRole: The role of the user
    """
    # Superuser check is a fallback - should use the role field first
    if hasattr(user, 'role') and user.role:
        try:
            return UserRole(user.role)
        except ValueError:
            # If the role is not valid, fall back to basic or admin
            pass
    
    # Fall back to superuser check if role not found or invalid
    if user.is_superuser:
        return UserRole.ADMIN
    
    # Default case: basic user
    return UserRole.BASIC


def has_permission(permission: Permission):
    """
    Dependency to check if a user has a specific permission.
    
    Args:
        permission: The permission to check
        
    Returns:
        Callable: A dependency function that checks the permission
    """
    
    async def check_permission(
        current_user: db_models.User = Depends(get_current_user),
        supabase_service = Depends(get_supabase_service)
    ) -> db_models.User:
        """Check if the current user has the required permission."""
        user_role = get_user_role(current_user)
        
        # Superusers bypass permission checks
        if current_user.is_superuser:
            return current_user
            
        # Check if the user's role has the required permission
        if permission in ROLE_PERMISSIONS.get(user_role, set()):
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions: {permission} required"
        )
        
    return check_permission


def has_role(role: UserRole):
    """
    Dependency to check if a user has a specific role or higher.
    
    Args:
        role: The minimum role required
        
    Returns:
        Callable: A dependency function that checks the role
    """
    
    async def check_role(
        current_user: db_models.User = Depends(get_current_user)
    ) -> db_models.User:
        """Check if the current user has the required role or higher."""
        user_role = get_user_role(current_user)
        
        # Role hierarchy for comparison
        role_hierarchy = {
            UserRole.BASIC: 0,
            UserRole.CONTRIBUTOR: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3
        }
        
        # Check if user's role is sufficient
        if role_hierarchy.get(user_role, 0) >= role_hierarchy.get(role, 0):
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {role} or higher required"
        )
        
    return check_role 