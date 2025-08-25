"""
Database configuration and session management for mechanical integrity system.

Provides PostgreSQL connection and SQLAlchemy session management with
proper connection pooling for production deployment.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .base import Base

# ========================================================================
# DATABASE CONNECTION CONFIGURATION
# ========================================================================

# Get database URL from environment with fallback for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://will:t00r@localhost:5432/risk-assessment"
)

# Create engine with production-ready configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,                    # Number of connections to maintain
    max_overflow=20,                 # Additional connections when needed
    pool_pre_ping=True,              # Validate connections before use
    pool_recycle=3600,               # Recycle connections after 1 hour
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"  # SQL logging
)

# Configure session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ========================================================================
# SESSION MANAGEMENT
# ========================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    
    Provides database sessions with automatic cleanup.
    Used as a dependency in API endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> sessionmaker:
    """
    Get session factory for services that need to create their own sessions.
    
    Used by services that perform background tasks or need session isolation.
    Each service operation creates its own session to avoid connection conflicts.
    
    Returns:
        sessionmaker: Session factory configured for the database
    """
    return SessionLocal


def verify_db_connection() -> bool:
    """
    Verify database connection for health checks.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def create_tables():
    """
    Create all database tables.
    
    Should be called during application startup or via migration scripts.
    In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.
    
    WARNING: This will destroy all data!
    Only use in development/testing environments.
    """
    Base.metadata.drop_all(bind=engine)


# ========================================================================
# DATABASE EVENT LISTENERS
# ========================================================================

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Set PostgreSQL-specific connection parameters.
    
    This function is called for each new database connection.
    """
    # For PostgreSQL, we can set timezone and other session parameters
    with dbapi_connection.cursor() as cursor:
        # Set timezone to UTC for consistent timestamp handling
        cursor.execute("SET timezone TO 'UTC'")


# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

def get_db_info() -> dict:
    """
    Get database connection information for debugging.
    
    Returns:
        dict: Database connection details (without sensitive info)
    """
    url_parts = str(engine.url).split('@')
    if len(url_parts) > 1:
        host_db = url_parts[1]
    else:
        host_db = "localhost/mechanical_integrity"
    
    return {
        "database_type": engine.dialect.name,
        "host_database": host_db,
        "pool_size": engine.pool.size(),
        "checked_out_connections": engine.pool.checkedout(),
        "connection_count": engine.pool.size() - engine.pool.checkedin()
    }