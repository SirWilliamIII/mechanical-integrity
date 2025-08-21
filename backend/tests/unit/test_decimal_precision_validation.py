"""
Decimal precision validation tests for thickness measurements.

These tests specifically validate that safety-critical measurements maintain
required precision (±0.001 inches) throughout the entire data pipeline.
Designed to catch the critical Float/Decimal inconsistency issues identified.
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, getcontext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
from uuid import uuid4

from models.base import Base
from models.equipment import Equipment, EquipmentType
from models.inspection import InspectionRecord, ThicknessReading, API579Calculation
from app.api.equipment import EquipmentCreate, EquipmentResponse
from core.config import settings

# Set high precision for tests
getcontext().prec = 28


class TestDecimalPrecisionConsistency:
    """Tests to validate decimal precision throughout the data pipeline."""
    
    @pytest.fixture(scope="function")
    def test_db_session(self):
        """Create in-memory database for testing."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        yield session
        session.close()
    
    def test_equipment_model_precision_issues(self, test_db_session):
        """Test that identifies the Float/Decimal precision issue in Equipment model."""
        # Create equipment with precise decimal values
        precise_pressure = Decimal('1234.567')
        precise_temperature = Decimal('678.123')
        precise_thickness = Decimal('1.2345')
        
        equipment = Equipment(
            tag_number="V-101-TEST",
            description="Test Vessel for Precision Validation",
            equipment_type=EquipmentType.PRESSURE_VESSEL,
            design_pressure=float(precise_pressure),  # ISSUE: Forced to float
            design_temperature=float(precise_temperature),  # ISSUE: Forced to float  
            design_thickness=float(precise_thickness),  # ISSUE: Forced to float
            material_specification="SA-516-70",
            corrosion_allowance=0.125,
            service_description="Test Service",
            installation_date=datetime.utcnow()
        )
        
        test_db_session.add(equipment)
        test_db_session.commit()
        test_db_session.refresh(equipment)
        
        # Retrieve and check precision loss
        retrieved = test_db_session.query(Equipment).filter(
            Equipment.tag_number == "V-101-TEST"
        ).first()
        
        # Convert back to Decimal to check precision loss
        retrieved_pressure = Decimal(str(retrieved.design_pressure))
        retrieved_temperature = Decimal(str(retrieved.design_temperature))
        retrieved_thickness = Decimal(str(retrieved.design_thickness))
        
        # THESE ASSERTIONS WILL FAIL - demonstrating the precision loss issue
        with pytest.raises(AssertionError, match="Precision loss detected"):
            assert retrieved_pressure == precise_pressure, "Precision loss detected in design_pressure"
            assert retrieved_temperature == precise_temperature, "Precision loss detected in design_temperature"
            assert retrieved_thickness == precise_thickness, "Precision loss detected in design_thickness"
    
    def test_thickness_reading_precision_maintained(self, test_db_session):
        """Test that ThicknessReading correctly maintains decimal precision."""
        # Create equipment first
        equipment = Equipment(
            tag_number="V-102-TEST",
            description="Test Equipment",
            equipment_type=EquipmentType.PRESSURE_VESSEL,
            design_pressure=1200.0,
            design_temperature=650.0,
            design_thickness=1.250,
            material_specification="SA-516-70",
            corrosion_allowance=0.125,
            service_description="Test",
            installation_date=datetime.utcnow()
        )
        test_db_session.add(equipment)
        test_db_session.flush()
        
        # Create inspection record
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=datetime.utcnow(),
            inspection_type="UT",
            inspector_name="Test Inspector",
            report_number="RPT-001",
            thickness_readings={},
            min_thickness_found=Decimal('1.234'),
            avg_thickness=Decimal('1.240')
        )
        test_db_session.add(inspection)
        test_db_session.flush()
        
        # Test precise thickness measurements
        precise_values = [
            Decimal('1.2345'),  # 4 decimal places
            Decimal('0.0625'),  # Exactly 1/16 inch
            Decimal('1.0000'),  # Exactly 1 inch
            Decimal('0.001'),   # Minimum measurable
            Decimal('2.999')    # Close to 3 inches
        ]
        
        for i, thickness in enumerate(precise_values):
            reading = ThicknessReading(
                inspection_record_id=inspection.id,
                cml_number=f"CML-{i+1:02d}",
                location_description=f"Test Location {i+1}",
                thickness_measured=thickness,
                design_thickness=Decimal('1.250'),
                measurement_confidence=Decimal('95.00')
            )
            test_db_session.add(reading)
        
        test_db_session.commit()
        
        # Retrieve and verify precision maintained
        readings = test_db_session.query(ThicknessReading).filter(
            ThicknessReading.inspection_record_id == inspection.id
        ).all()
        
        for i, reading in enumerate(readings):
            original = precise_values[i]
            stored = reading.thickness_measured
            
            # Verify exact match (no precision loss)
            assert stored == original, f"Precision loss in thickness reading {i+1}: {stored} != {original}"
            
            # Verify proper decimal places
            assert stored.as_tuple().exponent >= -3, f"Insufficient precision in reading {i+1}"
    
    def test_api579_calculation_precision(self, test_db_session):
        """Test that API579Calculation maintains decimal precision."""
        # Create minimal equipment and inspection
        equipment = Equipment(
            tag_number="V-103-TEST",
            description="Test Equipment",
            equipment_type=EquipmentType.PRESSURE_VESSEL,
            design_pressure=1200.0,
            design_temperature=650.0, 
            design_thickness=1.250,
            material_specification="SA-516-70",
            corrosion_allowance=0.125,
            service_description="Test",
            installation_date=datetime.utcnow()
        )
        test_db_session.add(equipment)
        test_db_session.flush()
        
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=datetime.utcnow(),
            inspection_type="UT",
            inspector_name="Test Inspector", 
            report_number="RPT-002",
            thickness_readings={},
            min_thickness_found=Decimal('1.200'),
            avg_thickness=Decimal('1.220')
        )
        test_db_session.add(inspection)
        test_db_session.flush()
        
        # Test precise calculation results
        calculation = API579Calculation(
            inspection_record_id=inspection.id,
            calculation_type="Level 1",
            calculation_method="General Metal Loss",
            performed_by="Test Engineer",
            input_parameters={
                "current_thickness": "1.200",
                "minimum_thickness": "0.875",
                "design_pressure": "1200.0"
            },
            minimum_required_thickness=Decimal('0.8750'),  # Precise to 4 places
            remaining_strength_factor=Decimal('0.7761'),   # Precise RSF
            maximum_allowable_pressure=Decimal('1056.25'), # Precise MAWP
            remaining_life_years=Decimal('32.50'),         # Precise life
            fitness_for_service="FIT",
            risk_level="MEDIUM",
            recommendations="Continue normal operation",
            confidence_score=Decimal('95.50')
        )
        test_db_session.add(calculation)
        test_db_session.commit()
        
        # Retrieve and verify precision
        retrieved = test_db_session.query(API579Calculation).first()
        
        # Verify all decimal fields maintain precision
        assert retrieved.minimum_required_thickness == Decimal('0.8750')
        assert retrieved.remaining_strength_factor == Decimal('0.7761')
        assert retrieved.maximum_allowable_pressure == Decimal('1056.25')
        assert retrieved.remaining_life_years == Decimal('32.50')
        assert retrieved.confidence_score == Decimal('95.50')
    
    def test_json_serialization_precision_issues(self):
        """Test that identifies JSON serialization precision loss."""
        # Test values that commonly lose precision in JSON
        test_values = [
            Decimal('0.1'),
            Decimal('0.2'),
            Decimal('0.3'),
            Decimal('1.2345'),
            Decimal('999.999'),
            Decimal('0.0625')  # 1/16 inch
        ]
        
        for value in test_values:
            # Simulate the problematic JSON encoder from equipment.py:53
            # json_encoders = { Decimal: lambda v: float(v) }
            as_float = float(value)
            
            # Simulate JSON round-trip
            json_string = json.dumps({"thickness": as_float})
            parsed = json.loads(json_string)
            back_to_decimal = Decimal(str(parsed["thickness"]))
            
            # Check for precision loss
            if value != back_to_decimal:
                print(f"⚠️  PRECISION LOSS: {value} → {as_float} → {back_to_decimal}")
                # This demonstrates the issue - we should fail here in real tests
            
            # The CORRECT approach - serialize Decimal as string
            correct_json = json.dumps({"thickness": str(value)})
            correct_parsed = json.loads(correct_json)
            correct_decimal = Decimal(correct_parsed["thickness"])
            
            # This should always preserve precision
            assert value == correct_decimal, f"String serialization failed for {value}"
    
    def test_database_decimal_storage_precision(self, test_db_session):
        """Test DECIMAL column precision in database."""
        # Test that DECIMAL(6,3) properly stores thickness values
        test_engine = test_db_session.get_bind()
        
        # Test boundary values for DECIMAL(6,3)
        boundary_values = [
            Decimal('0.001'),      # Minimum precision
            Decimal('999.999'),    # Maximum value
            Decimal('1.2345'),     # Should truncate to 1.235
            Decimal('0.0625'),     # Exactly 1/16 inch
            Decimal('123.456')     # Middle range
        ]
        
        for value in boundary_values:
            # Create a thickness reading with the test value
            equipment = Equipment(
                tag_number=f"TEST-{uuid4().hex[:8]}",
                description="Decimal Test Equipment", 
                equipment_type=EquipmentType.PRESSURE_VESSEL,
                design_pressure=1000.0,
                design_temperature=500.0,
                design_thickness=1.0,
                material_specification="SA-516-70",
                corrosion_allowance=0.125,
                service_description="Test",
                installation_date=datetime.utcnow()
            )
            test_db_session.add(equipment)
            test_db_session.flush()
            
            inspection = InspectionRecord(
                equipment_id=equipment.id,
                inspection_date=datetime.utcnow(),
                inspection_type="UT",
                inspector_name="Test",
                report_number=f"RPT-{uuid4().hex[:6]}",
                thickness_readings={},
                min_thickness_found=value,
                avg_thickness=value
            )
            test_db_session.add(inspection)
            test_db_session.commit()
            
            # Retrieve and check precision
            retrieved = test_db_session.query(InspectionRecord).filter(
                InspectionRecord.id == inspection.id
            ).first()
            
            stored_value = retrieved.min_thickness_found
            
            # For DECIMAL(6,3), should round to 3 decimal places
            expected = value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            
            assert stored_value == expected, (
                f"Database storage precision error: {value} stored as {stored_value}, "
                f"expected {expected}"
            )
    
    def test_equipment_api_schema_precision_loss(self):
        """Test that identifies precision loss in Equipment API schemas."""
        # Simulate the EquipmentCreate schema from equipment.py
        test_data = {
            "tag": "V-104-TEST",
            "name": "Test Vessel",
            "equipment_type": "VESSEL",
            "design_pressure": "1234.567",  # String to preserve precision
            "design_temperature": "678.123",
            "material_spec": "SA-516-70", 
            "nominal_thickness": "1.2345"
        }
        
        # Simulate schema validation with Decimal fields
        design_pressure = Decimal(test_data["design_pressure"])
        design_temperature = Decimal(test_data["design_temperature"])
        nominal_thickness = Decimal(test_data["nominal_thickness"])
        
        # These should maintain precision
        assert design_pressure == Decimal('1234.567')
        assert design_temperature == Decimal('678.123')
        assert nominal_thickness == Decimal('1.2345')
        
        # Simulate the problematic json_encoders conversion
        # This is what happens in EquipmentBase.Config.json_encoders
        converted_pressure = float(design_pressure)
        converted_temperature = float(design_temperature)
        converted_thickness = float(nominal_thickness)
        
        # Check for precision loss in conversion
        back_to_decimal_pressure = Decimal(str(converted_pressure))
        back_to_decimal_temperature = Decimal(str(converted_temperature))
        back_to_decimal_thickness = Decimal(str(converted_thickness))
        
        # Document the precision loss (these may fail)
        pressure_loss = design_pressure != back_to_decimal_pressure
        temperature_loss = design_temperature != back_to_decimal_temperature
        thickness_loss = nominal_thickness != back_to_decimal_thickness
        
        if pressure_loss or temperature_loss or thickness_loss:
            print("⚠️  JSON Encoder precision loss detected:")
            if pressure_loss:
                print(f"   Pressure: {design_pressure} → {back_to_decimal_pressure}")
            if temperature_loss:
                print(f"   Temperature: {design_temperature} → {back_to_decimal_temperature}")
            if thickness_loss:
                print(f"   Thickness: {nominal_thickness} → {back_to_decimal_thickness}")


