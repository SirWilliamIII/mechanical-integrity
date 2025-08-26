"""Base model with common fields"""
from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.types import TypeDecorator, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
import uuid


class Base(DeclarativeBase):
    """Base model class with common fields"""
    pass


class GUID(TypeDecorator):
    """
    Platform-independent GUID type for gradual UUID migration.
    
    Handles both string and UUID inputs/outputs, allowing for gradual
    migration from VARCHAR to native UUID types.
    """
    impl = String
    cache_ok = True

    def __init__(self):
        # Use String(36) to match existing database schema
        super().__init__(String(36))

    def process_bind_param(self, value, dialect):
        """Convert UUID objects to strings for database storage."""
        if value is None:
            return value
        elif isinstance(value, uuid.UUID):
            return str(value)
        elif isinstance(value, str):
            # Validate it's a proper UUID format
            try:
                uuid.UUID(value)
                return value
            except (TypeError, ValueError):
                raise ValueError(f"Invalid UUID format: {value}")
        else:
            raise TypeError(f"Expected UUID or string, got {type(value)}")

    def process_result_value(self, value, dialect):
        """Convert strings from database to UUID objects for Python."""
        if value is None:
            return value
        elif isinstance(value, str):
            return uuid.UUID(value)
        else:
            return value  # Already a UUID object


class TimestampMixin:
    """Mixin for created/updated timestamps"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class UUIDMixin:
    """Mixin for UUID primary key"""
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4
    )


class BaseModel(Base, TimestampMixin, UUIDMixin):
    """
    Base model class combining common functionality.
    
    Provides UUID primary key, timestamp fields, and common database patterns
    for all application models.
    """
    __abstract__ = True
