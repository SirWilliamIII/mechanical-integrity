"""
Test configuration and fixtures for Mechanical Integrity system.
"""
import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Generator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add the project root to Python path so imports work correctly
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Import after path is set
try:
    from backend.app.main import app
    from backend.models.database import Base, get_db
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    app = None
    Base = None
    get_db = None

@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")
    
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator:
    """Create a test client with overridden database dependency."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("App imports not available")
    
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

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

# Helper functions for tests
def assert_response_success(response, expected_status: int = 200):
    """Assert API response is successful."""
    assert response.status_code == expected_status, \
        f"Expected status {expected_status} but got {response.status_code}. Response: {response.json() if hasattr(response, 'json') else response}"

def validate_equipment_safety(equipment_data: dict):
    """Validate equipment meets safety requirements."""
    assert float(equipment_data["design_pressure"]) > 0, "Design pressure must be positive"
    assert float(equipment_data["nominal_thickness"]) > 0, "Thickness must be positive"
    assert equipment_data["equipment_type"] in ["VESSEL", "TANK", "PIPING"], "Invalid equipment type"
    assert equipment_data["material_spec"], "Material specification required"

def validate_inspection_safety(inspection_data: dict):
    """Validate inspection meets safety requirements."""
    assert len(inspection_data["thickness_readings"]) > 0, "At least one thickness reading required"
    
    for reading in inspection_data["thickness_readings"]:
        assert float(reading["thickness"]) > 0, "Thickness readings must be positive"
        assert reading["location"], "Location required for each reading"
    
    assert inspection_data["inspection_type"] in ["EXTERNAL", "INTERNAL", "UT", "RT", "VT"], \
        "Invalid inspection type"
