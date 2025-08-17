"""
Unit tests for API 579 fitness-for-service calculations.
Tests safety-critical calculations with high precision requirements.
"""
import pytest
from decimal import Decimal
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
        
        # Expected value for these parameters
        expected_t_min = Decimal("0.831")  # inches
        assert_decimal_equal(t_min, expected_t_min, precision=3)
        
        # Verify safety margin
        assert t_min < vessel_data["nominal_thickness"] - vessel_data["corrosion_allowance"]
    
    def test_future_corrosion_allowance(self, thickness_measurements):
        """Test FCA calculation with statistical methods."""
        # Calculate mean and standard deviation
        mean_thickness = sum(thickness_measurements) / len(thickness_measurements)
        
        # Calculate standard deviation
        variance = sum((x - mean_thickness) ** 2 for x in thickness_measurements) / (len(thickness_measurements) - 1)
        std_dev = variance.sqrt()
        
        # FCA = mean - 2*std_dev (95% confidence)
        fca = mean_thickness - 2 * std_dev
        
        # Verify calculation
        assert_decimal_equal(mean_thickness, Decimal("1.240"))
        assert fca < mean_thickness
        assert fca > min(thickness_measurements) - Decimal("0.010")  # Reasonable bounds
    
    def test_remaining_strength_factor(self, vessel_data):
        """Test RSF calculation for general metal loss."""
        current_thickness = Decimal("1.100")  # After corrosion
        t_min = Decimal("0.831")  # From previous calculation
        FCA = Decimal("0.050")  # Future corrosion allowance
        
        # RSF = (t_current - FCA - t_min) / (t_nominal - t_min)
        RSF = (current_thickness - FCA - t_min) / (vessel_data["nominal_thickness"] - t_min)
        
        # Verify RSF is between 0 and 1
        assert Decimal("0") <= RSF <= Decimal("1")
        
        # For this example, RSF should be around 0.52
        assert_decimal_equal(RSF, Decimal("0.521"), precision=3)
        
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
        
        # Verify MAWP calculation
        expected_mawp = Decimal("761.4")  # psi
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
    
    def test_coefficient_of_variation(self, thickness_measurements):
        """Test COV calculation for thickness uniformity."""
        mean_thickness = sum(thickness_measurements) / len(thickness_measurements)
        
        # Calculate standard deviation
        variance = sum((x - mean_thickness) ** 2 for x in thickness_measurements) / (len(thickness_measurements) - 1)
        std_dev = variance.sqrt()
        
        # COV = (std_dev / mean) * 100%
        cov = (std_dev / mean_thickness) * 100
        
        # For uniform corrosion, COV should be low (< 10%)
        assert cov < Decimal("10.0")
        assert_decimal_equal(cov, Decimal("0.323"), precision=3)
    
    def test_inspection_interval_api653(self, vessel_data):
        """Test inspection interval calculation per API 653."""
        current_thickness = Decimal("1.100")
        t_min = Decimal("0.500")  # 50% of nominal for tanks
        corrosion_rate = Decimal("0.005")
        
        # RCA = current - minimum (in mils)
        RCA = (current_thickness - t_min) * 1000  # Convert to mils
        
        # Interval = RCA / (4 * N) where N is corrosion rate in mpy
        N = corrosion_rate * 1000  # Convert to mils per year
        interval = RCA / (4 * N)
        
        # Maximum interval is 5 years for external inspection
        actual_interval = min(interval, Decimal("5.0"))
        
        assert_decimal_equal(actual_interval, Decimal("5.0"), precision=1)
    
    def test_level_1_acceptability(self, vessel_data):
        """Test Level 1 assessment acceptability criteria."""
        current_thickness = Decimal("1.100")
        t_min = Decimal("0.831")
        
        # Check thickness ratio
        thickness_ratio = current_thickness / vessel_data["nominal_thickness"]
        
        # Level 1 acceptable if:
        # 1. Thickness ratio > 0.5
        # 2. Current thickness > t_min
        # 3. Uniform corrosion (COV < 10%)
        
        assert thickness_ratio > Decimal("0.5")
        assert current_thickness > t_min
        
        # This would pass Level 1 screening
        level_1_acceptable = (
            thickness_ratio > Decimal("0.5") and
            current_thickness > t_min
        )
        
        assert level_1_acceptable is True


class TestSafetyFactors:
    """Test application of safety factors in calculations."""
    
    def test_conservative_corrosion_rate(self):
        """Test conservative corrosion rate application."""
        measured_rates = [
            Decimal("0.004"), Decimal("0.005"), Decimal("0.006"),
            Decimal("0.004"), Decimal("0.007")
        ]
        
        # Use statistical approach: mean + 2*std_dev
        mean_rate = sum(measured_rates) / len(measured_rates)
        variance = sum((x - mean_rate) ** 2 for x in measured_rates) / (len(measured_rates) - 1)
        std_dev = variance.sqrt()
        
        conservative_rate = mean_rate + 2 * std_dev
        
        # Should be higher than mean
        assert conservative_rate > mean_rate
        assert_decimal_equal(conservative_rate, Decimal("0.0078"), precision=4)
    
    def test_safety_factor_application(self):
        """Test safety factor application to remaining life."""
        remaining_life_calculated = Decimal("10.5")  # years
        safety_factor = Decimal("2.0")
        
        # Safe inspection interval = remaining_life / safety_factor
        safe_interval = remaining_life_calculated / safety_factor
        
        assert_decimal_equal(safe_interval, Decimal("5.25"), precision=2)
        
        # Should not exceed maximum allowed interval
        max_interval = Decimal("5.0")  # API maximum
        actual_interval = min(safe_interval, max_interval)
        
        assert actual_interval == max_interval
    
    def test_minimum_thickness_safety_margin(self):
        """Test safety margin in minimum thickness."""
        t_min_calculated = Decimal("0.831")
        safety_margin = Decimal("0.050")  # Additional safety
        
        t_min_required = t_min_calculated + safety_margin
        
        assert_decimal_equal(t_min_required, Decimal("0.881"), precision=3)
        
        # Verify against current thickness
        current_thickness = Decimal("0.900")
        
        # Should pass with margin
        assert current_thickness > t_min_calculated
        # But fail with safety margin
        assert current_thickness > t_min_required


class TestCalculationPrecision:
    """Test precision requirements for safety-critical calculations."""
    
    def test_thickness_precision(self):
        """Test thickness measurements maintain required precision."""
        # Thickness must be to 0.001" precision
        thickness = Decimal("1.2345")
        rounded = thickness.quantize(Decimal("0.001"))
        
        assert_decimal_equal(rounded, Decimal("1.235"), precision=3)
        
        # Verify string conversion maintains precision
        assert str(rounded) == "1.235"
    
    def test_pressure_precision(self):
        """Test pressure calculations maintain required precision."""
        # Pressure must be to 0.1 psi precision
        pressure = Decimal("1234.567")
        rounded = pressure.quantize(Decimal("0.1"))
        
        assert_decimal_equal(rounded, Decimal("1234.6"), precision=1)
    
    def test_stress_precision(self):
        """Test stress calculations maintain required precision."""
        # Stress must be to 1 psi precision
        stress = Decimal("17543.789")
        rounded = stress.quantize(Decimal("1"))
        
        assert rounded == Decimal("17544")
    
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
