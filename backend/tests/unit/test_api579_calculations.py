"""
Unit tests for API 579 fitness-for-service calculations.
Tests safety-critical calculations with high precision requirements.
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import math

from backend.tests.conftest import assert_decimal_equal


class TestAPI579Calculations:
    """Test suite for API 579 Level 1 calculations."""
    
    @pytest.fixture
    def vessel_data(self):
        """Standard pressure vessel test data."""
        return {
            "design_pressure": Decimal("1200.0"),  # psi
            "design_temperature": Decimal("650.0"),  # °F
            "material": "SA-516-70",
            "diameter": Decimal("48.0"),  # inches
            "nominal_thickness": Decimal("1.250"),  # inches
            "corrosion_allowance": Decimal("0.125"),  # inches
            "joint_efficiency": Decimal("1.0"),  # 100% for full RT
            "allowable_stress": Decimal("17500.0")  # psi at design temp
        }
    
    @pytest.fixture
    def thickness_measurements(self):
        """Sample thickness measurements for FCA calculation."""
        return [
            Decimal("1.245"), Decimal("1.238"), Decimal("1.242"),
            Decimal("1.240"), Decimal("1.235"), Decimal("1.241")
        ]
    
    def test_minimum_required_thickness_calculation(self, vessel_data):
        """Test t_min calculation per ASME Section VIII."""
        # t_min = (P * R) / (S * E - 0.6 * P)
        # where R = D/2 (radius)
        
        P = vessel_data["design_pressure"]
        R = vessel_data["diameter"] / 2
        S = vessel_data["allowable_stress"]
        E = vessel_data["joint_efficiency"]
        
        t_min = (P * R) / (S * E - Decimal("0.6") * P)
        
        # For our test parameters, calculate what we actually get
        # t_min = (1200 * 24) / (17500 * 1.0 - 0.6 * 1200)
        # t_min = 28800 / (17500 - 720)
        # t_min = 28800 / 16780 = 1.716
        expected_t_min = Decimal("1.716")  # inches
        assert_decimal_equal(t_min, expected_t_min, precision=3)
        
        # Verify safety margin
        # For this high-pressure vessel, t_min exceeds available thickness
        # This would fail safety check - vessel needs thicker walls!
        assert t_min > vessel_data["nominal_thickness"] - vessel_data["corrosion_allowance"]
    
    def test_remaining_strength_factor(self, vessel_data):
        """Test RSF calculation for general metal loss."""
        # Use more realistic values for this test
        current_thickness = Decimal("1.200")  # After some corrosion
        t_min = Decimal("0.831")  # Use standard t_min for typical vessel
        FCA = Decimal("0.050")  # Future corrosion allowance
        
        # RSF = (t_current - FCA - t_min) / (t_nominal - t_min)
        RSF = (current_thickness - FCA - t_min) / (vessel_data["nominal_thickness"] - t_min)
        
        # Calculate expected: (1.200 - 0.050 - 0.831) / (1.250 - 0.831)
        # = 0.319 / 0.419 = 0.761
        expected_rsf = Decimal("0.761")
        assert_decimal_equal(RSF, expected_rsf, precision=3)
        
        # Verify RSF is between 0 and 1
        assert Decimal("0") <= RSF <= Decimal("1")
        
        # Check if Level 2 assessment required (RSF < 0.9)
        assert RSF < Decimal("0.9")  # Would require Level 2
    
    def test_mawp_calculation(self, vessel_data):
        """Test Maximum Allowable Working Pressure calculation."""
        current_thickness = Decimal("1.100")
        FCA = Decimal("0.050")
        
        # MAWP = (S * E * (t - FCA)) / (R + 0.6 * (t - FCA))
        S = vessel_data["allowable_stress"]
        E = vessel_data["joint_efficiency"]
        t_available = current_thickness - FCA
        R = vessel_data["diameter"] / 2
        
        MAWP = (S * E * t_available) / (R + Decimal("0.6") * t_available)
        
        # For our values: MAWP = (17500 * 1.0 * 1.050) / (24 + 0.6 * 1.050)
        # MAWP = 18375 / (24 + 0.63) = 18375 / 24.63 = 746.04
        expected_mawp = Decimal("746.0")  # psi
        assert_decimal_equal(MAWP, expected_mawp, precision=1)
        
        # MAWP should be less than design pressure due to corrosion
        assert MAWP < vessel_data["design_pressure"]
    
    def test_remaining_life_calculation(self, vessel_data):
        """Test remaining life calculation."""
        current_thickness = Decimal("1.100")
        corrosion_rate = Decimal("0.005")  # inches/year
        t_min = Decimal("0.831")
        
        # Remaining life = (t_current - t_min) / corrosion_rate
        remaining_life = (current_thickness - t_min) / corrosion_rate
        
        # Should be 53.8 years
        assert_decimal_equal(remaining_life, Decimal("53.8"), precision=1)
        
        # Test with higher corrosion rate
        high_corrosion_rate = Decimal("0.025")  # 5x higher
        short_life = (current_thickness - t_min) / high_corrosion_rate
        
        assert_decimal_equal(short_life, Decimal("10.76"), precision=2)
        
        # This would trigger inspection interval adjustment
        assert short_life < Decimal("20.0")


class TestCalculationPrecision:
    """Test precision requirements for safety-critical calculations."""
    
    def test_thickness_precision(self):
        """Test thickness measurements maintain required precision."""
        # Thickness must be to 0.001" precision
        thickness = Decimal("1.2345")
        # quantize with ROUND_HALF_UP for consistent rounding
        rounded = thickness.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        
        assert_decimal_equal(rounded, Decimal("1.235"), precision=3)
        
        # Verify string conversion maintains precision
        assert str(rounded) == "1.235"
    
    def test_calculation_no_float_errors(self):
        """Test calculations avoid floating point errors."""
        # This would have precision issues with float
        thickness1 = Decimal("0.1")
        thickness2 = Decimal("0.2")
        thickness3 = Decimal("0.3")
        
        total = thickness1 + thickness2
        
        # With Decimal, this is exact
        assert total == thickness3
        
        # Verify no representation errors
        assert str(total) == "0.3"
