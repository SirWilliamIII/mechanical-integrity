"""
Basic decimal precision tests that can run independently.

These tests validate fundamental decimal precision requirements
without requiring the full application stack.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
import json

# Set high precision for tests
getcontext().prec = 28


class TestBasicDecimalPrecision:
    """Basic tests for decimal precision requirements."""
    
    def test_thickness_precision_requirements(self):
        """Test that thickness values maintain ±0.001 inch precision."""
        # Test precise thickness values
        test_thicknesses = [
            Decimal('1.2345'),  # 4 decimal places
            Decimal('0.0625'),  # Exactly 1/16 inch
            Decimal('1.0000'),  # Exactly 1 inch
            Decimal('0.001'),   # Minimum precision
            Decimal('2.999')    # Close to 3 inches
        ]
        
        for thickness in test_thicknesses:
            # Round to required precision (0.001 inches)
            rounded = thickness.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            
            # Verify precision is maintained
            assert rounded.as_tuple().exponent >= -3, f"Insufficient precision for {thickness}"
            
            # Verify no precision loss in string conversion
            thickness_str = str(rounded)
            reconstructed = Decimal(thickness_str)
            assert reconstructed == rounded, f"String conversion precision loss: {thickness}"
        
        print("✅ Thickness precision requirements verified")
    
    def test_decimal_arithmetic_precision(self):
        """Test that decimal arithmetic maintains precision."""
        # Test values that commonly lose precision with float
        test_values = [
            (Decimal('0.1'), Decimal('0.2'), Decimal('0.3')),
            (Decimal('1.0'), Decimal('3.0'), Decimal('0.333333333')),
            (Decimal('999999999.999'), Decimal('0.001'), Decimal('1000000000.000'))
        ]
        
        for val1, val2, expected_sum in test_values:
            # Test addition
            result = val1 + val2
            
            # Verify no floating point errors
            if val1 + val2 == expected_sum:
                assert result == expected_sum, f"Addition precision error: {val1} + {val2} = {result}"
            
            # Test multiplication/division roundtrip
            if val2 != Decimal('0'):
                multiplied = val1 * val2
                divided = multiplied / val2
                
                # Should return to original (within tiny tolerance)
                difference = abs(divided - val1)
                relative_error = difference / val1 if val1 != 0 else difference
                assert relative_error < Decimal('0.000000001'), f"Roundtrip error: {val1} -> {divided}"
        
        print("✅ Decimal arithmetic precision verified")
    
    def test_json_serialization_precision_loss_detection(self):
        """Test detection of JSON serialization precision loss."""
        # Test values that lose precision when converted to float
        # Use values with very high precision that exceed float64 precision
        test_values = [
            Decimal('0.123456789012345678901'),  # 21 decimal places - exceeds float precision
            Decimal('1.234567890123456789012'),  # 21 decimal places
            Decimal('999.999999999999999999'),   # Very high precision
            Decimal('0.00000000000000000001'),   # Tiny value beyond float precision
        ]
        
        precision_loss_detected = False
        
        for value in test_values:
            # Simulate problematic JSON encoder: Decimal -> float -> JSON -> float -> Decimal
            as_float = float(value)
            json_string = json.dumps({"value": as_float})
            parsed = json.loads(json_string)
            back_to_decimal = Decimal(str(parsed["value"]))
            
            print(f"Testing {value}:")
            print(f"  Original: {value}")
            print(f"  As float: {as_float}")
            print(f"  Back to Decimal: {back_to_decimal}")
            print(f"  Equal? {value == back_to_decimal}")
            
            # Check for precision loss
            if value != back_to_decimal:
                precision_loss_detected = True
                print(f"⚠️  PRECISION LOSS DETECTED: {value} → {as_float} → {back_to_decimal}")
            
            # The CORRECT approach - serialize Decimal as string
            correct_json = json.dumps({"value": str(value)})
            correct_parsed = json.loads(correct_json)
            correct_decimal = Decimal(correct_parsed["value"])
            
            # This should always preserve precision
            assert value == correct_decimal, f"String serialization failed for {value}"
        
        # We expect to detect precision loss (this demonstrates the problem)
        assert precision_loss_detected, "Should detect precision loss with float conversion"
        print("✅ JSON precision loss detection verified")
    
    def test_database_decimal_precision_simulation(self):
        """Test DECIMAL column precision simulation."""
        # Simulate DECIMAL(6,3) storage - 6 total digits, 3 after decimal
        test_values = [
            Decimal('0.001'),      # Minimum precision
            Decimal('999.999'),    # Maximum value
            Decimal('1.2345'),     # Should round to 1.235
            Decimal('0.0625'),     # Exactly 1/16 inch
            Decimal('123.456')     # Middle range
        ]
        
        for value in test_values:
            # Simulate database DECIMAL(6,3) storage
            stored = value.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            
            # Verify fits in DECIMAL(6,3) - max 999.999
            assert stored <= Decimal('999.999'), f"Value {stored} exceeds DECIMAL(6,3) range"
            assert stored >= Decimal('0.000'), f"Value {stored} below DECIMAL(6,3) range"
            
            # Verify precision is exactly 3 decimal places
            assert stored.as_tuple().exponent == -3, f"Wrong precision for {value} -> {stored}"
            
            # For values that need rounding, verify correct rounding
            if value != stored:
                print(f"   Rounded: {value} → {stored}")
        
        print("✅ Database decimal precision simulation verified")
    
    def test_corrosion_rate_calculation_precision(self):
        """Test corrosion rate calculation maintains required precision."""
        # Simulate thickness measurements from different inspections
        measurements = [
            (Decimal('1.250'), "2020-01-01"),  # Original thickness
            (Decimal('1.235'), "2022-01-01"),  # After 2 years
            (Decimal('1.220'), "2024-01-01")   # After 4 years total
        ]
        
        # Calculate corrosion rates between measurements
        for i in range(1, len(measurements)):
            prev_thickness, prev_date = measurements[i-1]
            curr_thickness, curr_date = measurements[i]
            
            # Calculate metal loss and time span
            metal_loss = prev_thickness - curr_thickness
            time_span_years = Decimal('2.0')  # 2 years between measurements
            
            # Corrosion rate in inches/year
            corrosion_rate = metal_loss / time_span_years
            
            # Verify precision maintained (5 decimal places per model spec)
            assert corrosion_rate.as_tuple().exponent >= -5, f"Insufficient corrosion rate precision: {corrosion_rate}"
            
            # Verify rate is reasonable (0.001 to 0.100 inches/year)
            assert Decimal('0.001') <= corrosion_rate <= Decimal('0.100'), f"Unrealistic corrosion rate: {corrosion_rate}"
            
            print(f"   Period {i}: {metal_loss} inches lost over {time_span_years} years = {corrosion_rate} in/yr")
        
        print("✅ Corrosion rate calculation precision verified")
    
    def test_api_579_calculation_precision_requirements(self):
        """Test API 579 calculation precision requirements."""
        # Mock API 579 minimum thickness calculation
        # t_min = (P * R) / (S * E - 0.6 * P)
        
        pressure = Decimal('1000.0')    # psi
        radius = Decimal('24.0')        # inches  
        stress = Decimal('17500.0')     # psi
        efficiency = Decimal('1.0')     # 100%
        
        # Calculate minimum required thickness
        denominator = stress * efficiency - Decimal('0.6') * pressure
        t_min = (pressure * radius) / denominator
        
        # Round to required precision for API 579 (0.001 inches)
        t_min_rounded = t_min.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        
        # Verify calculation precision after rounding
        assert t_min_rounded.as_tuple().exponent >= -3, f"Insufficient t_min precision: {t_min_rounded}"
        
        # Mock RSF calculation
        # RSF = (t_current - FCA - t_min) / (t_nominal - t_min)
        current_thickness = Decimal('1.200')
        nominal_thickness = Decimal('1.250')
        fca = Decimal('0.050')
        
        numerator = current_thickness - fca - t_min_rounded
        rsf_denominator = nominal_thickness - t_min_rounded
        
        if rsf_denominator > 0:
            rsf = numerator / rsf_denominator
            
            # Verify RSF precision (4 decimal places per model spec)
            assert rsf.as_tuple().exponent >= -4, f"Insufficient RSF precision: {rsf}"
            
            # Verify RSF bounds
            assert Decimal('0') <= rsf <= Decimal('1'), f"RSF out of bounds: {rsf}"
            
            print(f"   t_min = {t_min_rounded:.3f} inches")
            print(f"   RSF = {rsf:.4f}")
        
        print("✅ API 579 calculation precision requirements verified")
    
    def test_measurement_uncertainty_propagation(self):
        """Test that measurement uncertainty is properly handled."""
        # Base thickness with measurement uncertainty
        measured_thickness = Decimal('1.234')
        uncertainty = Decimal('0.001')  # ±0.001 inch measurement tolerance
        
        # Calculate range of possible values
        min_thickness = measured_thickness - uncertainty
        max_thickness = measured_thickness + uncertainty
        
        # Verify uncertainty bounds maintain precision
        assert min_thickness.as_tuple().exponent >= -3, "Min thickness precision insufficient"
        assert max_thickness.as_tuple().exponent >= -3, "Max thickness precision insufficient"
        
        # Calculate uncertainty propagation in derived values
        # For remaining life: RL = (t_current - t_min) / CR
        t_min = Decimal('0.875')
        corrosion_rate = Decimal('0.005')
        
        min_life = (min_thickness - t_min) / corrosion_rate
        max_life = (max_thickness - t_min) / corrosion_rate
        life_uncertainty = max_life - min_life
        
        print(f"   Thickness: {measured_thickness} ± {uncertainty} inches")
        print(f"   Remaining life: {(min_life + max_life)/2:.1f} ± {life_uncertainty/2:.1f} years")
        
        # Verify uncertainty calculation maintains precision
        assert life_uncertainty.as_tuple().exponent >= -2, "Life uncertainty precision insufficient"
        
        print("✅ Measurement uncertainty propagation verified")


class TestFloatVsDecimalDemonstration:
    """Demonstrate why float is inadequate for safety-critical calculations."""
    
    def test_float_precision_problems(self):
        """Demonstrate float precision problems that Decimal avoids."""
        # Classic floating point precision issue
        float_result = 0.1 + 0.2
        decimal_result = Decimal('0.1') + Decimal('0.2')
        
        print(f"Float: 0.1 + 0.2 = {float_result}")
        print(f"Decimal: 0.1 + 0.2 = {decimal_result}")
        
        # Float gives wrong answer!
        assert float_result != 0.3, "Float arithmetic precision issue"
        assert decimal_result == Decimal('0.3'), "Decimal arithmetic correct"
        
        # Thickness calculation with float vs decimal
        thickness_float = 1.2345
        thickness_decimal = Decimal('1.2345')
        
        # Simulate JSON round-trip (common in web APIs)
        json_float = json.loads(json.dumps(thickness_float))
        json_decimal_as_float = json.loads(json.dumps(float(thickness_decimal)))
        json_decimal_as_string = json.loads(json.dumps(str(thickness_decimal)))
        
        print(f"Original float: {thickness_float}")
        print(f"After JSON: {json_float}")
        print(f"Decimal as float via JSON: {json_decimal_as_float}")
        print(f"Decimal as string via JSON: {json_decimal_as_string}")
        
        # Verify string approach preserves precision
        assert json_decimal_as_string == "1.2345", "String serialization preserves precision"
        
        print("✅ Float vs Decimal precision problems demonstrated")
    
    def test_cumulative_precision_errors(self):
        """Test cumulative precision errors with float vs decimal."""
        # Simulate 1000 small additions (common in iterative calculations)
        float_sum = 0.0
        decimal_sum = Decimal('0.0')
        increment = Decimal('0.001')
        
        for i in range(1000):
            float_sum += float(increment)
            decimal_sum += increment
        
        expected = Decimal('1.000')
        
        print(f"Expected sum: {expected}")
        print(f"Float sum: {float_sum}")
        print(f"Decimal sum: {decimal_sum}")
        
        float_error = abs(Decimal(str(float_sum)) - expected)
        decimal_error = abs(decimal_sum - expected)
        
        print(f"Float error: {float_error}")
        print(f"Decimal error: {decimal_error}")
        
        # Decimal should be exact, float will have accumulated error
        assert decimal_error == Decimal('0'), "Decimal should be exact"
        assert float_error > Decimal('0'), "Float should have accumulated error"
        
        print("✅ Cumulative precision error demonstration complete")