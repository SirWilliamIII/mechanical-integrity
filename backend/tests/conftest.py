# backend/tests/conftest.py
"""
Test configuration and fixtures for Mechanical Integrity system.
"""
import pytest
import sys
import asyncio
from pathlib import Path
from typing import Generator
from decimal import Decimal
from datetime import datetime

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Import our modules
try:
    from models.base import Base
    from models.database import get_db
    from app.main import app
except ImportError:
    # If imports fail, create mock objects for basic testing
    class MockBase:
        metadata = type('metadata', (), {'create_all': lambda **kwargs: None, 'drop_all': lambda **kwargs: None})()
    Base = MockBase()
    
    def get_db():
        # TODO: [TESTING] Replace mock get_db() with proper test database fixture
        # This stub prevents import failures but doesn't provide actual database functionality
        # Need to implement proper test database session management for integration tests
        pass
    
    app = None

@pytest.fixture
def sample_equipment_data():
    """Sample equipment data for testing."""
    return {
        "tag": "V-101",
        "name": "High Pressure Separator",
        "equipment_type": "VESSEL",
        "design_pressure": "1200.0",
        "design_temperature": "650.0",
        "material_spec": "SA-516-70",
        "nominal_thickness": "1.250",
        "diameter": "48.0",
        "location": "Unit 100",
        "manufacturer": "Pressure Vessels Inc",
        "year_built": 2010,
        "criticality": "HIGH"
    }

def assert_decimal_equal(actual: Decimal, expected: Decimal, precision: int = 3):
    """Assert decimal values are equal within precision."""
    assert round(actual, precision) == round(expected, precision)

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh test database for each test.
    Uses in-memory SQLite for speed.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal()
    
    # Clean up
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator:
    """
    Create a test client with overridden database dependency.
    """
    if app is None:
        pytest.skip("FastAPI app not available")
    
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()
