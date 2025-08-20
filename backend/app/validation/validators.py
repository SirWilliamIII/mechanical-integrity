"""
API 579 Input Validators

Validates all inputs against API 579 specified ranges with detailed
error messages and regulatory references.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Union
import logging

from pydantic import BaseModel, Field, validator

from app.calculations.constants import API579Constants, EquipmentType

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation fails with API 579 reference"""
    def __init__(
        self, 
        field: str, 
        value: any, 
        reason: str, 
        api_reference: str,
        action_required: Optional[str] = None
    ):
        self.field = field
        self.value = value
        self.reason = reason
        self.api_reference = api_reference
        self.action_required = action_required
        
        message = (
            f"Validation failed for {field}: {reason}\n"
            f"Value: {value}\n"
            f"API Reference: {api_reference}"
        )
        if action_required:
            message += f"\nAction Required: {action_required}"
        
        super().__init__(message)


class ValidationResult(BaseModel):
    """Result of validation with detailed information"""
    valid: bool = Field(..., description="Whether validation passed")
    field: str = Field(..., description="Field that was validated")
    value: Union[Decimal, str, int, float] = Field(..., description="Value that was validated")
    reason: Optional[str] = Field(None, description="Reason for failure if not valid")
    api_reference: Optional[str] = Field(None, description="API 579 clause reference")
    action_required: Optional[str] = Field(None, description="Required action if not valid")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class API579Validator:
    """
    Comprehensive validator for API 579 compliance.
    
    Validates all inputs against acceptable ranges specified in
    API 579-1/ASME FFS-1 with full traceability.
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, warnings become errors (recommended for safety)
        """
        self.strict_mode = strict_mode
        self.constants = API579Constants
        logger.info(f"Initialized API579Validator in {'strict' if strict_mode else 'normal'} mode")
    
    def validate_thickness_measurement(
        self,
        thickness: Union[Decimal, float, str],
        equipment_type: Union[EquipmentType, str],
        location: str,
        nominal_thickness: Optional[Decimal] = None,
        previous_thickness: Optional[Decimal] = None
    ) -> ValidationResult:
        """
        Validate thickness measurement against API 579 requirements.
        
        Args:
            thickness: Measured thickness in inches
            equipment_type: Type of equipment being measured
            location: Measurement location (e.g., "Shell Course 1")
            nominal_thickness: Original thickness for comparison
            previous_thickness: Previous measurement for trend analysis
            
        Returns:
            ValidationResult with detailed validation information
        """
        # Convert to Decimal for precision
        try:
            thickness_decimal = Decimal(str(thickness))
        except (InvalidOperation, ValueError) as e:
            return ValidationResult(
                valid=False,
                field="thickness",
                value=thickness,
                reason=f"Invalid thickness value: {e}",
                api_reference="API 579 Part 4, Section 4.3.3.1"
            )
        
        # Ensure equipment type is valid enum
        if isinstance(equipment_type, str):
            try:
                equipment_type = EquipmentType(equipment_type)
            except ValueError:
                return ValidationResult(
                    valid=False,
                    field="equipment_type",
                    value=equipment_type,
                    reason=f"Invalid equipment type: {equipment_type}",
                    api_reference="API 579 Part 2, Table 2.1"
                )
        
        warnings = []
        
        # Get limits for equipment type
        limits = self.constants.THICKNESS_LIMITS.get(equipment_type, {})
        abs_min = limits.get("absolute_minimum", Decimal("0"))
        nom_max = limits.get("nominal_maximum", Decimal("999"))
        
        # Check absolute minimum
        if thickness_decimal < abs_min:
            return ValidationResult(
                valid=False,
                field="thickness",
                value=thickness_decimal,
                reason=f"Thickness {thickness_decimal} below minimum {abs_min} for {equipment_type.value}",
                api_reference="API 579 Part 4, Table 4.1",
                action_required="IMMEDIATE INSPECTION AND ASSESSMENT REQUIRED"
            )
        
        # Check maximum (suspicious measurement)
        if thickness_decimal > nom_max:
            if self.strict_mode:
                return ValidationResult(
                    valid=False,
                    field="thickness",
                    value=thickness_decimal,
                    reason=f"Thickness {thickness_decimal} exceeds maximum {nom_max} for {equipment_type.value}",
                    api_reference="API 579 Part 4, Section 4.3.2",
                    action_required="Verify measurement accuracy and equipment specifications"
                )
            else:
                warnings.append(
                    f"Thickness {thickness_decimal} exceeds typical maximum {nom_max}"
                )
        
        # Check measurement precision
        # API 579 requires measurements to nearest 0.001"
        precision_check = thickness_decimal.as_tuple().exponent
        if precision_check > -3:  # Less than 3 decimal places
            warnings.append(
                f"Thickness precision insufficient. API 579 requires 0.001\" precision, "
                f"provided value has {-precision_check} decimal places"
            )
        
        # Compare with nominal if provided
        if nominal_thickness:
            metal_loss = nominal_thickness - thickness_decimal
            metal_loss_percent = (metal_loss / nominal_thickness * 100) if nominal_thickness > 0 else Decimal("0")
            
            if metal_loss_percent > Decimal("80"):
                return ValidationResult(
                    valid=False,
                    field="thickness",
                    value=thickness_decimal,
                    reason=f"Metal loss {metal_loss_percent:.1f}% exceeds 80% limit",
                    api_reference="API 579 Part 5, Section 5.4.2.2",
                    action_required="Level 2 or 3 FFS assessment required"
                )
            elif metal_loss_percent > Decimal("50"):
                warnings.append(
                    f"Significant metal loss detected: {metal_loss_percent:.1f}%"
                )
        
        # Compare with previous if provided (corrosion rate check)
        if previous_thickness and previous_thickness > thickness_decimal:
            thickness_change = previous_thickness - thickness_decimal
            
            # Suspicious if loss > 0.1" between inspections
            if thickness_change > Decimal("0.1"):
                warnings.append(
                    f"Large thickness change detected: {thickness_change} inches. "
                    "Verify measurement location and consider accelerated corrosion"
                )
        
        # Location validation
        if not location or len(location.strip()) < 3:
            warnings.append(
                "Measurement location description insufficient for traceability"
            )
        
        return ValidationResult(
            valid=True,
            field="thickness",
            value=thickness_decimal,
            warnings=warnings,
            api_reference="API 579 Part 4, Section 4.3.3"
        )
    
    def validate_pressure(
        self,
        pressure: Union[Decimal, float, str],
        pressure_type: str = "operating",
        temperature: Optional[Decimal] = None,
        equipment_type: Optional[EquipmentType] = None
    ) -> ValidationResult:
        """
        Validate pressure values against API 579 limits.
        
        Args:
            pressure: Pressure value in psi
            pressure_type: "design", "operating", or "test"
            temperature: Temperature for pressure-temperature limits
            equipment_type: Type of equipment for specific limits
            
        Returns:
            ValidationResult with detailed validation information
        """
        # Convert to Decimal
        try:
            pressure_decimal = Decimal(str(pressure))
        except (InvalidOperation, ValueError) as e:
            return ValidationResult(
                valid=False,
                field="pressure",
                value=pressure,
                reason=f"Invalid pressure value: {e}",
                api_reference="API 579 Part 4, Section 4.3.1"
            )
        
        warnings = []
        
        # Check basic limits
        if pressure_decimal < self.constants.PRESSURE_LIMITS["vacuum_limit"]:
            return ValidationResult(
                valid=False,
                field="pressure",
                value=pressure_decimal,
                reason=f"Pressure {pressure_decimal} psi below full vacuum limit",
                api_reference="API 579 Part 4, Section 4.3.1",
                action_required="Verify gauge calibration and vacuum design"
            )
        
        if pressure_decimal > self.constants.PRESSURE_LIMITS["maximum_design_pressure"]:
            if self.strict_mode or pressure_type == "operating":
                return ValidationResult(
                    valid=False,
                    field="pressure",
                    value=pressure_decimal,
                    reason=f"Pressure {pressure_decimal} psi exceeds maximum {self.constants.PRESSURE_LIMITS['maximum_design_pressure']} psi",
                    api_reference="API 579 Part 4, Table 4.3",
                    action_required="Special high-pressure design review required"
                )
            else:
                warnings.append(
                    f"Pressure {pressure_decimal} psi requires special design considerations"
                )
        
        # Check if high pressure
        if pressure_decimal > self.constants.PRESSURE_LIMITS["high_pressure_threshold"]:
            warnings.append(
                f"High pressure service ({pressure_decimal} psi) requires enhanced inspection "
                "per API 579 Part 4, Section 4.3.4"
            )
        
        # TODO: [PERFORMANCE] Implement pressure validation caching for frequently used values
        # Common pressure ranges could be pre-validated and cached to reduce computation overhead
        
        # Validate test pressures
        if pressure_type == "test":
            if pressure_decimal > self.constants.PRESSURE_LIMITS["maximum_design_pressure"] * self.constants.PRESSURE_LIMITS["proof_test_factor"]:
                return ValidationResult(
                    valid=False,
                    field="pressure",
                    value=pressure_decimal,
                    reason=f"Test pressure exceeds safe limit",
                    api_reference="ASME Section VIII, UG-99",
                    action_required="Reduce test pressure to safe levels"
                )
        
        # Temperature-pressure relationship
        if temperature and equipment_type:
            if self.constants.is_creep_range(temperature, "carbon_steel"):
                if pressure_decimal > self.constants.PRESSURE_LIMITS["high_pressure_threshold"] * Decimal("0.8"):
                    warnings.append(
                        f"Pressure-temperature combination ({pressure_decimal} psi at {temperature}°F) "
                        "requires creep analysis per API 579 Part 10"
                    )
        
        return ValidationResult(
            valid=True,
            field="pressure",
            value=pressure_decimal,
            warnings=warnings,
            api_reference="API 579 Part 4, Section 4.3"
        )
    
    def validate_temperature(
        self,
        temperature: Union[Decimal, float, str],
        material: str,
        service_type: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate temperature against material limits.
        
        Args:
            temperature: Temperature in °F
            material: Material specification
            service_type: Type of service for specific limits
            
        Returns:
            ValidationResult with detailed validation information
        """
        # Convert to Decimal
        try:
            temp_decimal = Decimal(str(temperature))
        except (InvalidOperation, ValueError) as e:
            return ValidationResult(
                valid=False,
                field="temperature",
                value=temperature,
                reason=f"Invalid temperature value: {e}",
                api_reference="API 579 Annex F"
            )
        
        warnings = []
        
        # Check absolute limits
        if temp_decimal < self.constants.TEMPERATURE_LIMITS["minimum_metal_temperature"]:
            return ValidationResult(
                valid=False,
                field="temperature",
                value=temp_decimal,
                reason=f"Temperature {temp_decimal}°F below minimum metal temperature",
                api_reference="API 579 Part 3, Section 3.4",
                action_required="Perform brittle fracture assessment"
            )
        
        if temp_decimal > self.constants.TEMPERATURE_LIMITS["maximum_temperature"]:
            return ValidationResult(
                valid=False,
                field="temperature",
                value=temp_decimal,
                reason=f"Temperature {temp_decimal}°F exceeds maximum limit",
                api_reference="API 579 Annex F",
                action_required="Special high-temperature material required"
            )
        
        # Check creep range
        if self.constants.is_creep_range(temp_decimal, material):
            warnings.append(
                f"Temperature {temp_decimal}°F in creep range for {material}. "
                "Time-dependent analysis required per API 579 Part 10"
            )
        
        # Check for brittle fracture concerns
        if temp_decimal < Decimal("50") and "carbon" in material.lower():
            warnings.append(
                f"Low temperature service ({temp_decimal}°F) with carbon steel. "
                "Perform brittle fracture assessment per API 579 Part 3"
            )
        
        return ValidationResult(
            valid=True,
            field="temperature",
            value=temp_decimal,
            warnings=warnings,
            api_reference="API 579 Annex F"
        )
    
    def validate_corrosion_rate(
        self,
        corrosion_rate: Union[Decimal, float, str],
        material: str,
        service: str,
        measurement_interval_years: Optional[Decimal] = None
    ) -> ValidationResult:
        """
        Validate corrosion rate against typical values.
        
        Args:
            corrosion_rate: Measured corrosion rate in inches/year
            material: Material type
            service: Service environment
            measurement_interval_years: Time between measurements
            
        Returns:
            ValidationResult with detailed validation information
        """
        # Convert to Decimal
        try:
            rate_decimal = Decimal(str(corrosion_rate))
        except (InvalidOperation, ValueError) as e:
            return ValidationResult(
                valid=False,
                field="corrosion_rate",
                value=corrosion_rate,
                reason=f"Invalid corrosion rate value: {e}",
                api_reference="API 579 Part 4, Section 4.4.3"
            )
        
        warnings = []
        
        # Negative corrosion rate is invalid
        if rate_decimal < 0:
            return ValidationResult(
                valid=False,
                field="corrosion_rate",
                value=rate_decimal,
                reason="Corrosion rate cannot be negative",
                api_reference="API 579 Part 4, Section 4.4.3.1",
                action_required="Review thickness measurements and calculation method"
            )
        
        # Get typical rates
        typical, minimum, maximum = self.constants.get_corrosion_rate_range(material, service)
        
        # Check against typical ranges
        if rate_decimal > maximum:
            if self.strict_mode:
                return ValidationResult(
                    valid=False,
                    field="corrosion_rate",
                    value=rate_decimal,
                    reason=f"Corrosion rate {rate_decimal} exceeds maximum expected {maximum} for {material} in {service}",
                    api_reference="API 579 Part 4, Table 4.4",
                    action_required="Investigate accelerated corrosion mechanism"
                )
            else:
                warnings.append(
                    f"Corrosion rate {rate_decimal} in/yr unusually high for {material} in {service}"
                )
        
        # Very high corrosion rate
        if rate_decimal > Decimal("0.050"):  # 50 mpy
            warnings.append(
                "Corrosion rate exceeds 50 mpy - consider material upgrade or inhibition"
            )
        
        # Check measurement interval validity
        if measurement_interval_years and measurement_interval_years < Decimal("0.5"):
            warnings.append(
                f"Measurement interval {measurement_interval_years} years may be too short "
                "for accurate corrosion rate determination"
            )
        
        # Zero corrosion rate warning
        if rate_decimal == 0:
            warnings.append(
                "Zero corrosion rate measured - verify this is accurate and not "
                "due to measurement limitations"
            )
        
        # TODO: [FEATURE] Add statistical analysis for corrosion rate validation
        # Implement trending analysis to validate rates against historical data patterns
        
        return ValidationResult(
            valid=True,
            field="corrosion_rate",
            value=rate_decimal,
            warnings=warnings,
            api_reference="API 579 Part 4, Section 4.4.3"
        )
    
    def validate_material_specification(
        self,
        material_spec: str,
        equipment_type: EquipmentType,
        service_conditions: Optional[Dict[str, any]] = None
    ) -> ValidationResult:
        """
        Validate material specification for service.
        
        Args:
            material_spec: Material specification (e.g., "SA-516-70")
            equipment_type: Type of equipment
            service_conditions: Dict with temperature, pressure, service type
            
        Returns:
            ValidationResult with detailed validation information
        """
        warnings = []
        
        # Check if material is in known materials
        known_materials = list(self.constants.MATERIAL_YIELD_STRENGTH.keys())
        
        if material_spec not in known_materials:
            warnings.append(
                f"Material {material_spec} not in standard materials database. "
                "Manual verification of properties required"
            )
        
        # Service condition checks
        if service_conditions:
            temp = service_conditions.get("temperature")
            service = service_conditions.get("service_type", "").lower()
            
            # Check for material-service compatibility
            if "stainless" not in material_spec.lower() and "acid" in service:
                warnings.append(
                    f"Carbon steel material {material_spec} in acid service "
                    "requires careful corrosion monitoring"
                )
            
            if temp and temp > Decimal("800") and "carbon" in material_spec.lower():
                return ValidationResult(
                    valid=False,
                    field="material_specification",
                    value=material_spec,
                    reason=f"Carbon steel not suitable above 800°F",
                    api_reference="API 579 Annex F",
                    action_required="Upgrade to high-temperature alloy"
                )
        
        return ValidationResult(
            valid=True,
            field="material_specification",
            value=material_spec,
            warnings=warnings,
            api_reference="API 579 Annex F"
        )
    
    def validate_calculation_inputs(
        self,
        calculation_type: str,
        inputs: Dict[str, any]
    ) -> List[ValidationResult]:
        """
        Validate all inputs for a specific calculation type.
        
        Args:
            calculation_type: Type of calculation (e.g., "minimum_thickness")
            inputs: Dictionary of input parameters
            
        Returns:
            List of ValidationResult objects for each input
        """
        results = []
        
        # Define required inputs for each calculation type
        required_inputs = {
            "minimum_thickness": ["pressure", "radius", "stress", "efficiency"],
            "remaining_strength_factor": ["current_thickness", "minimum_thickness", "nominal_thickness"],
            "remaining_life": ["current_thickness", "minimum_thickness", "corrosion_rate"],
            "mawp": ["current_thickness", "radius", "stress", "efficiency"]
        }
        
        # Check for missing required inputs
        required = required_inputs.get(calculation_type, [])
        for param in required:
            if param not in inputs:
                results.append(ValidationResult(
                    valid=False,
                    field=param,
                    value=None,
                    reason=f"Required parameter '{param}' missing for {calculation_type}",
                    api_reference="API 579 Part 4"
                ))
        
        # Validate each input based on type
        for param, value in inputs.items():
            if param in ["pressure", "design_pressure", "operating_pressure"]:
                results.append(self.validate_pressure(value))
            
            elif param in ["thickness", "current_thickness", "minimum_thickness", "nominal_thickness"]:
                equipment_type = inputs.get("equipment_type", EquipmentType.PRESSURE_VESSEL)
                results.append(self.validate_thickness_measurement(
                    value, 
                    equipment_type,
                    f"{param} measurement"
                ))
            
            elif param == "temperature":
                material = inputs.get("material", "carbon_steel")
                results.append(self.validate_temperature(value, material))
            
            elif param == "corrosion_rate":
                material = inputs.get("material", "carbon_steel")
                service = inputs.get("service", "general")
                results.append(self.validate_corrosion_rate(value, material, service))
            
            elif param == "efficiency":
                # Joint efficiency must be between 0 and 1
                try:
                    eff = Decimal(str(value))
                    if not (Decimal("0") < eff <= Decimal("1")):
                        results.append(ValidationResult(
                            valid=False,
                            field=param,
                            value=value,
                            reason=f"Joint efficiency must be between 0 and 1",
                            api_reference="ASME Section VIII, UW-12"
                        ))
                    else:
                        results.append(ValidationResult(
                            valid=True,
                            field=param,
                            value=eff
                        ))
                except:
                    results.append(ValidationResult(
                        valid=False,
                        field=param,
                        value=value,
                        reason=f"Invalid efficiency value",
                        api_reference="ASME Section VIII, UW-12"
                    ))
        
        return results
