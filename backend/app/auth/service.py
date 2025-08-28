"""
Authentication service layer for user management and authentication operations.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.auth.schemas import UserCreate, UserUpdate, LoginRequest
from app.auth.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    is_password_strong
)
from core.config import settings


class AuthenticationError(Exception):
    """Authentication-related errors."""
    pass


class AuthService:
    """Service class for user authentication and management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, login_request: LoginRequest) -> Optional[User]:
        """
        Authenticate a user with username/email and password.
        
        Args:
            login_request: Login credentials
            
        Returns:
            User object if authentication successful, None otherwise
            
        Raises:
            AuthenticationError: If account is locked or other auth issues
        """
        # Find user by username or email
        result = await self.db.execute(
            select(User).where(
                (User.username == login_request.username) | 
                (User.email == login_request.username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Prevent username enumeration by taking similar time
            get_password_hash("dummy_password")
            return None
        
        # Check if account is locked
        if user.is_account_locked:
            raise AuthenticationError(
                "Account is temporarily locked due to multiple failed login attempts"
            )
        
        # Verify password
        if not verify_password(login_request.password, user.hashed_password):
            # Increment failed login attempts
            await self._handle_failed_login(user)
            return None
        
        # Reset failed login attempts on successful login
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.db.commit()
        
        return user
    
    async def _handle_failed_login(self, user: User) -> None:
        """Handle failed login attempt and potentially lock account."""
        user.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        await self.db.commit()
    
    async def create_user(self, user_create: UserCreate) -> User:
        """
        Create a new user account.
        
        Args:
            user_create: User creation data
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If user data is invalid
            IntegrityError: If username/email already exists
        """
        # Validate password strength
        is_strong, issues = is_password_strong(user_create.password)
        if not is_strong:
            raise ValueError(f"Password validation failed: {'; '.join(issues)}")
        
        # Hash password
        hashed_password = get_password_hash(user_create.password)
        
        # Create user object
        user = User(
            id=uuid.uuid4(),
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            role=user_create.role,
            license_number=user_create.license_number,
            certifications=user_create.certifications,
            password_changed_at=datetime.utcnow(),
        )
        
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError as e:
            await self.db.rollback()
            if "username" in str(e):
                raise ValueError("Username already exists")
            elif "email" in str(e):
                raise ValueError("Email address already exists")
            else:
                raise ValueError("User creation failed")
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: uuid.UUID, user_update: UserUpdate) -> Optional[User]:
        """
        Update user information.
        
        Args:
            user_id: User ID to update
            user_update: Update data
            
        Returns:
            Updated user object or None if not found
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Update fields if provided
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def change_password(
        self, 
        user: User, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """
        Change user password with current password verification.
        
        Args:
            user: User object
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            True if password changed successfully
            
        Raises:
            ValueError: If password validation fails
        """
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            return False
        
        # Validate new password strength
        is_strong, issues = is_password_strong(new_password)
        if not is_strong:
            raise ValueError(f"Password validation failed: {'; '.join(issues)}")
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.password_changed_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def create_access_token_for_user(self, user: User) -> dict:
        """
        Create access token for authenticated user.
        
        Args:
            user: Authenticated user object
            
        Returns:
            Token data including access token and expiration
        """
        # Create token data
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "email": user.email,
        }
        
        # Create access token
        access_token = create_access_token(data=token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            "user": user
        }
    
    async def deactivate_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Deactivate a user account (admin only)."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def unlock_user_account(self, user_id: uuid.UUID) -> Optional[User]:
        """Unlock a user account (admin only)."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        return user