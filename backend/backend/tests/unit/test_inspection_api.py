"""
Unit tests for Inspection API endpoints.
Tests thickness measurements, corrosion calculations, and compliance.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, Mock

from backend.tests.conftest import (
    assert_response_success,
    validate_inspection_safety,
    assert_decimal_equal
)


class TestInspectionAPI:
    """Test suite for inspection endpoints."""
    
    def test_create_inspection_success(self, client, sample_inspection_data):
        """Test successful inspection creation."""
        response = client.post(
            "/api/v1/inspections/",
            json=sample_inspection_data
        )
        
        assert_response_success(response, 201)
        data = response.json()
        
        # Verify response
        assert data["equipment_id"] == sample_inspection_data["equipment_id"]
        assert data["inspection_type"] == sample_inspection_data["inspection_type"]
        assert data["inspector_name"] == sample_inspection_data["inspector_name"]
        assert len(data["thickness_readings"]) == len(sample_inspection_data["thickness_readings"])
        
        # Verify calculations
        assert_decimal_equal(Decimal(data["min_thickness_found"]), Decimal("1.238"))
        assert_decimal_equal(Decimal(data["avg_thickness"]), Decimal("1.241"))
        
        # Validate safety requirements
        validate_inspection_safety(data)
    
    def test_create_inspection_calculates_corrosion_rate(self, client, multiple_inspections, sample_equipment):
        """Test corrosion rate calculation from previous inspection."""
        # Create new inspection with lower thickness
        new_inspection_data = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": datetime.utcnow().isoformat(),
            "inspection_type": "UT",
            "inspector_name": "Test Inspector",
            "thickness_readings": [
                {"location": "N", "thickness": "1.235"},  # Lower than previous
                {"location": "E", "thickness": "1.230"},
                {"location": "S", "thickness": "1.233"},
                {"location": "W", "thickness": "1.232"}
            ],
            "report_number": "TEST-001"
        }
        
        response = client.post(
            "/api/v1/inspections/",
            json=new_inspection_data
        )
        
        assert_response_success(response, 201)
        data = response.json()
        
        # Verify corrosion rate was calculated
        assert data["corrosion_rate_calculated"] is not None
        assert float(data["corrosion_rate_calculated"]) > 0
        
        # Verify it's reasonable (should be around 0.003-0.005 inches/year)
        assert 0.001 < float(data["corrosion_rate_calculated"]) < 0.010
    
    def test_create_inspection_no_thickness_readings(self, client, sample_inspection_data):
        """Test that inspection without thickness readings is rejected."""
        sample_inspection_data["thickness_readings"] = []
        
        response = client.post(
            "/api/v1/inspections/",
            json=sample_inspection_data
        )
        
        assert response.status_code == 422
    
    def test_create_inspection_duplicate_locations(self, client, sample_inspection_data):
        """Test that duplicate CML locations are rejected."""
        sample_inspection_data["thickness_readings"] = [
            {"location": "N", "thickness": "1.245"},
            {"location": "N", "thickness": "1.240"},  # Duplicate location
        ]
        
        response = client.post(
            "/api/v1/inspections/",
            json=sample_inspection_data
        )
        
        assert response.status_code == 422
    
    def test_create_inspection_invalid_thickness(self, client, sample_inspection_data):
        """Test that negative thickness is rejected."""
        sample_inspection_data["thickness_readings"][0]["thickness"] = "-0.5"
        
        response = client.post(
            "/api/v1/inspections/",
            json=sample_inspection_data
        )
        
        assert response.status_code == 422
    
    def test_get_inspection_by_id(self, client, sample_inspection):
        """Test retrieving inspection by ID."""
        response = client.get(f"/api/v1/inspections/{sample_inspection.id}")
        
        assert_response_success(response)
        data = response.json()
        
        assert data["id"] == str(sample_inspection.id)
        assert data["equipment_id"] == str(sample_inspection.equipment_id)
    
    def test_get_equipment_inspections(self, client, multiple_inspections, sample_equipment):
        """Test retrieving all inspections for equipment."""
        response = client.get(f"/api/v1/inspections/equipment/{sample_equipment.id}")
        
        assert_response_success(response)
        data = response.json()
        
        assert len(data) == len(multiple_inspections)
        # Should be ordered by date descending (newest first)
        dates = [datetime.fromisoformat(item["inspection_date"].replace("Z", "")) for item in data]
        assert dates == sorted(dates, reverse=True)
    
    def test_verify_inspection(self, client, sample_inspection):
        """Test human verification of inspection."""
        response = client.post(
            f"/api/v1/inspections/{sample_inspection.id}/verify",
            params={
                "verifier_name": "Jane Doe, PE",
                "notes": "Reviewed and approved. Corrosion within acceptable limits."
            }
        )
        
        assert_response_success(response)
        data = response.json()
        
        assert data["verified_by"] == "Jane Doe, PE"
        assert "verified_at" in data
        
        # Verify cannot be verified twice
        response = client.post(
            f"/api/v1/inspections/{sample_inspection.id}/verify",
            params={"verifier_name": "Another Person"}
        )
        
        assert response.status_code == 400
        assert "already verified" in response.json()["detail"]
    
    def test_analyze_corrosion_with_history(self, client, multiple_inspections):
        """Test corrosion analysis with inspection history."""
        latest_inspection = multiple_inspections[-1]
        
        response = client.post(
            f"/api/v1/inspections/{latest_inspection.id}/analyze-corrosion"
        )
        
        assert_response_success(response)
        data = response.json()
        
        # Verify analysis results
        assert data["equipment_id"] == str(latest_inspection.equipment_id)
        assert data["current_min_thickness"] == float(latest_inspection.min_thickness_found)
        assert data["corrosion_rate"] is not None
        assert data["remaining_life"] is not None
        assert data["confidence_level"] > 50
        
        # Check calculation method
        assert "regression" in data["calculation_method"].lower() or "average" in data["calculation_method"].lower()
        
        # Verify assumptions and warnings
        assert len(data["assumptions"]) > 0
        assert any("uniform corrosion" in a.lower() for a in data["assumptions"])
    
    def test_analyze_corrosion_critical_warning(self, client, sample_equipment, test_db):
        """Test critical warning for low remaining life."""
        # Create inspection with very low thickness
        thin_inspection = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": datetime.utcnow().isoformat(),
            "inspection_type": "UT",
            "inspector_name": "Test",
            "thickness_readings": [
                {"location": "N", "thickness": "0.650"}  # Very thin (close to 50% of nominal)
            ],
            "report_number": "CRITICAL-001"
        }
        
        response = client.post("/api/v1/inspections/", json=thin_inspection)
        assert_response_success(response, 201)
        inspection_id = response.json()["id"]
        
        # Analyze corrosion
        response = client.post(f"/api/v1/inspections/{inspection_id}/analyze-corrosion")
        assert_response_success(response)
        data = response.json()
        
        # Should have critical warning
        assert any("CRITICAL" in w for w in data["warnings"])
        assert data["remaining_life"] is not None
        if data["remaining_life"]:
            assert float(data["remaining_life"]) < 2.0  # Less than 2 years
    
    @patch('backend.services.document_analyzer.DocumentAnalyzer.extract_inspection_data')
    def test_upload_inspection_report(self, mock_extract, client, sample_equipment, mock_ollama_response):
        """Test uploading and processing inspection report."""
        # Mock the document analyzer
        mock_extract.return_value = mock_ollama_response
        
        # Create a mock PDF file
        pdf_content = b"Mock PDF content"
        files = {"file": ("inspection_report.pdf", pdf_content, "application/pdf")}
        
        response = client.post(
            f"/api/v1/inspections/upload-report?equipment_tag={sample_equipment.tag}",
            files=files
        )
        
        assert_response_success(response, 201)
        data = response.json()
        
        # Verify AI processing flags
        assert data["ai_processed"] is True
        assert data["ai_confidence_score"] == 85.0
        assert data["inspector_name"] == "AI Extracted"
        
        # Verify thickness data was extracted
        assert len(data["thickness_readings"]) == 3
        assert data["min_thickness_found"] == 1.238


class TestInspectionCalculations:
    """Test safety-critical calculations."""
    
    def test_minimum_thickness_calculation(self, client, sample_inspection_data):
        """Test correct minimum thickness identification."""
        sample_inspection_data["thickness_readings"] = [
            {"location": "1", "thickness": "1.250"},
            {"location": "2", "thickness": "1.235"},  # Minimum
            {"location": "3", "thickness": "1.245"},
            {"location": "4", "thickness": "1.240"}
        ]
        
        response = client.post("/api/v1/inspections/", json=sample_inspection_data)
        assert_response_success(response, 201)
        data = response.json()
        
        assert_decimal_equal(Decimal(data["min_thickness_found"]), Decimal("1.235"))
    
    def test_average_thickness_calculation(self, client, sample_inspection_data):
        """Test correct average thickness calculation."""
        sample_inspection_data["thickness_readings"] = [
            {"location": "1", "thickness": "1.200"},
            {"location": "2", "thickness": "1.300"},
            {"location": "3", "thickness": "1.250"}
        ]
        
        response = client.post("/api/v1/inspections/", json=sample_inspection_data)
        assert_response_success(response, 201)
        data = response.json()
        
        # Average should be 1.250
        assert_decimal_equal(Decimal(data["avg_thickness"]), Decimal("1.250"))
    
    def test_corrosion_rate_time_calculation(self, client, sample_equipment, test_db):
        """Test accurate time-based corrosion rate calculation."""
        # Create first inspection 2 years ago
        first_date = datetime.utcnow() - timedelta(days=730)  # Exactly 2 years
        first_inspection = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": first_date.isoformat(),
            "inspection_type": "UT",
            "inspector_name": "Test",
            "thickness_readings": [{"location": "N", "thickness": "1.250"}],
            "report_number": "FIRST-001"
        }
        
        response = client.post("/api/v1/inspections/", json=first_inspection)
        assert_response_success(response, 201)
        
        # Create second inspection today with 0.010" loss
        second_inspection = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": datetime.utcnow().isoformat(),
            "inspection_type": "UT", 
            "inspector_name": "Test",
            "thickness_readings": [{"location": "N", "thickness": "1.240"}],
            "report_number": "SECOND-001"
        }
        
        response = client.post("/api/v1/inspections/", json=second_inspection)
        assert_response_success(response, 201)
        data = response.json()
        
        # Corrosion rate should be 0.010" / 2 years = 0.005 inches/year
        assert data["corrosion_rate_calculated"] is not None
        assert_decimal_equal(
            Decimal(data["corrosion_rate_calculated"]), 
            Decimal("0.005"),
            precision=3
        )


class TestInspectionCompliance:
    """Test regulatory compliance features."""
    
    def test_inspection_interval_calculation(self, client, sample_equipment, test_db):
        """Test next inspection interval based on API standards."""
        # Create inspection with known corrosion rate
        inspection_data = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": datetime.utcnow().isoformat(),
            "inspection_type": "UT",
            "inspector_name": "Test",
            "thickness_readings": [
                {"location": "N", "thickness": "1.200"}  # 0.050" loss from nominal
            ],
            "report_number": "INTERVAL-001"
        }
        
        response = client.post("/api/v1/inspections/", json=inspection_data)
        assert_response_success(response, 201)
        
        # Check equipment was updated with next inspection date
        response = client.get(f"/api/v1/equipment/{sample_equipment.id}")
        equipment_data = response.json()
        
        assert equipment_data["next_inspection_due"] is not None
        
        # Verify interval is reasonable (should be less than 5 years for vessels)
        next_due = datetime.fromisoformat(equipment_data["next_inspection_due"].replace("Z", ""))
        interval_days = (next_due - datetime.utcnow()).days
        assert 0 < interval_days < (5 * 365)  # Less than 5 years
    
    def test_confidence_level_based_on_readings(self, client, sample_equipment):
        """Test confidence level increases with more readings."""
        # Test with few readings (low confidence)
        few_readings = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": datetime.utcnow().isoformat(),
            "inspection_type": "UT",
            "inspector_name": "Test",
            "thickness_readings": [
                {"location": "N", "thickness": "1.240"},
                {"location": "S", "thickness": "1.245"}
            ],
            "report_number": "FEW-001"
        }
        
        response = client.post("/api/v1/inspections/", json=few_readings)
        assert_response_success(response, 201)
        low_confidence = float(response.json()["confidence_level"])
        
        # Test with many readings (high confidence)
        many_readings = {
            "equipment_id": str(sample_equipment.id),
            "inspection_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "inspection_type": "UT",
            "inspector_name": "Test",
            "thickness_readings": [
                {"location": f"CML-{i}", "thickness": f"1.24{i}"}
                for i in range(10)
            ],
            "report_number": "MANY-001"
        }
        
        response = client.post("/api/v1/inspections/", json=many_readings)
        assert_response_success(response, 201)
        high_confidence = float(response.json()["confidence_level"])
        
        # More readings should give higher confidence
        assert high_confidence > low_confidence
