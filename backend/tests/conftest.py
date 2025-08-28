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
        # Mock database dependency for tests that cannot connect to real DB
        # Note: Use proper test database fixtures for integration tests requiring DB
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine)
        return TestSession()
    
    app = None

@pytest.fixture
def sample_equipment_data():
    """Sample equipment data for testing."""
    return {
        "tag_number": "V-101",
        "name": "High Pressure Separator",  # API schema expects this
        "description": "High Pressure Separator", 
        "equipment_type": "VESSEL",  # Use validated enum value
        "design_pressure": "150.0",  # Realistic pressure
        "design_temperature": "650.0",
        "material_specification": "SA-516-70",
        "design_thickness": "1.250",
        "service_description": "Hydrocarbon separation service",
        "installation_date": "2010-01-15T00:00:00Z"
    }


@pytest.fixture  
def sample_inspection_data(sample_equipment):
    """Sample inspection data for safety-critical testing."""
    return {
        "equipment_id": str(sample_equipment.id),
        "inspection_date": "2024-08-15T10:00:00Z",
        "inspection_type": "UT",
        "inspector_name": "John Smith",
        "inspector_certification": "SNT-TC-1A-LEVEL-III",
        "report_number": "UT-2024-001",
        "thickness_readings": [
            {
                "cml_number": "CML-1", 
                "location_description": "North quadrant - shell", 
                "thickness_measured": "1.245",
                "design_thickness": "1.250"
            },
            {
                "cml_number": "CML-2", 
                "location_description": "East quadrant - shell",
                "thickness_measured": "1.238",
                "design_thickness": "1.250"
            },
            {
                "cml_number": "CML-3",
                "location_description": "South quadrant - shell", 
                "thickness_measured": "1.242",
                "design_thickness": "1.250"
            },
            {
                "cml_number": "CML-4",
                "location_description": "West quadrant - shell",
                "thickness_measured": "1.240", 
                "design_thickness": "1.250"
            }
        ],
        "corrosion_type": "UNIFORM",
        "notes": "Routine ultrasonic thickness survey - all readings within acceptable limits"
    }


@pytest.fixture
def sample_equipment(test_db):
    """Create sample equipment in database for testing."""
    from models.equipment import Equipment, EquipmentType
    
    equipment = Equipment(
        tag_number="V-101",
        description="Test High Pressure Separator",
        equipment_type=EquipmentType.PRESSURE_VESSEL,
        design_pressure=Decimal("150.0"),  # Use realistic pressure 
        design_temperature=Decimal("650.0"),
        design_thickness=Decimal("1.250"),
        material_specification="SA-516-70",
        service_description="Hydrocarbon separation service",
        installation_date=datetime(2010, 1, 15)
    )
    
    # Add to database
    test_db.add(equipment)
    test_db.commit()
    test_db.refresh(equipment)
    
    return equipment


@pytest.fixture
def sample_inspection(test_db, sample_equipment):
    """Create sample inspection record in database."""
    from models.inspection import InspectionRecord, InspectionType
    import uuid
    
    thickness_data = [
        {"location": "CML-1", "thickness_measured": "1.245"},
        {"location": "CML-2", "thickness_measured": "1.238"},
        {"location": "CML-3", "thickness_measured": "1.242"},
        {"location": "CML-4", "thickness_measured": "1.240"}
    ]
    
    inspection = InspectionRecord(
        id=str(uuid.uuid4()),
        equipment_id=sample_equipment.id,
        inspection_date=datetime(2024, 8, 15, 10, 0, 0),
        inspection_type=InspectionType.UT,
        inspector_name="John Smith",
        inspector_certification="SNT-TC-1A Level III", 
        report_number="UT-2024-001",
        thickness_readings=thickness_data,
        min_thickness_found=Decimal("1.238"),
        avg_thickness=Decimal("1.241"),
        confidence_level=Decimal("95.0"),  # Statistical confidence level required for all inspections
        verified_by=None,  # Not yet verified
        verified_at=None
    )
    
    test_db.add(inspection)
    test_db.commit() 
    test_db.refresh(inspection)
    
    return inspection


