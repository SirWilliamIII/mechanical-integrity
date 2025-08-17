"""
Unit tests for Equipment API endpoints.
Tests CRUD operations and safety validations.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from backend.tests.conftest import (
    assert_response_success, 
    validate_equipment_safety,
    assert_decimal_equal
)


class TestEquipmentAPI:
    """Test suite for equipment endpoints."""
    
    def test_create_equipment_success(self, client, sample_equipment_data):
        """Test successful equipment creation."""
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert_response_success(response, 201)
        data = response.json()
        
        # Verify response
        assert data["tag"] == sample_equipment_data["tag"]
        assert data["name"] == sample_equipment_data["name"]
        assert data["equipment_type"] == sample_equipment_data["equipment_type"]
        assert float(data["design_pressure"]) == float(sample_equipment_data["design_pressure"])
        assert "id" in data
        assert "created_at" in data
        
        # Validate safety requirements
        validate_equipment_safety(data)
    
    def test_create_equipment_duplicate_tag(self, client, sample_equipment):
        """Test that duplicate equipment tags are rejected."""
        duplicate_data = {
            "tag": sample_equipment.tag,  # Same tag
            "name": "Duplicate Equipment",
            "equipment_type": "VESSEL",
            "design_pressure": "1000.0",
            "design_temperature": "500.0",
            "material_spec": "SA-516-70",
            "nominal_thickness": "1.0"
        }
        
        response = client.post(
            "/api/v1/equipment/",
            json=duplicate_data
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_create_equipment_invalid_pressure(self, client, sample_equipment_data):
        """Test that negative pressure is rejected."""
        sample_equipment_data["design_pressure"] = "-100.0"
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_equipment_by_id(self, client, sample_equipment):
        """Test retrieving equipment by ID."""
        response = client.get(f"/api/v1/equipment/{sample_equipment.id}")
        
        assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_equipment.id)
        assert data["tag"] == sample_equipment.tag
        assert data["name"] == sample_equipment.name
