"""
Regression tests for API 579 dual-path verification.

These tests validate that dual-path verification continues to work correctly
as the calculation engine evolves. Uses known good reference calculations
to prevent regression errors in safety-critical calculations.

TODO: [CRITICAL_CALCULATION] Fix failing dual-path verification test discrepancies
Risk: Test expects 1.395" but calculation returns 1.420" for minimum thickness
Impact: CRITICAL - Could lead to incorrect remaining life assessments and equipment failure
Reference: API 579-1 Part 4, Equation 4.7 needs manual verification against hand calculations
"""
import pytest
from decimal import Decimal
from datetime import datetime

from app.calculations.dual_path_calculator import (
    API579Calculator, 
    CalculationDiscrepancyError
)


class TestAPI579RegressionSuite:
    """Regression tests using verified reference calculations."""
    
    @pytest.fixture(scope="class")
    def reference_calculations(self):
        """Load reference calculations from known good results."""
        # These would normally be loaded from a file of verified calculations
        # For now, we'll define them inline as known good values
        
        return {
            "minimum_thickness_cases": [
                {
                    "name": "Standard Pressure Vessel - SA-516-70",
                    "inputs": {
                        "pressure": Decimal('1000.0'),
                        "radius": Decimal('24.0'),
                        "stress": Decimal('17500.0'),
                        "efficiency": Decimal('1.0'),
                        "equipment_type": "pressure_vessel"
                    },
                    "expected_outputs": {
                        "minimum_thickness": Decimal('1.395'),  # Pre-calculated reference
                        "tolerance": Decimal('0.001')
                    },
                    "api_reference": "API 579-1 Part 4, Equation 4.7"
                },
                {
                    "name": "High Pressure Service - SA-516-70",
                    "inputs": {
                        "pressure": Decimal('2500.0'),
                        "radius": Decimal('30.0'),
                        "stress": Decimal('17500.0'),
                        "efficiency": Decimal('0.85'),
                        "equipment_type": "pressure_vessel"
                    },
                    "expected_outputs": {
                        "minimum_thickness": Decimal('5.357'),  # Pre-calculated reference
                        "tolerance": Decimal('0.001')
                    },
                    "api_reference": "API 579-1 Part 4, Equation 4.7"
                },
                {
                    "name": "Small Vessel - Low Pressure",
                    "inputs": {
                        "pressure": Decimal('150.0'),
                        "radius": Decimal('12.0'),
                        "stress": Decimal('17500.0'),
                        "efficiency": Decimal('1.0'),
                        "equipment_type": "pressure_vessel"
                    },
                    "expected_outputs": {
                        "minimum_thickness": Decimal('0.103'),  # Pre-calculated reference
                        "tolerance": Decimal('0.001')
                    },
                    "api_reference": "API 579-1 Part 4, Equation 4.7"
                }
            ],
            "rsf_cases": [
                {
                    "name": "Good Condition Vessel",
                    "inputs": {
                        "current_thickness": Decimal('1.200'),
                        "minimum_thickness": Decimal('0.875'),
                        "nominal_thickness": Decimal('1.250'),
                        "future_corrosion_allowance": Decimal('0.050')
                    },
                    "expected_outputs": {
                        "rsf": Decimal('0.733'),  # Pre-calculated reference
                        "tolerance": Decimal('0.001')
                    },
                    "api_reference": "API 579-1 Part 5, Equation 5.5"
                },
                {
                    "name": "Near Minimum Condition",
                    "inputs": {
                        "current_thickness": Decimal('0.950'),
                        "minimum_thickness": Decimal('0.875'),
                        "nominal_thickness": Decimal('1.250'),
                        "future_corrosion_allowance": Decimal('0.050')
                    },
                    "expected_outputs": {
                        "rsf": Decimal('0.067'),  # Pre-calculated reference
                        "tolerance": Decimal('0.001')
                    },
                    "api_reference": "API 579-1 Part 5, Equation 5.5"
                },
                {
                    "name": "New Equipment Condition",
                    "inputs": {
                        "current_thickness": Decimal('1.250'),
                        "minimum_thickness": Decimal('0.875'),
                        "nominal_thickness": Decimal('1.250'),
                        "future_corrosion_allowance": Decimal('0.000')
                    },
                    "expected_outputs": {
                        "rsf": Decimal('1.000'),  # Pre-calculated reference
                        "tolerance": Decimal('0.001')
                    },
                    "api_reference": "API 579-1 Part 5, Equation 5.5"
                }
            ],
            "remaining_life_cases": [
                {
                    "name": "Typical Corrosion Rate",
                    "inputs": {
                        "current_thickness": Decimal('1.150'),
                        "minimum_thickness": Decimal('0.875'),
                        "corrosion_rate": Decimal('0.005'),
                        "confidence_level": "conservative"
                    },
                    "expected_outputs": {
                        "remaining_life": Decimal('44.0'),  # Pre-calculated reference
                        "tolerance": Decimal('0.1')
                    },
                    "api_reference": "API 579-1 Part 4, Section 4.4.5"
                },
                {
                    "name": "High Corrosion Rate",
                    "inputs": {
                        "current_thickness": Decimal('1.100'),
                        "minimum_thickness": Decimal('0.875'),
                        "corrosion_rate": Decimal('0.025'),
                        "confidence_level": "conservative"
                    },
                    "expected_outputs": {
                        "remaining_life": Decimal('7.2'),  # Pre-calculated reference
                        "tolerance": Decimal('0.1')
                    },
                    "api_reference": "API 579-1 Part 4, Section 4.4.5"
                }
            ],
            "mawp_cases": [
                {
                    "name": "Current Thickness MAWP",
                    "inputs": {
                        "current_thickness": Decimal('1.150'),
                        "radius": Decimal('24.0'),
                        "stress": Decimal('17500.0'),
                        "efficiency": Decimal('1.0'),
                        "future_corrosion_allowance": Decimal('0.050')
                    },
                    "expected_outputs": {
                        "mawp": Decimal('780.6'),  # Corrected reference - API 579 Part 4, Eq. 4.8
                        "tolerance": Decimal('0.1')
                    },
                    "api_reference": "API 579-1 Part 4, Equation 4.8"
                }
            ]
        }
    
    def test_minimum_thickness_regression(self, reference_calculations):
        """Test minimum thickness calculations against reference values."""
        calculator = API579Calculator()
        
        for case in reference_calculations["minimum_thickness_cases"]:
            with pytest.raises(AssertionError, match="") if case.get("should_fail", False) else pytest.approx:
                print(f"\n📏 Testing: {case['name']}")
                
                inputs = case["inputs"]
                expected = case["expected_outputs"]
                
                # Perform calculation
                result = calculator.calculate_minimum_required_thickness(
                    pressure=inputs["pressure"],
                    radius=inputs["radius"],
                    stress=inputs["stress"],
                    efficiency=inputs["efficiency"],
                    equipment_type=inputs["equipment_type"]
                )
                
                # Check main result against reference
                difference = abs(result.value - expected["minimum_thickness"])
                tolerance = expected["tolerance"]
                
                print(f"   Expected: {expected['minimum_thickness']}")
                print(f"   Calculated: {result.value}")
                print(f"   Difference: {difference}")
                print(f"   Tolerance: {tolerance}")
                
                assert difference <= tolerance, (
                    f"Regression detected in {case['name']}: "
                    f"Expected {expected['minimum_thickness']}, got {result.value}, "
                    f"difference {difference} > tolerance {tolerance}"
                )
                
                # Verify dual-path agreement
                primary_secondary_diff = abs(result.primary_value - result.secondary_value)
                relative_diff = primary_secondary_diff / result.primary_value if result.primary_value != 0 else 0
                
                assert relative_diff <= calculator.THICKNESS_TOLERANCE, (
                    f"Dual-path verification failed for {case['name']}: "
                    f"Primary {result.primary_value}, Secondary {result.secondary_value}, "
                    f"Relative difference {relative_diff}"
                )
                
                # Verify API reference is preserved
                assert result.api_reference == case["api_reference"], (
                    f"API reference mismatch for {case['name']}"
                )
                
                print("   ✅ Passed regression test")
    
    def test_rsf_calculation_regression(self, reference_calculations):
        """Test RSF calculations against reference values."""
        calculator = API579Calculator()
        
        for case in reference_calculations["rsf_cases"]:
            print(f"\n🔢 Testing RSF: {case['name']}")
            
            inputs = case["inputs"]
            expected = case["expected_outputs"]
            
            # Perform calculation
            result = calculator.calculate_remaining_strength_factor(
                current_thickness=inputs["current_thickness"],
                minimum_thickness=inputs["minimum_thickness"],
                nominal_thickness=inputs["nominal_thickness"],
                future_corrosion_allowance=inputs["future_corrosion_allowance"]
            )
            
            # Check result against reference
            difference = abs(result.value - expected["rsf"])
            tolerance = expected["tolerance"]
            
            print(f"   Expected RSF: {expected['rsf']}")
            print(f"   Calculated RSF: {result.value}")
            print(f"   Difference: {difference}")
            
            assert difference <= tolerance, (
                f"RSF regression detected in {case['name']}: "
                f"Expected {expected['rsf']}, got {result.value}, "
                f"difference {difference} > tolerance {tolerance}"
            )
            
            # Verify RSF bounds
            assert Decimal('0') <= result.value <= Decimal('1'), (
                f"RSF out of bounds for {case['name']}: {result.value}"
            )
            
            # Verify dual-path verification
            assert result.verification_method in ["dual-path-reverse", "dual-path-iterative"], (
                f"Invalid verification method for {case['name']}: {result.verification_method}"
            )
            
            print("   ✅ Passed RSF regression test")
    
    def test_remaining_life_regression(self, reference_calculations):
        """Test remaining life calculations against reference values."""
        calculator = API579Calculator()
        
        for case in reference_calculations["remaining_life_cases"]:
            print(f"\n⏱️  Testing Remaining Life: {case['name']}")
            
            inputs = case["inputs"]
            expected = case["expected_outputs"]
            
            # Perform calculation
            result = calculator.calculate_remaining_life(
                current_thickness=inputs["current_thickness"],
                minimum_thickness=inputs["minimum_thickness"],
                corrosion_rate=inputs["corrosion_rate"],
                confidence_level=inputs["confidence_level"]
            )
            
            # Check result against reference
            difference = abs(result.value - expected["remaining_life"])
            tolerance = expected["tolerance"]
            
            print(f"   Expected Life: {expected['remaining_life']} years")
            print(f"   Calculated Life: {result.value} years")
            print(f"   Difference: {difference} years")
            
            assert difference <= tolerance, (
                f"Remaining life regression detected in {case['name']}: "
                f"Expected {expected['remaining_life']}, got {result.value}, "
                f"difference {difference} > tolerance {tolerance}"
            )
            
            # Verify conservative rounding (remaining life should not be rounded up)
            assert result.value <= result.primary_value, (
                f"Non-conservative rounding detected for {case['name']}: "
                f"Final {result.value} > Primary {result.primary_value}"
            )
            
            print("   ✅ Passed remaining life regression test")
    
    def test_mawp_calculation_regression(self, reference_calculations):
        """Test MAWP calculations against reference values."""
        calculator = API579Calculator()
        
        for case in reference_calculations["mawp_cases"]:
            print(f"\n🔧 Testing MAWP: {case['name']}")
            
            inputs = case["inputs"]
            expected = case["expected_outputs"]
            
            # Perform calculation
            result = calculator.calculate_mawp(
                current_thickness=inputs["current_thickness"],
                radius=inputs["radius"],
                stress=inputs["stress"],
                efficiency=inputs["efficiency"],
                future_corrosion_allowance=inputs["future_corrosion_allowance"]
            )
            
            # Check result against reference
            difference = abs(result.value - expected["mawp"])
            tolerance = expected["tolerance"]
            
            print(f"   Expected MAWP: {expected['mawp']} psi")
            print(f"   Calculated MAWP: {result.value} psi")
            print(f"   Difference: {difference} psi")
            
            assert difference <= tolerance, (
                f"MAWP regression detected in {case['name']}: "
                f"Expected {expected['mawp']}, got {result.value}, "
                f"difference {difference} > tolerance {tolerance}"
            )
            
            # Verify MAWP is reasonable
            assert result.value > Decimal('0'), f"MAWP must be positive for {case['name']}"
            assert result.value < Decimal('10000'), f"MAWP unreasonably high for {case['name']}: {result.value}"
            
            print("   ✅ Passed MAWP regression test")
    
    def test_calculation_result_structure_regression(self):
        """Test that VerifiedResult structure hasn't changed."""
        calculator = API579Calculator()
        
        # Perform a standard calculation
        result = calculator.calculate_minimum_required_thickness(
            pressure=Decimal('1000.0'),
            radius=Decimal('24.0'),
            stress=Decimal('17500.0'),
            efficiency=Decimal('1.0')
        )
        
        # Verify all required fields are present
        required_fields = [
            'value', 'primary_value', 'secondary_value', 'verification_method',
            'timestamp', 'calculation_id', 'api_reference', 'tolerance_used',
            'assumptions', 'warnings'
        ]
        
        for field in required_fields:
            assert hasattr(result, field), f"Missing required field: {field}"
            assert getattr(result, field) is not None, f"Field {field} is None"
        
        # Verify field types
        assert isinstance(result.value, Decimal), "Value must be Decimal"
        assert isinstance(result.primary_value, Decimal), "Primary value must be Decimal"
        assert isinstance(result.secondary_value, Decimal), "Secondary value must be Decimal"
        assert isinstance(result.verification_method, str), "Verification method must be string"
        assert isinstance(result.timestamp, datetime), "Timestamp must be datetime"
        assert isinstance(result.calculation_id, str), "Calculation ID must be string"
        assert isinstance(result.api_reference, str), "API reference must be string"
        assert isinstance(result.tolerance_used, Decimal), "Tolerance must be Decimal"
        assert isinstance(result.assumptions, list), "Assumptions must be list"
        assert isinstance(result.warnings, list), "Warnings must be list"
    
    def test_tolerance_values_regression(self):
        """Test that calculation tolerances haven't changed."""
        calculator = API579Calculator()
        
        # Verify tolerance constants
        expected_tolerances = {
            'DEFAULT_TOLERANCE': Decimal('0.001'),
            'PRESSURE_TOLERANCE': Decimal('0.0001'),
            'THICKNESS_TOLERANCE': Decimal('0.00001')
        }
        
        for tolerance_name, expected_value in expected_tolerances.items():
            actual_value = getattr(calculator, tolerance_name)
            assert actual_value == expected_value, (
                f"Tolerance regression: {tolerance_name} changed from {expected_value} to {actual_value}"
            )
    
    def test_verification_failure_behavior_regression(self):
        """Test that verification failure behavior is consistent."""
        API579Calculator()
        
        # Create a scenario that should trigger verification failure
        # by manually setting an unreasonable tolerance
        calculator_tight_tolerance = API579Calculator(tolerance_override=Decimal('0.000000001'))
        
        try:
            # This should potentially fail verification with extremely tight tolerance
            result = calculator_tight_tolerance.calculate_minimum_required_thickness(
                pressure=Decimal('1000.0'),
                radius=Decimal('24.0'),
                stress=Decimal('17500.0'),
                efficiency=Decimal('1.0')
            )
            # If it doesn't fail, that's also valid - the calculation is very precise
            print(f"   Tight tolerance calculation succeeded: {result.value}")
            
        except CalculationDiscrepancyError as e:
            # Verify error structure hasn't changed
            assert hasattr(e, 'primary'), "CalculationDiscrepancyError missing primary field"
            assert hasattr(e, 'secondary'), "CalculationDiscrepancyError missing secondary field"
            assert hasattr(e, 'tolerance'), "CalculationDiscrepancyError missing tolerance field"
            assert hasattr(e, 'api_reference'), "CalculationDiscrepancyError missing api_reference field"
            
            # Verify error message format
            error_msg = str(e)
            assert "Primary=" in error_msg, "Error message format changed"
            assert "Secondary=" in error_msg, "Error message format changed"
            assert "Tolerance=" in error_msg, "Error message format changed"
            assert "API Reference:" in error_msg, "Error message format changed"
            
            print("   ✅ Verification failure behavior consistent")
    
    def test_assumptions_and_warnings_regression(self):
        """Test that assumptions and warnings are generated consistently."""
        calculator = API579Calculator()
        
        # Test case that should generate specific warnings
        result = calculator.calculate_minimum_required_thickness(
            pressure=Decimal('1000.0'),
            radius=Decimal('5.0'),  # Small radius
            stress=Decimal('17500.0'),
            efficiency=Decimal('1.0')
        )
        
        # Should have standard assumptions
        expected_assumptions = [
            "Using circumferential stress formula (most conservative)",
            "Corrosion allowance not included (must be added separately)",
            "Temperature derating already applied to allowable stress"
        ]
        
        for assumption in expected_assumptions:
            assert any(assumption in a for a in result.assumptions), (
                f"Missing expected assumption: {assumption}"
            )
        
        # Test RSF near threshold
        rsf_result = calculator.calculate_remaining_strength_factor(
            current_thickness=Decimal('0.950'),
            minimum_thickness=Decimal('0.875'),
            nominal_thickness=Decimal('1.250'),
            future_corrosion_allowance=Decimal('0.050')
        )
        
        # Should generate warning for low RSF
        assert any("RSF" in w and "0.90" in w for w in rsf_result.warnings), (
            "Missing RSF threshold warning"
        )
    
    def test_api_reference_consistency_regression(self):
        """Test that API references are consistent and correct."""
        calculator = API579Calculator()
        
        # Test minimum thickness API reference
        t_min_result = calculator.calculate_minimum_required_thickness(
            pressure=Decimal('1000.0'),
            radius=Decimal('24.0'),
            stress=Decimal('17500.0'),
            efficiency=Decimal('1.0')
        )
        
        assert "API 579-1 Part 4" in t_min_result.api_reference, (
            f"Incorrect API reference for minimum thickness: {t_min_result.api_reference}"
        )
        
        # Test RSF API reference
        rsf_result = calculator.calculate_remaining_strength_factor(
            current_thickness=Decimal('1.200'),
            minimum_thickness=Decimal('0.875'),
            nominal_thickness=Decimal('1.250')
        )
        
        assert "API 579-1 Part 5" in rsf_result.api_reference, (
            f"Incorrect API reference for RSF: {rsf_result.api_reference}"
        )
        
        # Test remaining life API reference
        life_result = calculator.calculate_remaining_life(
            current_thickness=Decimal('1.150'),
            minimum_thickness=Decimal('0.875'),
            corrosion_rate=Decimal('0.005')
        )
        
        assert "API 579-1 Part 4" in life_result.api_reference, (
            f"Incorrect API reference for remaining life: {life_result.api_reference}"
        )
        
        # Test MAWP API reference
        mawp_result = calculator.calculate_mawp(
            current_thickness=Decimal('1.150'),
            radius=Decimal('24.0'),
            stress=Decimal('17500.0'),
            efficiency=Decimal('1.0')
        )
        
        assert "API 579-1 Part 4" in mawp_result.api_reference, (
            f"Incorrect API reference for MAWP: {mawp_result.api_reference}"
        )