@pytest.fixture
def multiple_inspections(test_db, sample_equipment):
    """Create multiple inspection records for trend analysis."""
    from models.inspection import InspectionRecord, InspectionType
    from datetime import timedelta
    import uuid
    
    inspections = []
    base_date = datetime(2024, 1, 15)
    
    # Create 3 inspections over time showing gradual thinning
    thicknesses = [
        {"readings": [1.250, 1.245, 1.248, 1.246], "min": 1.245, "avg": 1.247},
        {"readings": [1.248, 1.242, 1.245, 1.243], "min": 1.242, "avg": 1.245},
        {"readings": [1.245, 1.238, 1.242, 1.240], "min": 1.238, "avg": 1.241}
    ]
    
    for i, thickness_set in enumerate(thicknesses):
        thickness_data = [
            {"location": f"CML-{j+1}", "thickness_measured": str(thickness)}
            for j, thickness in enumerate(thickness_set["readings"])
        ]
        
        inspection = InspectionRecord(
            id=str(uuid.uuid4()),
            equipment_id=sample_equipment.id,
            inspection_date=base_date + timedelta(days=i*180),  # 6 months apart
            inspection_type=InspectionType.UT,
            inspector_name="John Smith",
            inspector_certification="SNT-TC-1A Level III",
            report_number=f"UT-2024-{i+1:03d}",
            thickness_readings=thickness_data,
            min_thickness_found=Decimal(str(thickness_set["min"])),
            avg_thickness=Decimal(str(thickness_set["avg"])),
            confidence_level=Decimal("95.0"),  # Statistical confidence level for trend analysis
            verified_by="Jane Smith" if i < 2 else None,
            verified_at=datetime(2024, 8, 20) if i < 2 else None
        )
        
        test_db.add(inspection)
        inspections.append(inspection)
    
    test_db.commit()
    
    for inspection in inspections:
        test_db.refresh(inspection)
    
    return inspections

def assert_decimal_equal(actual: Decimal, expected: Decimal, precision: int = 3):
    """Assert decimal values are equal within precision."""
    assert round(actual, precision) == round(expected, precision)