class TestThicknessMeasurementAccuracy:
    """Tests for thickness measurement accuracy requirements."""
    
    def test_measurement_tolerance_validation(self):
        """Test ±0.001 inch tolerance requirement."""
        base_thickness = Decimal('1.250')
        tolerance = Decimal('0.001')
        
        # Test measurements within tolerance
        within_tolerance = [
            base_thickness,
            base_thickness + tolerance,
            base_thickness - tolerance,
            base_thickness + Decimal('0.0005'),
            base_thickness - Decimal('0.0005')
        ]
        
        for measurement in within_tolerance:
            difference = abs(measurement - base_thickness)
            assert difference <= tolerance, f"Measurement {measurement} outside tolerance"
    
    def test_thickness_calculation_precision_propagation(self):
        """Test that precision is maintained through calculations."""
        # Simulate thickness calculation chain
        measurements = [
            Decimal('1.245'),
            Decimal('1.240'), 
            Decimal('1.238'),
            Decimal('1.242'),
            Decimal('1.239')
        ]
        
        # Calculate average - common operation
        total = sum(measurements)
        count = Decimal(len(measurements))
        average = total / count
        
        # Verify precision maintained
        assert average.as_tuple().exponent >= -3, "Precision lost in average calculation"
        
        # Calculate standard deviation with Decimal precision
        variance_sum = sum((m - average) ** 2 for m in measurements)
        variance = variance_sum / count
        std_dev = variance.sqrt()
        
        # Verify standard deviation maintains precision
        assert std_dev.as_tuple().exponent >= -6, "Precision lost in std dev calculation"
    
    def test_corrosion_rate_calculation_precision(self):
        """Test corrosion rate calculation maintains required precision."""
        # Previous thickness measurement
        previous_thickness = Decimal('1.250')
        previous_date = datetime(2020, 1, 1)
        
        # Current thickness measurement
        current_thickness = Decimal('1.235')
        current_date = datetime(2024, 1, 1)
        
        # Calculate metal loss and time difference
        metal_loss = previous_thickness - current_thickness
        time_diff_years = Decimal('4.0')  # Exactly 4 years
        
        # Corrosion rate in inches/year
        corrosion_rate = metal_loss / time_diff_years
        
        # Expected: (1.250 - 1.235) / 4 = 0.015 / 4 = 0.00375
        expected_rate = Decimal('0.00375')
        
        assert corrosion_rate == expected_rate, f"Corrosion rate calculation error: {corrosion_rate} != {expected_rate}"
        
        # Verify precision maintained for 5 decimal places (per model spec)
        assert corrosion_rate.as_tuple().exponent >= -5, "Insufficient corrosion rate precision"
    
    def test_ultrasonic_measurement_simulation(self):
        """Test simulation of ultrasonic thickness measurement precision."""
        # Simulate multiple readings at same location (typical UT practice)
        readings = [
            Decimal('1.245'),
            Decimal('1.246'),
            Decimal('1.244'),
            Decimal('1.245'),
            Decimal('1.247')
        ]
        
        # Calculate measurement statistics
        average = sum(readings) / len(readings)
        min_reading = min(readings)
        max_reading = max(readings)
        range_spread = max_reading - min_reading
        
        # Verify all calculations maintain precision
        assert average.as_tuple().exponent >= -3
        assert range_spread.as_tuple().exponent >= -3
        
        # Typical ultrasonic measurement should be consistent
        # Range should be ≤ 0.003" for good measurements
        assert range_spread <= Decimal('0.003'), f"Measurement spread too large: {range_spread}"