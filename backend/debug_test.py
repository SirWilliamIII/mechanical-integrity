#!/usr/bin/env python3
"""Debug script to check inspection endpoint validation."""

import requests
import json

# Test data from the failing test
inspection_data = {
    "equipment_id": "V-101-INTEGRATION",
    "inspection_date": "2024-01-15T10:00:00Z",
    "inspection_type": "UT",
    "inspector_name": "RBI Inspector",
    "report_number": "RPT-RBI-001",
    "thickness_readings": [
        {
            "cml_number": "CML-01",
            "location": "Critical location",
            "thickness": "1.100",
            "previous_thickness": "1.250"
        }
    ]
}

print("Testing inspection endpoint validation...")
print(f"Test data: {json.dumps(inspection_data, indent=2)}")

try:
    # This will test against test server
    response = requests.post("http://testserver/api/v1/inspections/", json=inspection_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")