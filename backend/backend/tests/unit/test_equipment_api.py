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
    
    def test_create_equipment_invalid_type(self, client, sample_equipment_data):
        """Test that invalid equipment type is rejected."""
        sample_equipment_data["equipment_type"] = "INVALID"
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert response.status_code == 422
    
    def test_get_equipment_by_id(self, client, sample_equipment):
        """Test retrieving equipment by ID."""
        response = client.get(f"/api/v1/equipment/{sample_equipment.id}")
        
        assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_equipment.id)
        assert data["tag"] == sample_equipment.tag
        assert data["name"] == sample_equipment.name
    
    def test_get_equipment_by_tag(self, client, sample_equipment):
        """Test retrieving equipment by tag."""
        response = client.get(f"/api/v1/equipment/tag/{sample_equipment.tag}")
        
        assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_equipment.id)
        assert data["tag"] == sample_equipment.tag
    
    def test_get_equipment_not_found(self, client):
        """Test 404 for non-existent equipment."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/equipment/{fake_id}")
        
        assert response.status_code == 404
    
    def test_list_equipment(self, client, test_db, sample_equipment_data):
        """Test listing equipment with filters."""
        # Create multiple equipment items
        equipment_items = []
        for i, criticality in enumerate(["HIGH", "MEDIUM", "LOW"]):
            data = sample_equipment_data.copy()
            data["tag"] = f"V-10{i+1}"
            data["criticality"] = criticality
            
            response = client.post("/api/v1/equipment/", json=data)
            assert_response_success(response, 201)
            equipment_items.append(response.json())
        
        # Test listing all
        response = client.get("/api/v1/equipment/")
        assert_response_success(response)
        data = response.json()
        assert len(data) >= 3
        
        # Test filter by criticality
        response = client.get("/api/v1/equipment/?criticality=HIGH")
        assert_response_success(response)
        data = response.json()
        assert all(item["criticality"] == "HIGH" for item in data)
    
    def test_equipment_with_overdue_inspection(self, client, sample_equipment, test_db):
        """Test filtering equipment with overdue inspections."""
        # Set inspection due date in the past
        sample_equipment.next_inspection_due = datetime.utcnow() - timedelta(days=30)
        test_db.commit()
        
        response = client.get("/api/v1/equipment/?overdue_only=true")
        assert_response_success(response)
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["id"] == str(sample_equipment.id)
        assert data[0]["inspection_overdue"] is True
        assert data[0]["days_until_inspection"] < 0
    
    def test_update_equipment(self, client, sample_equipment):
        """Test updating equipment details."""
        update_data = {
            "location": "Unit 200 - Relocated",
            "operating_pressure": "1100.0",
            "operating_temperature": "625.0"
        }
        
        response = client.patch(
            f"/api/v1/equipment/{sample_equipment.id}",
            json=update_data
        )
        
        assert_response_success(response)
        data = response.json()
        
        assert data["location"] == update_data["location"]
        assert float(data["operating_pressure"]) == float(update_data["operating_pressure"])
        
        # Verify design parameters unchanged (safety feature)
        assert float(data["design_pressure"]) == float(sample_equipment.design_pressure)
    
    def test_equipment_inspection_status(self, client, sample_equipment, test_db):
        """Test equipment inspection status endpoint."""
        # Set up inspection data
        sample_equipment.last_inspection_date = datetime.utcnow() - timedelta(days=365)
        sample_equipment.next_inspection_due = datetime.utcnow() + timedelta(days=30)
        test_db.commit()
        
        response = client.get(f"/api/v1/equipment/{sample_equipment.id}/inspection-status")
        assert_response_success(response)
        data = response.json()
        
        assert data["equipment_tag"] == sample_equipment.tag
        assert data["criticality"] == sample_equipment.criticality
        assert data["compliance_status"] == "COMPLIANT"
        assert data["days_overdue"] == 0
        assert data["max_interval_years"] == 10  # API 510 for vessels
    
    def test_high_pressure_warning(self, client, sample_equipment_data):
        """Test high pressure equipment warning."""
        sample_equipment_data["design_pressure"] = "5500.0"  # Above 5000 psi
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert_response_success(response, 201)
        # In real implementation, this would trigger a warning log


class TestEquipmentSafetyValidations:
    """Test safety-critical validations."""
    
    def test_thickness_validation(self, client, sample_equipment_data):
        """Test thickness must be positive."""
        sample_equipment_data["nominal_thickness"] = "0.0"
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert response.status_code == 422
    
    def test_material_spec_required(self, client, sample_equipment_data):
        """Test material specification is required."""
        sample_equipment_data["material_spec"] = ""
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert response.status_code == 422
    
    def test_year_built_validation(self, client, sample_equipment_data):
        """Test year built must be reasonable."""
        sample_equipment_data["year_built"] = 2050  # Future year
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert response.status_code == 422
    
    def test_temperature_range_validation(self, client, sample_equipment_data):
        """Test temperature must be within material limits."""
        sample_equipment_data["design_temperature"] = "2000.0"  # Too high
        
        response = client.post(
            "/api/v1/equipment/",
            json=sample_equipment_data
        )
        
        assert response.status_code == 422
