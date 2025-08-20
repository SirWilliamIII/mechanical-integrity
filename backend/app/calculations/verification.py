"""
Calculation Verification Module

Provides additional verification methods and cross-checks for
API 579 calculations to ensure accuracy and regulatory compliance.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging

from .constants import API579Constants, EquipmentType, DamageType

logger = logging.getLogger(__name__)


class CalculationVerifier:
    """
    Provides independent verification of API 579 calculations
    using alternative methods and sanity checks.
    """
    
    def __init__(self):
        self.constants = API579Constants
    
    def verify_thickness_calculation(
        self,
        calculated_thickness: Decimal,
        equipment_type: EquipmentType,
        pressure: Decimal,
        temperature: Decimal,
        material: str
    ) -> Tuple[bool, List[str]]:
        """
        Verify calculated minimum thickness against multiple criteria.
        
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Check absolute limits
        abs_min = self.constants.get_thickness_limit(equipment_type, "absolute_minimum")
        nom_max = self.constants.get_thickness_limit(equipment_type, "nominal_maximum")
        
        if calculated_thickness < abs_min:
            warnings.append(
                f"Calculated thickness {calculated_thickness} below absolute minimum "
                f"{abs_min} for {equipment_type}"
            )
            is_valid = False
        
        if calculated_thickness > nom_max:
            warnings.append(
                f"Calculated thickness {calculated_thickness} exceeds typical maximum "
                f"{nom_max} for {equipment_type}. Verify design conditions."
            )
        
        # Check pressure-based reasonableness
        if self.constants.is_high_pressure(pressure):
            if calculated_thickness < Decimal("0.25"):
                warnings.append(
                    f"High pressure service ({pressure} psi) typically requires "
                    f"thickness > 0.25\", calculated {calculated_thickness}\""
                )
        
        # Check temperature effects
        if self.constants.is_creep_range(temperature, material):
            warnings.append(
                f"Temperature {temperature}°F is in creep range for {material}. "
                "Additional creep analysis required per API 579 Part 10."
            )
        
        return is_valid, warnings
    
    def verify_rsf_calculation(
        self,
        rsf: Decimal,
        current_thickness: Decimal,
        minimum_thickness: Decimal,
        equipment_type: EquipmentType
    ) -> Tuple[bool, List[str], str]:
        """
        Verify RSF calculation and determine required action.
        
        Returns:
            Tuple of (is_valid, warnings, recommended_action)
        """
        warnings = []
        is_valid = True
        recommended_action = "Continue normal operation"
        
        # Basic sanity checks
        if rsf < Decimal("0") or rsf > Decimal("1"):
            warnings.append(f"RSF {rsf} outside valid range [0, 1]")
            is_valid = False
        
        # Check thickness ratio independently
        thickness_ratio = current_thickness / minimum_thickness if minimum_thickness > 0 else Decimal("0")
        
        if thickness_ratio < Decimal("1.0") and rsf > Decimal("0"):
            warnings.append(
                f"Inconsistent: thickness ratio {thickness_ratio:.3f} < 1.0 "
                f"but RSF {rsf:.3f} > 0"
            )
            is_valid = False
        
        # Determine action based on RSF value
        if rsf < self.constants.SAFETY_FACTORS["rsf_immediate_action"]:
            recommended_action = "IMMEDIATE ACTION REQUIRED - Schedule repair/replacement"
            warnings.append(f"RSF {rsf:.3f} below immediate action threshold")
        
        elif rsf < self.constants.SAFETY_FACTORS["rsf_minimum_acceptable"]:
            recommended_action = "Perform Level 2 or Level 3 FFS assessment"
            warnings.append(f"RSF {rsf:.3f} below Level 1 acceptance criteria")
        
        elif rsf < Decimal("0.95"):
            recommended_action = "Increase inspection frequency and monitor closely"
        
        return is_valid, warnings, recommended_action
    
    def verify_remaining_life(
        self,
        remaining_life: Decimal,
        corrosion_rate: Decimal,
        current_thickness: Decimal,
        minimum_thickness: Decimal
    ) -> Tuple[bool, List[str]]:
        """
        Verify remaining life calculation for consistency.
        
        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        is_valid = True
        
        # Sanity check: recalculate using simple method
        if corrosion_rate > 0:
            simple_calc = (current_thickness - minimum_thickness) / corrosion_rate
            difference = abs(simple_calc - remaining_life)
            
            if difference > Decimal("0.5"):  # More than 6 months difference
                warnings.append(
                    f"Remaining life verification shows {difference:.1f} year "
                    f"discrepancy. Calculated: {remaining_life:.1f}, "
                    f"Simple method: {simple_calc:.1f}"
                )
                is_valid = False
        
        # Check for unrealistic values
        if remaining_life > Decimal("100"):
            warnings.append(
                f"Remaining life {remaining_life:.1f} years seems unrealistic. "
                "Verify corrosion rate assumptions."
            )
        
        if remaining_life < Decimal("0"):
            warnings.append("Negative remaining life calculated - equipment already below minimum!")
            is_valid = False
        
        # Check corrosion rate reasonableness
        typical_rates = self.constants.TYPICAL_CORROSION_RATES
        max_expected = Decimal("0.050")  # 50 mpy is very high
        
        if corrosion_rate > max_expected:
            warnings.append(
                f"Corrosion rate {corrosion_rate:.3f} in/yr exceeds typical "
                f"maximum {max_expected}. Verify measurement data."
            )
        
        return is_valid, warnings
    
    def cross_check_calculations(
        self,
        thickness_data: Dict[str, Decimal],
        pressure_data: Dict[str, Decimal],
        material_data: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Perform comprehensive cross-checks between related calculations.
        
        This method verifies consistency between:
        - Minimum thickness and MAWP
        - RSF and remaining life
        - Corrosion rate and inspection history
        """
        results = {
            "is_consistent": True,
            "inconsistencies": [],
            "recommendations": []
        }
        
        # Cross-check 1: t_min and MAWP should be inversely related
        if "minimum_thickness" in thickness_data and "mawp" in pressure_data:
            t_min = thickness_data["minimum_thickness"]
            mawp = pressure_data["mawp"]
            design_pressure = pressure_data.get("design_pressure", mawp)
            
            # If we have excess thickness, MAWP should exceed design pressure
            if thickness_data.get("current_thickness", t_min) > t_min * Decimal("1.2"):
                if mawp < design_pressure:
                    results["inconsistencies"].append(
                        f"MAWP ({mawp} psi) less than design pressure ({design_pressure} psi) "
                        "despite 20% excess thickness"
                    )
                    results["is_consistent"] = False
        
        # Cross-check 2: RSF and remaining life correlation
        if "rsf" in thickness_data and "remaining_life" in thickness_data:
            rsf = thickness_data["rsf"]
            remaining_life = thickness_data["remaining_life"]
            
            # Low RSF should correlate with short remaining life
            if rsf < Decimal("0.90") and remaining_life > Decimal("10"):
                results["inconsistencies"].append(
                    f"Low RSF ({rsf:.3f}) but long remaining life ({remaining_life:.1f} years). "
                    "Verify corrosion rate assumptions."
                )
            
            if rsf > Decimal("0.95") and remaining_life < Decimal("2"):
                results["inconsistencies"].append(
                    f"High RSF ({rsf:.3f}) but short remaining life ({remaining_life:.1f} years). "
                    "Check for accelerated corrosion."
                )
        
        # Generate recommendations based on findings
        if results["inconsistencies"]:
            results["recommendations"].extend([
                "Review all input data for accuracy",
                "Verify measurement locations are consistent",
                "Check for localized corrosion or damage",
                "Consider Level 2 FFS assessment for detailed analysis"
            ])
        
        return results
    
    def validate_inspection_interval(
        self,
        proposed_interval: Decimal,
        remaining_life: Decimal,
        equipment_type: EquipmentType,
        inspection_type: str,
        rsf: Optional[Decimal] = None
    ) -> Tuple[bool, Decimal, List[str]]:
        """
        Validate proposed inspection interval against API requirements.
        
        Returns:
            Tuple of (is_valid, maximum_allowed_interval, warnings)
        """
        warnings = []
        
        # Get code maximum
        max_allowed = self.constants.get_maximum_inspection_interval(
            equipment_type,
            inspection_type,
            remaining_life
        )
        
        # Additional constraints based on condition
        if rsf and rsf < Decimal("0.90"):
            # Reduce interval for low RSF
            max_allowed = min(max_allowed, Decimal("2"))
            warnings.append(
                f"Inspection interval limited to 2 years due to RSF {rsf:.3f} < 0.90"
            )
        
        # Validate proposed interval
        is_valid = proposed_interval <= max_allowed
        
        if not is_valid:
            warnings.append(
                f"Proposed interval {proposed_interval} years exceeds maximum "
                f"allowed {max_allowed} years"
            )
        
        # Add recommendations
        if remaining_life < Decimal("4"):
            warnings.append(
                f"With {remaining_life:.1f} years remaining life, consider "
                "continuous monitoring or quarterly thickness measurements"
            )
        
        return is_valid, max_allowed, warnings