# Test database transaction rollback fixture
@pytest.fixture
def db_transaction():
    """Provide database session with transaction rollback for test isolation."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    connection = engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


def assert_response_success(response, expected_status: int = 200):
    """
    Assert HTTP response is successful for safety-critical API endpoints.
    
    For safety-critical mechanical integrity systems, this function:
    - Validates HTTP status code matches expected value
    - Ensures response can be parsed as JSON
    - Returns parsed JSON data for further validation
    
    Args:
        response: HTTP response object from test client
        expected_status: Expected HTTP status code (default: 200)
    
    Returns:
        dict: Parsed JSON response data
        
    Raises:
        AssertionError: If status code doesn't match or JSON parsing fails
    """
    assert response.status_code == expected_status, (
        f"Expected status {expected_status}, got {response.status_code}. "
        f"Response: {response.text}"
    )
    
    try:
        data = response.json()
    except Exception as e:
        raise AssertionError(f"Failed to parse response JSON: {e}. Response: {response.text}")
    
    return data


def validate_inspection_safety(inspection_data: dict):
    """
    Validate inspection data meets safety-critical requirements.
    
    For API 579 compliance and mechanical integrity, this function verifies:
    - Required fields are present and valid
    - Thickness measurements are within acceptable ranges
    - Safety-critical calculations are reasonable
    - Data integrity for audit trail compliance
    
    Args:
        inspection_data: Dictionary containing inspection response data
        
    Raises:
        AssertionError: If safety requirements are not met
    """
    # Verify required safety-critical fields
    required_fields = [
        "id", "equipment_id", "inspection_type", "inspector_name", 
        "min_thickness_found", "avg_thickness"
    ]
    
    for field in required_fields:
        assert field in inspection_data, f"Missing required safety field: {field}"
        assert inspection_data[field] is not None, f"Safety field cannot be None: {field}"
    
    # Validate thickness measurements for safety compliance
    min_thickness = Decimal(str(inspection_data["min_thickness_found"]))
    avg_thickness = Decimal(str(inspection_data["avg_thickness"]))
    
    # Safety checks for thickness values
    assert min_thickness > Decimal('0'), "Minimum thickness must be positive"
    assert avg_thickness > Decimal('0'), "Average thickness must be positive"
    assert min_thickness <= avg_thickness, "Minimum thickness cannot exceed average"
    
    # Reasonable bounds for typical pressure vessel applications (inches)
    assert min_thickness >= Decimal('0.001'), "Thickness below practical measurement limit"
    assert min_thickness <= Decimal('10.0'), "Thickness exceeds typical vessel range"
    assert avg_thickness <= Decimal('10.0'), "Average thickness exceeds typical range"
    
    # Validate inspector certification if present
    if "inspector_certification" in inspection_data:
        cert = inspection_data["inspector_certification"]
        if cert:
            assert isinstance(cert, str), "Inspector certification must be string"
            assert len(cert) > 0, "Inspector certification cannot be empty"
    
    # Validate thickness readings array if present
    if "thickness_readings" in inspection_data:
        readings = inspection_data["thickness_readings"]
        assert isinstance(readings, list), "Thickness readings must be list"
        assert len(readings) > 0, "Must have at least one thickness reading"
        
        for reading in readings:
            if isinstance(reading, dict) and "thickness_measured" in reading:
                thickness = Decimal(str(reading["thickness_measured"]))
                assert thickness > Decimal('0'), f"Invalid thickness reading: {thickness}"


def validate_equipment_safety(equipment_data: dict):
    """
    Validate equipment data meets safety-critical requirements.
    
    For API 579 compliance and pressure vessel safety, this function verifies:
    - Required fields are present and valid  
    - Design parameters are within safe operating ranges
    - Material specifications are proper
    - Data integrity for regulatory compliance
    
    Args:
        equipment_data: Dictionary containing equipment data
        
    Raises:
        AssertionError: If safety requirements are not met
    """
    # Verify required safety-critical fields
    required_fields = [
        "tag_number", "name", "equipment_type", "design_pressure", 
        "design_temperature", "material_specification", "design_thickness"
    ]
    
    for field in required_fields:
        assert field in equipment_data, f"Missing required safety field: {field}"
        assert equipment_data[field] is not None, f"Safety field cannot be None: {field}"
        
        # Ensure string fields are not empty
        if isinstance(equipment_data[field], str):
            assert len(equipment_data[field].strip()) > 0, f"Safety field cannot be empty: {field}"
    
    # Validate design pressure ranges (PSI) for safety
    design_pressure = Decimal(str(equipment_data["design_pressure"]))
    assert design_pressure > Decimal('0'), "Design pressure must be positive"
    assert design_pressure <= Decimal('15000'), "Design pressure exceeds typical safe limits (15,000 PSI)"
    
    # Validate design temperature ranges (°F)
    design_temp = Decimal(str(equipment_data["design_temperature"]))
    assert design_temp >= Decimal('-50'), "Design temperature below typical safe limits"
    assert design_temp <= Decimal('1500'), "Design temperature exceeds typical safe limits (1500°F)"
    
    # Validate thickness measurements (inches)
    design_thickness = Decimal(str(equipment_data["design_thickness"]))
    assert design_thickness > Decimal('0'), "Design thickness must be positive"
    assert design_thickness >= Decimal('0.001'), "Thickness below practical measurement limit"
    assert design_thickness <= Decimal('10.0'), "Thickness exceeds typical vessel range"
    
    # Validate equipment tag format
    tag = equipment_data["tag_number"].strip()
    assert len(tag) >= 2, "Equipment tag must be at least 2 characters"
    assert len(tag) <= 20, "Equipment tag exceeds maximum length (20 characters)"
    
    # Validate material specification format
    material_spec = equipment_data["material_specification"].strip()
    assert len(material_spec) >= 5, "Material specification too short"
    assert len(material_spec) <= 50, "Material specification too long"
    
    # Check for proper equipment type
    valid_types = ["VESSEL", "TANK", "PIPING", "HEAT_EXCHANGER", "pressure_vessel", "storage_tank", "piping", "heat_exchanger"]
    equipment_type = equipment_data["equipment_type"]
    assert equipment_type in valid_types, f"Invalid equipment type: {equipment_type}"
    
    # Optional diameter validation if present
    if "diameter" in equipment_data and equipment_data["diameter"] is not None:
        diameter = Decimal(str(equipment_data["diameter"]))
        assert diameter > Decimal('0'), "Diameter must be positive"
        assert diameter <= Decimal('500'), "Diameter exceeds typical vessel range (500 inches)"

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
            pass  # Don't close the session between requests
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_ollama_response():
    """Mock AI extraction response for document processing tests."""
    from app.services.document_analyzer import InspectionData, ThicknessMeasurement
    
    return InspectionData(
        equipment_tag="V-101",
        inspection_date="2024-08-15T10:00:00Z",
        thickness_measurements=[
            ThicknessMeasurement(location="CML-N", thickness=1.245, measurement_method="UT"),
            ThicknessMeasurement(location="CML-E", thickness=1.238, measurement_method="UT"),  # This is the minimum
            ThicknessMeasurement(location="CML-S", thickness=1.242, measurement_method="UT")
        ],
        corrosion_rates=[0.003, 0.004, 0.0035],
        recommendations=["Continue monitoring", "Schedule re-inspection in 2 years"],
        confidence_score=85.0  # This maps to ai_confidence_score in the API response
    )
