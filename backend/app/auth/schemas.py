"""
Pydantic schemas for authentication and user management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.auth.models import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.VIEWER
    license_number: Optional[str] = Field(None, max_length=50)
    certifications: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating new users."""
    
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    license_number: Optional[str] = Field(None, max_length=50)
    certifications: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    """Schema for password updates."""
    
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class User(UserBase):
    """User schema for API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    password_changed_at: datetime
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserInDB(User):
    """User schema including hashed password for internal use."""
    
    hashed_password: str


# Authentication schemas
class Token(BaseModel):
    """JWT token response schema."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: User


class TokenData(BaseModel):
    """Token payload data for JWT validation."""
    
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    """Login response schema."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


# Password reset schemas
class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    
    email: EmailStr


class PasswordReset(BaseModel):
    """Password reset schema."""
    
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# Admin user management schemas
class UserList(BaseModel):
    """Schema for paginated user list."""
    
    users: list[User]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserStatusUpdate(BaseModel):
    """Schema for updating user status (admin only)."""
    
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    failed_login_attempts: Optional[int] = None
    locked_until: Optional[datetime] = None