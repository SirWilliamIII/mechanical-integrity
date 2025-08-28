"""
Authentication dependencies for FastAPI dependency injection.

Provides reusable authentication and authorization dependencies
for protecting API endpoints based on user roles.
"""
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.models import User, UserRole
from app.auth.schemas import TokenData
from app.auth.security import verify_token
from models.database import get_db

# Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        db: Database session
        token: Bearer token from Authorization header
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    # Verify the JWT token
    payload = verify_token(token.credentials)
    if payload is None:
        raise credentials_exception
    
    # Extract user information from token
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    # Check if account is locked
    if user.is_account_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked due to multiple failed login attempts"
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current user and ensure account is active and verified.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        Active user object
        
    Raises:
        HTTPException: If user is inactive or unverified
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    
    return current_user


async def require_role(required_role: UserRole):
    """
    Create a dependency that requires a specific user role.
    
    Args:
        required_role: Minimum role required for access
        
    Returns:
        Dependency function that checks user role
    """
    def role_dependency(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        """Check if user has required role."""
        
        # Define role hierarchy (higher roles include lower permissions)
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.INSPECTOR: 2,
            UserRole.ENGINEER: 3,
            UserRole.ADMIN: 4,
        }
        
        user_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 999)
        
        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        
        return current_user
    
    return role_dependency


# Commonly used role dependencies
require_admin = require_role(UserRole.ADMIN)
require_engineer = require_role(UserRole.ENGINEER) 
require_inspector = require_role(UserRole.INSPECTOR)
require_viewer = require_role(UserRole.VIEWER)


def require_calculation_permission():
    """
    Dependency for endpoints that perform API 579 calculations.
    Requires engineer-level permissions or above.
    """
    def calculation_dependency(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        """Check if user can perform safety-critical calculations."""
        
        if not current_user.can_calculate:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for safety-critical calculations. "
                       "Engineer role or above required."
            )
        
        return current_user
    
    return calculation_dependency


def require_inspection_permission():
    """
    Dependency for endpoints that handle inspection data.
    Requires inspector-level permissions or above.
    """
    def inspection_dependency(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        """Check if user can enter/modify inspection data."""
        
        if not current_user.can_inspect:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for inspection data. "
                       "Inspector role or above required."
            )
        
        return current_user
    
    return inspection_dependency


# Safety-critical calculation permission dependency
RequireCalculationPermission = Depends(require_calculation_permission())
RequireInspectionPermission = Depends(require_inspection_permission())

# Role-based dependencies
RequireAdmin = Depends(require_admin)
RequireEngineer = Depends(require_engineer)
RequireInspector = Depends(require_inspector)
RequireViewer = Depends(require_viewer)