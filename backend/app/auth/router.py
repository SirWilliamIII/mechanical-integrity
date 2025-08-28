"""
Authentication API router for user management and JWT authentication.
"""
from typing import Annotated, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_active_user,
    RequireAdmin,
    RequireEngineer,
)
from app.auth.models import User
from app.auth.schemas import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    LoginRequest,
    LoginResponse,
    Token,
)
from app.auth.service import AuthService, AuthenticationError
from models.database import get_db

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Authenticate user and return JWT access token.
    
    Returns:
        JWT access token with user information
        
    Raises:
        HTTPException: If authentication fails
    """
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.authenticate_user(login_request)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        # Create access token
        token_data = await auth_service.create_access_token_for_user(user)
        
        return LoginResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=UserSchema.model_validate(user)
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(e)
        )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Get current user information."""
    return UserSchema.model_validate(current_user)


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Update current user's profile information."""
    auth_service = AuthService(db)
    
    # Remove sensitive fields that users can't update themselves
    update_data = user_update.model_copy()
    update_data.role = None  # Users can't change their own role
    update_data.is_active = None  # Users can't deactivate themselves
    update_data.is_verified = None  # Users can't verify themselves
    
    updated_user = await auth_service.update_user(current_user.id, update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserSchema.model_validate(updated_user)


@router.put("/me/password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Change current user's password."""
    auth_service = AuthService(db)
    
    try:
        success = await auth_service.change_password(
            current_user,
            password_update.current_password,
            password_update.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return {"message": "Password changed successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Admin endpoints for user management
@router.post("/users", response_model=UserSchema, dependencies=[RequireAdmin])
async def create_user(
    user_create: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Create a new user (admin only)."""
    auth_service = AuthService(db)
    
    try:
        user = await auth_service.create_user(user_create)
        return UserSchema.model_validate(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users/{user_id}", response_model=UserSchema, dependencies=[RequireAdmin])
async def get_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Get user by ID (admin only)."""
    auth_service = AuthService(db)
    
    user = await auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserSchema.model_validate(user)


@router.put("/users/{user_id}", response_model=UserSchema, dependencies=[RequireAdmin])
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Update user (admin only)."""
    auth_service = AuthService(db)
    
    updated_user = await auth_service.update_user(user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserSchema.model_validate(updated_user)


@router.delete("/users/{user_id}", dependencies=[RequireAdmin])
async def deactivate_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Deactivate user account (admin only)."""
    auth_service = AuthService(db)
    
    user = await auth_service.deactivate_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}


@router.post("/users/{user_id}/unlock", dependencies=[RequireAdmin])
async def unlock_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Unlock user account (admin only)."""
    auth_service = AuthService(db)
    
    user = await auth_service.unlock_user_account(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User account unlocked successfully"}


# Engineer-only endpoint example
@router.get("/engineer-info", dependencies=[RequireEngineer])
async def get_engineer_info():
    """Example endpoint requiring engineer-level permissions."""
    return {
        "message": "This endpoint requires engineer-level permissions",
        "api_579_access": True,
        "calculation_permissions": True
    }