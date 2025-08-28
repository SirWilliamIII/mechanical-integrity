"""
Authentication models for user management and role-based access control.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from models.base import Base


class UserRole(str, Enum):
    """User roles for role-based access control in mechanical integrity system."""
    
    ADMIN = "admin"              # Full system access, user management
    ENGINEER = "engineer"        # API 579 calculations, equipment management
    INSPECTOR = "inspector"      # Inspection data entry, basic calculations
    VIEWER = "viewer"           # Read-only access to reports and data


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    
    # Authentication fields
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # User profile
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(20), nullable=False, default=UserRole.VIEWER)
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Safety-critical audit fields
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Professional credentials for audit compliance
    license_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    certifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON field for certifications
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<User(username='{self.username}', role='{self.role}')>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_engineer(self) -> bool:
        """Check if user has engineer privileges (can perform calculations)."""
        return self.role in (UserRole.ADMIN, UserRole.ENGINEER)
    
    @property
    def can_calculate(self) -> bool:
        """Check if user can perform API 579 calculations."""
        return self.role in (UserRole.ADMIN, UserRole.ENGINEER)
    
    @property
    def can_inspect(self) -> bool:
        """Check if user can enter inspection data."""
        return self.role in (UserRole.ADMIN, UserRole.ENGINEER, UserRole.INSPECTOR)
    
    @property
    def is_account_locked(self) -> bool:
        """Check if account is currently locked due to failed login attempts."""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until