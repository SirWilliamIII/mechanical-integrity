"""
Physical Bounds Validation for API 579 Compliance.
Validates all parameters against API 579 acceptable ranges and physical limits.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger("mechanical_integrity.physical_bounds")


class ValidationSeverity(str, Enum):
    """Severity levels for validation results."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PhysicalBoundsValidator:
    """
    Comprehensive validator for physical parameters per API 579 requirements.
    
    Validates all inputs against:
    - API 579-1/ASME FFS-1 acceptable ranges
    - Physical laws and engineering limits
    - Industry standard practice ranges
    - Safety-critical thresholds
    """
    
    # API 579 Part 4 - Pressure limits (PSI)
    PRESSURE_LIMITS = {
        'minimum': Decimal('0.1'),        # Minimum meaningful pressure
        'maximum': Decimal('10000'),      # Typical API 579 upper limit
        'vacuum_limit': Decimal('-15'),   # Full vacuum limit (PSIA)
        'warning_high': Decimal('5000')   # High pressure warning threshold
    }
    
    # API 579 Part 4 - Temperature limits (°F)
    TEMPERATURE_LIMITS = {
        'minimum': Decimal('-80'),        # Cryogenic limit
        'maximum': Decimal('1200'),       # High temperature creep limit
        'ambient_min': Decimal('32'),     # Freezing point
        'ambient_max': Decimal('120'),    # Hot climate maximum
        'creep_threshold': Decimal('800') # Creep damage threshold
    }
    
    # API 579 Part 5 - Thickness limits (inches)
    THICKNESS_LIMITS = {
        'minimum_measurable': Decimal('0.001'),   # UT measurement precision limit
        'maximum_practical': Decimal('20'),       # Practical thickness limit
        'minimum_required': Decimal('0.025'),     # Minimum structural thickness
        'corrosion_allowance_max': Decimal('1'),  # Maximum reasonable CA
        'warning_thin': Decimal('0.1')            # Thin wall warning
    }
    
    # API 579 Part 4 - Stress limits (PSI)
    STRESS_LIMITS = {
        'minimum': Decimal('1000'),       # Minimum meaningful allowable stress
        'maximum': Decimal('80000'),      # High strength steel limit
        'carbon_steel_typical': Decimal('20000'),  # Typical carbon steel
        'alloy_steel_max': Decimal('60000')        # High alloy steel maximum
    }
    
    # Equipment dimensional limits
    DIMENSION_LIMITS = {
        'radius_min': Decimal('0.5'),     # 1" diameter minimum
        'radius_max': Decimal('600'),     # 1200" diameter maximum (100 feet)
        'length_max': Decimal('1200'),    # 100 feet maximum length
        'aspect_ratio_max': Decimal('50') # Length/diameter ratio limit
    }
    
    # Material property limits
    MATERIAL_LIMITS = {
        'joint_efficiency_min': Decimal('0.6'),   # Minimum per ASME VIII
        'joint_efficiency_max': Decimal('1.0'),   # Full radiography
        'safety_factor_min': Decimal('2.5'),      # Minimum safety factor
        'safety_factor_max': Decimal('8.0'),      # Maximum reasonable SF
        'corrosion_rate_max': Decimal('0.5')      # inches/year maximum
    }
    
    @classmethod
    def validate_pressure(
        cls, 
        pressure: Decimal, 
        parameter_name: str = "pressure"
    ) -> Dict[str, Any]:
        """
        Validate pressure against API 579 limits and physical constraints.
        
        Args:
            pressure: Pressure in PSI
            parameter_name: Name of parameter for error messages
            
        Returns:
            Validation result with pass/fail, warnings, and messages
        """
        result = {
            'valid': True,
            'severity': ValidationSeverity.INFO,
            'messages': [],
            'value': pressure,
            'parameter': parameter_name,
            'bounds_applied': 'API_579_PART_4'
        }
        
        # Check absolute limits
        if pressure < cls.PRESSURE_LIMITS['vacuum_limit']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({pressure} PSI) below vacuum limit "
                f"({cls.PRESSURE_LIMITS['vacuum_limit']} PSI)"
            )
        elif pressure < cls.PRESSURE_LIMITS['minimum']:
            result['severity'] = ValidationSeverity.WARNING
            result['messages'].append(
                f"{parameter_name} ({pressure} PSI) below typical minimum "
                f"({cls.PRESSURE_LIMITS['minimum']} PSI)"
            )
        
        if pressure > cls.PRESSURE_LIMITS['maximum']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({pressure} PSI) exceeds API 579 typical limit "
                f"({cls.PRESSURE_LIMITS['maximum']} PSI) - requires specialist review"
            )
        elif pressure > cls.PRESSURE_LIMITS['warning_high']:
            result['severity'] = ValidationSeverity.WARNING
            result['messages'].append(
                f"{parameter_name} ({pressure} PSI) is high pressure - "
                f"verify material suitability and inspection requirements"
            )
        
        return result
    
    @classmethod
    def validate_temperature(
        cls,
        temperature: Decimal,
        material_spec: Optional[str] = None,
        parameter_name: str = "temperature"
    ) -> Dict[str, Any]:
        """
        Validate temperature against API 579 limits and material constraints.
        
        Args:
            temperature: Temperature in °F
            material_spec: Material specification (e.g., "SA-516-70")
            parameter_name: Parameter name for messages
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'severity': ValidationSeverity.INFO,
            'messages': [],
            'value': temperature,
            'parameter': parameter_name,
            'bounds_applied': 'API_579_PART_4'
        }
        
        # Check absolute limits
        if temperature < cls.TEMPERATURE_LIMITS['minimum']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({temperature}°F) below cryogenic limit "
                f"({cls.TEMPERATURE_LIMITS['minimum']}°F) - brittle fracture risk"
            )
        
        if temperature > cls.TEMPERATURE_LIMITS['maximum']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({temperature}°F) exceeds high temperature limit "
                f"({cls.TEMPERATURE_LIMITS['maximum']}°F) - creep damage likely"
            )
        
        # Check creep threshold
        if temperature >= cls.TEMPERATURE_LIMITS['creep_threshold']:
            result['severity'] = ValidationSeverity.WARNING
            result['messages'].append(
                f"{parameter_name} ({temperature}°F) above creep threshold "
                f"({cls.TEMPERATURE_LIMITS['creep_threshold']}°F) - "
                f"requires API 579 Part 10 creep assessment"
            )
        
        # Material-specific validation
        if material_spec:
            if "SA-516" in material_spec and temperature > Decimal('800'):
                result['severity'] = max(result['severity'], ValidationSeverity.WARNING)
                result['messages'].append(
                    f"Carbon steel {material_spec} approaching temperature limit at {temperature}°F"
                )
        
        return result
    
    @classmethod
    def validate_thickness(
        cls,
        thickness: Decimal,
        design_thickness: Optional[Decimal] = None,
        parameter_name: str = "thickness"
    ) -> Dict[str, Any]:
        """
        Validate thickness measurements against API 579 requirements.
        
        Args:
            thickness: Thickness in inches
            design_thickness: Original design thickness for comparison
            parameter_name: Parameter name for messages
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'severity': ValidationSeverity.INFO,
            'messages': [],
            'value': thickness,
            'parameter': parameter_name,
            'bounds_applied': 'API_579_PART_5'
        }
        
        # Check measurement precision
        if thickness < cls.THICKNESS_LIMITS['minimum_measurable']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({thickness}\") below measurement precision limit "
                f"({cls.THICKNESS_LIMITS['minimum_measurable']}\") - invalid measurement"
            )
        
        # Check structural minimum
        if thickness < cls.THICKNESS_LIMITS['minimum_required']:
            result['severity'] = ValidationSeverity.ERROR
            result['messages'].append(
                f"{parameter_name} ({thickness}\") below structural minimum "
                f"({cls.THICKNESS_LIMITS['minimum_required']}\") - immediate replacement required"
            )
        
        # Check practical maximum
        if thickness > cls.THICKNESS_LIMITS['maximum_practical']:
            result['severity'] = ValidationSeverity.WARNING
            result['messages'].append(
                f"{parameter_name} ({thickness}\") exceeds typical maximum "
                f"({cls.THICKNESS_LIMITS['maximum_practical']}\") - verify measurement"
            )
        
        # Thin wall warning
        if thickness <= cls.THICKNESS_LIMITS['warning_thin']:
            result['severity'] = max(result['severity'], ValidationSeverity.WARNING)
            result['messages'].append(
                f"{parameter_name} ({thickness}\") is thin wall - increased inspection required"
            )
        
        # Compare to design thickness
        if design_thickness:
            metal_loss_percent = ((design_thickness - thickness) / design_thickness) * 100
            if metal_loss_percent > 50:
                result['severity'] = max(result['severity'], ValidationSeverity.ERROR)
                result['messages'].append(
                    f"Metal loss {metal_loss_percent:.1f}% exceeds 50% - "
                    f"requires Level 2 assessment"
                )
            elif metal_loss_percent > 30:
                result['severity'] = max(result['severity'], ValidationSeverity.WARNING)
                result['messages'].append(
                    f"Metal loss {metal_loss_percent:.1f}% exceeds 30% - "
                    f"increased monitoring required"
                )
        
        return result
    
    @classmethod
    def validate_allowable_stress(
        cls,
        stress: Decimal,
        material_spec: str,
        temperature: Decimal,
        parameter_name: str = "allowable_stress"
    ) -> Dict[str, Any]:
        """
        Validate allowable stress against ASME Section II-D limits.
        
        Args:
            stress: Allowable stress in PSI
            material_spec: Material specification
            temperature: Operating temperature in °F
            parameter_name: Parameter name for messages
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'severity': ValidationSeverity.INFO,
            'messages': [],
            'value': stress,
            'parameter': parameter_name,
            'bounds_applied': 'ASME_SECTION_II_D'
        }
        
        # Check absolute limits
        if stress < cls.STRESS_LIMITS['minimum']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({stress} PSI) below minimum meaningful value "
                f"({cls.STRESS_LIMITS['minimum']} PSI)"
            )
        
        if stress > cls.STRESS_LIMITS['maximum']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"{parameter_name} ({stress} PSI) exceeds maximum reasonable value "
                f"({cls.STRESS_LIMITS['maximum']} PSI)"
            )
        
        # Material-specific validation
        if "SA-516" in material_spec or "SA-106" in material_spec:
            # Carbon steel
            if stress > cls.STRESS_LIMITS['carbon_steel_typical'] * Decimal('1.2'):
                result['severity'] = ValidationSeverity.WARNING
                result['messages'].append(
                    f"Carbon steel stress ({stress} PSI) unusually high for {material_spec}"
                )
        elif "SA-335" in material_spec or "SA-387" in material_spec:
            # Alloy steel
            if stress > cls.STRESS_LIMITS['alloy_steel_max']:
                result['severity'] = ValidationSeverity.WARNING
                result['messages'].append(
                    f"Alloy steel stress ({stress} PSI) approaching maximum for {material_spec}"
                )
        
        return result
    
    @classmethod
    def validate_equipment_dimensions(
        cls,
        internal_radius: Decimal,
        length: Optional[Decimal] = None,
        parameter_name: str = "dimensions"
    ) -> Dict[str, Any]:
        """
        Validate equipment dimensions against API 579 geometric limits.
        
        Args:
            internal_radius: Internal radius in inches
            length: Equipment length in inches (optional)
            parameter_name: Parameter name for messages
            
        Returns:
            Validation result
        """
        result = {
            'valid': True,
            'severity': ValidationSeverity.INFO,
            'messages': [],
            'value': {'internal_radius': internal_radius, 'length': length},
            'parameter': parameter_name,
            'bounds_applied': 'API_579_GEOMETRIC_LIMITS'
        }
        
        # Validate radius
        if internal_radius < cls.DIMENSION_LIMITS['radius_min']:
            result['valid'] = False
            result['severity'] = ValidationSeverity.CRITICAL
            result['messages'].append(
                f"Internal radius ({internal_radius}\") below minimum "
                f"({cls.DIMENSION_LIMITS['radius_min']}\") - invalid geometry"
            )
        
        if internal_radius > cls.DIMENSION_LIMITS['radius_max']:
            result['severity'] = ValidationSeverity.WARNING
            result['messages'].append(
                f"Internal radius ({internal_radius}\") exceeds typical API 579 range "
                f"({cls.DIMENSION_LIMITS['radius_max']}\") - specialist review required"
            )
        
        # Validate aspect ratio if length provided
        if length:
            diameter = internal_radius * 2
            aspect_ratio = length / diameter
            
            if aspect_ratio > cls.DIMENSION_LIMITS['aspect_ratio_max']:
                result['severity'] = ValidationSeverity.WARNING
                result['messages'].append(
                    f"Aspect ratio ({aspect_ratio:.1f}) exceeds typical limit "
                    f"({cls.DIMENSION_LIMITS['aspect_ratio_max']}) - "
                    f"may require advanced stress analysis"
                )
        
        return result
    
    @classmethod
    def validate_calculation_inputs(
        cls,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of all API 579 calculation inputs.
        
        Args:
            inputs: Dictionary of calculation inputs
            
        Returns:
            Combined validation result
        """
        validation_results = []
        overall_valid = True
        highest_severity = ValidationSeverity.INFO
        
        # Validate pressure
        if 'pressure' in inputs:
            pressure_result = cls.validate_pressure(
                Decimal(str(inputs['pressure'])), 'design_pressure'
            )
            validation_results.append(pressure_result)
            if not pressure_result['valid']:
                overall_valid = False
            if pressure_result['severity'] > highest_severity:
                highest_severity = pressure_result['severity']
        
        # Validate temperature
        if 'temperature' in inputs:
            temp_result = cls.validate_temperature(
                Decimal(str(inputs['temperature'])),
                inputs.get('material_specification'),
                'design_temperature'
            )
            validation_results.append(temp_result)
            if not temp_result['valid']:
                overall_valid = False
            if temp_result['severity'] > highest_severity:
                highest_severity = temp_result['severity']
        
        # Validate thickness parameters
        thickness_params = ['current_thickness', 'minimum_thickness', 'design_thickness']
        for param in thickness_params:
            if param in inputs:
                thickness_result = cls.validate_thickness(
                    Decimal(str(inputs[param])),
                    inputs.get('design_thickness'),
                    param
                )
                validation_results.append(thickness_result)
                if not thickness_result['valid']:
                    overall_valid = False
                if thickness_result['severity'] > highest_severity:
                    highest_severity = thickness_result['severity']
        
        # Validate allowable stress
        if 'allowable_stress' in inputs:
            stress_result = cls.validate_allowable_stress(
                Decimal(str(inputs['allowable_stress'])),
                inputs.get('material_specification', 'SA-516-70'),
                Decimal(str(inputs.get('temperature', 200))),
                'allowable_stress'
            )
            validation_results.append(stress_result)
            if not stress_result['valid']:
                overall_valid = False
            if stress_result['severity'] > highest_severity:
                highest_severity = stress_result['severity']
        
        # Validate dimensions
        if 'internal_radius' in inputs:
            dim_result = cls.validate_equipment_dimensions(
                Decimal(str(inputs['internal_radius'])),
                inputs.get('length'),
                'equipment_dimensions'
            )
            validation_results.append(dim_result)
            if not dim_result['valid']:
                overall_valid = False
            if dim_result['severity'] > highest_severity:
                highest_severity = dim_result['severity']
        
        # Compile results
        all_messages = []
        for result in validation_results:
            all_messages.extend(result['messages'])
        
        return {
            'overall_valid': overall_valid,
            'highest_severity': highest_severity,
            'total_checks': len(validation_results),
            'failed_checks': sum(1 for r in validation_results if not r['valid']),
            'all_messages': all_messages,
            'detailed_results': validation_results,
            'summary': f"Validated {len(validation_results)} parameters, "
                      f"{sum(1 for r in validation_results if not r['valid'])} failures, "
                      f"highest severity: {highest_severity}"
        }