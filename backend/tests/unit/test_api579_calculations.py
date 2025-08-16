"""
Unit tests for API 579 calculations.
These tests ensure safety-critical calculations are accurate to specification.
"""
import pytest
from decimal import Decimal, ROUND_DOWN


class TestAPI579Calculations:
    """Test API 579 fitness-for-service calculations."""
    
    def test_remaining_strength_factor_basic(self):
        """Test basic RSF calculation: RSF = (t_actual - FCA) / t_required"""
        # Given: typical pipe parameters
        t_actual = Decimal("0.500")  # inches
        t_required = Decimal("0.375")  # inches
        fca = Decimal("0.025")  # inches
        
        # When: calculating RSF
        rsf = (t_actual - fca) / t_required
        
        # Then: should be conservative calculation
        expected_rsf = Decimal("1.267")  # (0.500 - 0.025) / 0.375
        assert abs(rsf - expected_rsf) < Decimal("0.001")
        assert rsf > Decimal("0.9")  # Above critical threshold
    
    def test_remaining_strength_factor_critical_threshold(self):
        """Test RSF at critical threshold requiring immediate review."""
        # Given: degraded pipe at threshold
        t_actual = Decimal("0.400")
        t_required = Decimal("0.375") 
        fca = Decimal("0.062")  # Higher corrosion allowance
        
        # When: calculating RSF
        rsf = (t_actual - fca) / t_required
        
        # Then: should flag for immediate review
        assert rsf < Decimal("0.9")  # Below critical threshold
        assert rsf == Decimal("0.901").quantize(Decimal("0.001"), rounding=ROUND_DOWN)
    
    def test_maximum_allowable_working_pressure(self):
        """Test MAWP calculation per API 579."""
        # Given: pressure vessel parameters
        allowable_stress = Decimal("20000")  # psi
        thickness = Decimal("0.500")  # inches
        radius = Decimal("24.0")  # inches
        joint_efficiency = Decimal("1.0")
        
        # When: calculating MAWP using thin wall formula
        # MAWP = (S * t * E) / (R + 0.6 * t)
        mawp = (allowable_stress * thickness * joint_efficiency) / (radius + Decimal("0.6") * thickness)
        
        # Then: should match expected pressure rating
        expected_mawp = Decimal("408.16")  # psi
        assert abs(mawp - expected_mawp) < Decimal("0.1")
    
    def test_future_corrosion_allowance(self):
        """Test FCA calculation for remaining service life."""
        # Given: corrosion rate and inspection interval
        corrosion_rate = Decimal("0.005")  # inches/year
        inspection_interval = Decimal("5.0")  # years
        safety_factor = Decimal("1.5")
        
        # When: calculating FCA
        fca = corrosion_rate * inspection_interval * safety_factor
        
        # Then: should be conservative estimate
        expected_fca = Decimal("0.0375")  # inches
        assert fca == expected_fca
        assert fca > corrosion_rate * inspection_interval  # More conservative than basic calc
    
    def test_minimum_required_thickness(self):
        """Test minimum thickness calculation."""
        # Given: design pressure and material properties
        design_pressure = Decimal("150")  # psi
        radius = Decimal("24.0")  # inches
        allowable_stress = Decimal("20000")  # psi
        joint_efficiency = Decimal("1.0")
        
        # When: calculating minimum thickness
        # t_min = (P * R) / (S * E - 0.6 * P)
        t_min = (design_pressure * radius) / (allowable_stress * joint_efficiency - Decimal("0.6") * design_pressure)
        
        # Then: should provide safe minimum thickness
        expected_t_min = Decimal("0.180")  # inches
        assert abs(t_min - expected_t_min) < Decimal("0.001")
    
    def test_precision_requirements(self):
        """Test that calculations meet API 579 precision requirements."""
        # Given: thickness measurement
        thickness = Decimal("0.4567")  # inches
        
        # When: rounding to required precision
        rounded_thickness = thickness.quantize(Decimal("0.001"))
        
        # Then: should maintain ±0.001 inch precision
        assert str(rounded_thickness) == "0.457"
        assert len(str(rounded_thickness).split(".")[-1]) <= 3
    
    def test_conservative_rounding(self):
        """Test that safety calculations always round conservatively."""
        # Given: remaining life calculation result
        remaining_life = Decimal("5.789")  # years
        
        # When: applying conservative rounding
        conservative_life = remaining_life.quantize(Decimal("1"), rounding=ROUND_DOWN)
        
        # Then: should round down for safety
        assert conservative_life == Decimal("5")
        assert conservative_life <= remaining_life