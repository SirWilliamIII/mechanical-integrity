"""Simple tests to verify setup is working."""
import pytest

def test_pytest_works():
    """Verify pytest is running."""
    assert True

def test_imports_work():
    """Verify we can import our modules."""
    try:
        from backend.core.config import settings
        assert settings.PROJECT_NAME == "Mechanical Integrity AI"
        print(f"✅ Successfully loaded settings: {settings.PROJECT_NAME}")
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_decimal_calculations():
    """Test decimal precision for safety-critical calculations."""
    from decimal import Decimal
    
    # Test thickness calculation precision
    nominal = Decimal("1.250")
    measured = Decimal("1.245")
    loss = nominal - measured
    
    assert loss == Decimal("0.005")
    assert str(loss) == "0.005"  # Verify string representation

def test_sample_fixture(sample_equipment_data):
    """Test that fixtures are working."""
    assert sample_equipment_data["tag_number"] == "V-101"
    assert sample_equipment_data["equipment_type"] == "VESSEL"
    assert float(sample_equipment_data["design_pressure"]) == 150.0

class TestSafetyValidations:
    """Test safety validation helpers."""
    
    def test_validate_equipment_safety(self, sample_equipment_data):
        """Test equipment safety validation."""
        from backend.tests.conftest import validate_equipment_safety
        
        # Should pass validation
        validate_equipment_safety(sample_equipment_data)
        
        # Test negative pressure rejection
        bad_data = sample_equipment_data.copy()
        bad_data["design_pressure"] = "-100"
        
        with pytest.raises(AssertionError, match="must be positive"):
            validate_equipment_safety(bad_data)
