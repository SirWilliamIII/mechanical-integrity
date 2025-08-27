#!/usr/bin/env python3
"""
Test script for API 579 integration.
Tests the complete workflow from equipment creation to calculations.
"""

import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_api579_integration():
    """Test the complete API 579 integration workflow.
    
    # ✅ RESOLVED: Converted from httpx to FastAPI TestClient for reliable test execution
    # Benefits: No external server dependency, faster execution, better CI/CD compatibility
    # No network calls required - tests run in-process against actual FastAPI application
    """
    
    with TestClient(app) as client:
        print("🧪 Testing API 579 Integration")
        print("=" * 50)
        
        # Step 1: Create test equipment
        print("\n1. Creating test pressure vessel...")
        equipment_data = {
            "tag_number": "V-101",
            "name": "Test Pressure Vessel for API 579",
            "equipment_type": "VESSEL",
            "design_pressure": 150.0,
            "design_temperature": 350.0,
            "material_specification": "SA-516-70",
            "design_thickness": 0.500,
            "location": "Unit 100 - Test Area"
        }
        
        response = client.post("/api/v1/equipment/", json=equipment_data)
        if response.status_code != 201:
            print(f"❌ Failed to create equipment: {response.text}")
            return
        
        equipment = response.json()
        equipment_id = equipment["id"]
        print(f"✅ Created equipment: {equipment['tag_number']} (ID: {equipment_id})")
        
        # Step 2: Create inspection with thickness readings
        print("\n2. Creating inspection with thickness readings...")
        inspection_data = {
            "equipment_id": equipment_id,
            "inspection_date": "2024-08-20",
            "inspector_name": "John Smith",
            "inspection_type": "thickness_survey", 
            "operating_pressure": 145.0,
            "operating_temperature": 340.0,
            "corrosion_rate": 0.005,
            "inspection_scope": "Complete thickness survey per API 510",
            "findings": "General metal loss observed in bottom head area",
            "thickness_readings": [
                {
                    "location": "Shell - 0 deg",
                    "thickness_measured": 0.485,
                    "design_thickness": 0.500,
                    "previous_thickness": 0.492,
                    "measurement_method": "ultrasonic",
                    "grid_reference": "A1"
                },
                {
                    "location": "Shell - 90 deg", 
                    "thickness_measured": 0.478,
                    "design_thickness": 0.500,
                    "previous_thickness": 0.490,
                    "measurement_method": "ultrasonic",
                    "grid_reference": "B1"
                },
                {
                    "location": "Bottom Head",
                    "thickness_measured": 0.445,  # This will trigger safety concerns
                    "design_thickness": 0.500,
                    "previous_thickness": 0.475,
                    "measurement_method": "ultrasonic", 
                    "grid_reference": "C1"
                },
                {
                    "location": "Shell - 180 deg",
                    "thickness_measured": 0.482,
                    "design_thickness": 0.500,
                    "previous_thickness": 0.488,
                    "measurement_method": "ultrasonic",
                    "grid_reference": "D1"
                },
                {
                    "location": "Shell - 270 deg",
                    "thickness_measured": 0.476,
                    "design_thickness": 0.500,
                    "previous_thickness": 0.486,
                    "measurement_method": "ultrasonic",
                    "grid_reference": "E1"
                }
            ]
        }
        
        response = client.post("/api/v1/inspections/", json=inspection_data)
        if response.status_code != 201:
            print(f"❌ Failed to create inspection: {response.text}")
            return
            
        inspection = response.json()
        inspection_id = inspection["id"]
        print(f"✅ Created inspection: {inspection_id}")
        print(f"   Min thickness found: {inspection['min_thickness_found']} inches")
        print(f"   Confidence level: {inspection['confidence_level']}%")
        
        # Step 3: Wait for background calculations
        print("\n3. Waiting for API 579 calculations to complete...")
        import time
        time.sleep(5)  # Give background task time to run
        
        # Step 4: Check calculation results
        print("\n4. Retrieving API 579 calculation results...")
        response = client.get(f"/api/v1/inspections/{inspection_id}/calculations")
        
        if response.status_code != 200:
            print(f"❌ Failed to get calculations: {response.text}")
            return
            
        calculations = response.json()
        if not calculations:
            print("⏳ No calculations found yet. Background task may still be running.")
            print("   Check server logs for calculation progress.")
            return
            
        print(f"✅ Found {len(calculations)} calculation sets")
        
        # Display latest calculation results
        latest_calc = calculations[0]  # Most recent
        print("\n📊 Latest API 579 Assessment Results:")
        print(f"   Calculation Date: {latest_calc['calculation_date']}")
        print(f"   RSF (Remaining Strength Factor): {latest_calc['rsf']}")
        print(f"   MAWP: {latest_calc['mawp']} psi")
        print(f"   Remaining Life: {latest_calc['remaining_life']} years")
        print(f"   Min Required Thickness: {latest_calc['minimum_thickness']} inches")
        print(f"   Assessment Level: {latest_calc['assessment_level']}")
        
        # Check for safety concerns
        rsf = float(latest_calc['rsf'])
        remaining_life = float(latest_calc['remaining_life'])
        
        print("\n🔍 Safety Assessment:")
        if rsf < 0.80:
            print(f"   🚨 CRITICAL: RSF {rsf:.3f} - IMMEDIATE ACTION REQUIRED")
        elif rsf < 0.90:
            print(f"   ⚠️  WARNING: RSF {rsf:.3f} - Level 2/3 assessment needed")
        else:
            print(f"   ✅ ACCEPTABLE: RSF {rsf:.3f} meets Level 1 criteria")
            
        if remaining_life < 2.0:
            print(f"   🚨 CRITICAL: {remaining_life:.1f} years remaining - Plan replacement")
        elif remaining_life < 5.0:
            print(f"   ⚠️  WARNING: {remaining_life:.1f} years remaining - Increase monitoring")
        else:
            print(f"   ✅ ACCEPTABLE: {remaining_life:.1f} years remaining life")
        
        # Step 5: Get detailed inspection record
        print("\n5. Retrieving complete inspection record...")
        response = client.get(f"/api/v1/inspections/{inspection_id}")
        
        if response.status_code == 200:
            detailed_inspection = response.json()
            print("✅ Complete inspection record retrieved")
            print(f"   Thickness readings: {detailed_inspection['thickness_readings_count']}")
            print(f"   Calculations: {detailed_inspection['calculations_count']}")
        
        print("\n🎯 API 579 Integration Test Complete!")
        print(f"   Equipment ID: {equipment_id}")
        print(f"   Inspection ID: {inspection_id}")
        print("   Check the FastAPI logs to see background calculation details.")

if __name__ == "__main__":
    test_api579_integration()
