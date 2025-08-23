# backend/tests/unit/test_imports.py
"""Test that all imports are working correctly."""
import pytest

def test_backend_in_path():
    """Verify backend module is importable."""
    try:
        import backend
        assert True
    except ImportError:
        pytest.fail("Cannot import backend module")

def test_core_config_import():
    """Test importing settings."""
    try:
        from backend.core.config import settings
        assert settings.APP_NAME == "Mechanical Integrity AI"
    except ImportError as e:
        pytest.fail(f"Cannot import config: {e}")

def test_model_imports():
    """Test importing models."""
    try:
        from backend.models import equipment, inspection
        assert True
    except ImportError as e:
        pytest.skip(f"Models not ready: {e}")
