#!/usr/bin/env python3
"""Test corrected inspection data format."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_corrected_inspection_format():
    """Test inspection with corrected field names."""
    
    # Corrected inspection data with proper field names
    corrected_inspection_data = {
        "equipment_id": "V-101-INTEGRATION",
        "inspection_date": "2024-01-15T10:00:00Z",
        "inspection_type": "UT",
        "inspector_name": "RBI Inspector",
        "report_number": "RPT-RBI-001",
        "thickness_readings": [
            {
                "cml_number": "CML-01",
                "location_description": "Critical location",  # Changed from 'location' to 'location_description'
                "thickness_measured": "1.100",              # Changed from 'thickness' to 'thickness_measured'
                "design_thickness": "1.250",                # Added required field
                "previous_thickness": "1.250"               # Optional field
            }
        ]
    }
    
    print("Testing corrected inspection data format...")
    print("Expected field names:")
    print("- location_description (not 'location')")
    print("- thickness_measured (not 'thickness')")
    print("- design_thickness (required)")
    
    response = client.post("/api/v1/inspections/", json=corrected_inspection_data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 201:
        print(f"Response: {response.text}")
        return False
    else:
        print("✅ Inspection created successfully!")
        return True

if __name__ == "__main__":
    test_corrected_inspection_format()