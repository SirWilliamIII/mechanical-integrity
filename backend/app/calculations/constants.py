"""
API 579 Constants and Reference Values

This module contains all constants, limits, and reference values from
API 579-1/ASME FFS-1 standard. These values are critical for safety
calculations and must not be modified without proper authorization.

References:
- API 579-1/ASME FFS-1 2021 Edition
- API 510, 570, 653 for inspection intervals
- ASME Section VIII for pressure vessel design
"""
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Tuple


class EquipmentType(str, Enum):
    """Equipment types per API 579 categorization"""
    PRESSURE_VESSEL = "pressure_vessel"
    STORAGE_TANK = "storage_tank"
    PIPING = "piping"
    HEAT_EXCHANGER = "heat_exchanger"


class DamageType(str, Enum):
    """Damage mechanisms covered by API 579"""
    GENERAL_METAL_LOSS = "general_metal_loss"  # Part 4
    LOCAL_METAL_LOSS = "local_metal_loss"      # Part 5
    PITTING_CORROSION = "pitting_corrosion"    # Part 6
    BLISTERS_HIC_SOHIC = "blisters_hic_sohic"  # Part 7
    WELD_MISALIGNMENT = "weld_misalignment"    # Part 8
    CRACK_LIKE_FLAWS = "crack_like_flaws"      # Part 9
    CREEP_DAMAGE = "creep_damage"              # Part 10
    FIRE_DAMAGE = "fire_damage"                # Part 11
    DENTS_GOUGES = "dents_gouges"              # Part 12
    LAMINATIONS = "laminations"                # Part 13


class API579Constants:
    """Central repository for all API 579 constants and limits"""
    
    # ========================================================================
    # THICKNESS LIMITS - API 579 Part 4, Table 4.1
    # ========================================================================
    THICKNESS_LIMITS: Dict[EquipmentType, Dict[str, Decimal]] = {
        EquipmentType.PRESSURE_VESSEL: {
            "absolute_minimum": Decimal("0.0625"),  # 1/16 inch
            "nominal_minimum": Decimal("0.125"),    # 1/8 inch typical
            "nominal_maximum": Decimal("6.0"),      # 6 inches
            "thin_wall_limit": Decimal("0.1")       # t/R ratio for thin wall
        },
        EquipmentType.PIPING: {
            "absolute_minimum": Decimal("0.065"),   # Schedule 10 minimum
            "nominal_minimum": Decimal("0.109"),    # Schedule 40 typical
            "nominal_maximum": Decimal("2.0"),      # 2 inches
            "thin_wall_limit": Decimal("0.1")       # t/R ratio
        },
        EquipmentType.STORAGE_TANK: {
            "absolute_minimum": Decimal("0.1875"),  # 3/16 inch per API 653
            "nominal_minimum": Decimal("0.25"),     # 1/4 inch typical
            "nominal_maximum": Decimal("2.0"),      # 2 inches
            "thin_wall_limit": Decimal("0.1")       # Not typically used for tanks
        }
    }
    
    # ========================================================================
    # PRESSURE LIMITS - API 579 Part 4, Section 4.3
    # ========================================================================
    PRESSURE_LIMITS: Dict[str, Decimal] = {
        "maximum_design_pressure": Decimal("5000"),    # psi - above requires special review
        "high_pressure_threshold": Decimal("1500"),    # psi - enhanced inspection
        "vacuum_limit": Decimal("-14.7"),             # psi - full vacuum
        "proof_test_factor": Decimal("1.5"),          # Times MAWP for proof test
        "hydro_test_factor": Decimal("1.3")           # Times MAWP for hydro test
    }
    
    # ========================================================================
    # TEMPERATURE LIMITS - API 579 Annex F
    # ========================================================================
    TEMPERATURE_LIMITS: Dict[str, Decimal] = {
        "minimum_metal_temperature": Decimal("-320"),  # °F - Cryogenic limit
        "creep_threshold_carbon": Decimal("700"),      # °F - Carbon steel creep
        "creep_threshold_low_alloy": Decimal("750"),   # °F - Low alloy steel
        "creep_threshold_stainless": Decimal("800"),   # °F - Stainless steel
        "maximum_temperature": Decimal("1500")          # °F - Practical limit
    }
    
    # ========================================================================
    # CORROSION RATES - API 579 Part 4, Section 4.4.3
    # ========================================================================
    TYPICAL_CORROSION_RATES: Dict[str, Dict[str, Decimal]] = {
        "carbon_steel": {
            "water_service": Decimal("0.005"),         # inches/year
            "steam_service": Decimal("0.003"),         # inches/year
            "hydrocarbon_dry": Decimal("0.001"),       # inches/year
            "hydrocarbon_wet": Decimal("0.010"),       # inches/year
            "acid_service": Decimal("0.020")           # inches/year - requires monitoring
        },
        "stainless_steel": {
            "water_service": Decimal("0.001"),         # inches/year
            "steam_service": Decimal("0.0005"),        # inches/year
            "hydrocarbon_dry": Decimal("0.0001"),      # inches/year
            "chloride_service": Decimal("0.050")       # inches/year - SCC risk
        }
    }
    
    # ========================================================================
    # SAFETY FACTORS AND LIMITS - API 579 Part 2 & 4
    # ========================================================================
    SAFETY_FACTORS: Dict[str, Decimal] = {
        "rsf_minimum_acceptable": Decimal("0.90"),     # Below requires Level 2/3
        "rsf_immediate_action": Decimal("0.80"),       # Immediate inspection/repair
        "thickness_measurement_tolerance": Decimal("0.001"),  # ±0.001 inch
        "pressure_calculation_tolerance": Decimal("0.0001"),  # 0.01% for pressure
        "fca_minimum": Decimal("0.0"),                # inches - can be zero
        "fca_typical": Decimal("0.0625"),             # 1/16 inch typical
        "fca_conservative": Decimal("0.125")          # 1/8 inch conservative
    }
    
    # ========================================================================
    # INSPECTION INTERVALS - API 510/570/653
    # ========================================================================
    MAXIMUM_INSPECTION_INTERVALS: Dict[EquipmentType, Dict[str, int]] = {
        EquipmentType.PRESSURE_VESSEL: {
            "internal_rbi": 10,          # years - with RBI program
            "internal_no_rbi": 5,        # years - without RBI
            "external_online": 5,        # years - while in service
            "thickness_measurement": 5    # years - CML readings
        },
        EquipmentType.PIPING: {
            "class_1": 5,               # years - High risk
            "class_2": 10,              # years - Medium risk
            "class_3": 10,              # years - Low risk
            "thickness_measurement": 5   # years - Or 1/2 remaining life
        },
        EquipmentType.STORAGE_TANK: {
            "internal_initial": 10,      # years - First internal
            "internal_subsequent": 20,   # years - If no issues
            "external": 5,              # years - External inspection
            "thickness_measurement": 15  # years - Or per corrosion rate
        }
    }
    
    # ========================================================================
    # LEVEL 1 ASSESSMENT CRITERIA - API 579 Part 4 & 5
    # ========================================================================
    LEVEL1_CRITERIA: Dict[str, Dict[str, Decimal]] = {
        "metal_loss": {
            "maximum_depth_ratio": Decimal("0.80"),    # 80% of thickness
            "maximum_length_diameter": Decimal("1.0"),  # Length/Diameter ratio
            "minimum_remaining_ratio": Decimal("0.20")  # 20% remaining thickness
        },
        "pitting": {
            "maximum_pit_depth": Decimal("0.50"),      # 50% of thickness
            "minimum_spacing_ratio": Decimal("3.0"),    # Spacing/Diameter
            "density_limit": Decimal("10")             # Pits per square inch
        }
    }
    
    # ========================================================================
    # MATERIAL PROPERTIES - API 579 Annex F
    # ========================================================================
    # TODO: [DATA] Expand material database with additional ASME materials
    # Add SA-515, SA-537, A-105, and other common pressure vessel materials
    # Include ultimate tensile strength and elastic modulus for complete analysis
    MATERIAL_YIELD_STRENGTH: Dict[str, Dict[Decimal, Decimal]] = {
        "SA-516-70": {  # Temperature: Yield Strength (psi)
            Decimal("70"): Decimal("38000"),
            Decimal("200"): Decimal("36600"),
            Decimal("400"): Decimal("35100"),
            Decimal("600"): Decimal("32500"),
            Decimal("700"): Decimal("28200")
        },
        "SA-106-B": {
            Decimal("70"): Decimal("35000"),
            Decimal("200"): Decimal("33300"),
            Decimal("400"): Decimal("31200"),
            Decimal("600"): Decimal("28700"),
            Decimal("700"): Decimal("23300")
        }
    }
    
    # ========================================================================
    # WELD JOINT EFFICIENCY - ASME Section VIII
    # ========================================================================
    JOINT_EFFICIENCY: Dict[str, Decimal] = {
        "full_rt": Decimal("1.00"),          # Full radiography
        "spot_rt": Decimal("0.85"),          # Spot radiography
        "no_rt": Decimal("0.70"),            # No radiography
        "partial_penetration": Decimal("0.80"),  # Partial penetration welds
        "fillet_weld": Decimal("0.55")       # Fillet welds (special cases)
    }
    
    # ========================================================================
    # CALCULATION METHODS BY DAMAGE TYPE
    # ========================================================================
    CALCULATION_METHODS: Dict[DamageType, List[str]] = {
        DamageType.GENERAL_METAL_LOSS: [
            "remaining_strength_factor",
            "minimum_required_thickness",
            "maximum_allowable_working_pressure",
            "remaining_life"
        ],
        DamageType.LOCAL_METAL_LOSS: [
            "remaining_strength_factor",
            "folias_factor",
            "level_2_assessment"
        ],
        DamageType.PITTING_CORROSION: [
            "pit_couple_assessment",
            "remaining_strength_factor",
            "pit_depth_screening"
        ]
    }
    
    @classmethod
    def get_thickness_limit(
        cls, 
        equipment_type: EquipmentType, 
        limit_type: str
    ) -> Decimal:
        """Get thickness limit for equipment type"""
        limits = cls.THICKNESS_LIMITS.get(equipment_type, {})
        return limits.get(limit_type, Decimal("0"))
    
    @classmethod
    def get_maximum_inspection_interval(
        cls,
        equipment_type: EquipmentType,
        inspection_type: str,
        remaining_life: Decimal
    ) -> Decimal:
        """
        Get maximum allowed inspection interval per API codes.
        
        Returns the lesser of:
        - Code maximum interval
        - Half the remaining life
        - 10 years (absolute maximum for most equipment)
        """
        code_intervals = cls.MAXIMUM_INSPECTION_INTERVALS.get(equipment_type, {})
        code_maximum = Decimal(str(code_intervals.get(inspection_type, 10)))
        
        # API 510/570/653 requirement: interval cannot exceed half remaining life
        half_life = remaining_life / Decimal("2")
        
        # Take minimum of all constraints
        return min(code_maximum, half_life, Decimal("10"))
    
    @classmethod
    def get_corrosion_rate_range(
        cls,
        material: str,
        service: str
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Get typical, minimum, and maximum corrosion rates.
        
        Returns:
            Tuple of (typical, minimum, maximum) rates in inches/year
        """
        material_rates = cls.TYPICAL_CORROSION_RATES.get(material, {})
        typical = material_rates.get(service, Decimal("0.005"))
        
        # Industry practice: min = 50% of typical, max = 200% of typical
        minimum = typical * Decimal("0.5")
        maximum = typical * Decimal("2.0")
        
        return (typical, minimum, maximum)
    
    @classmethod
    def is_high_pressure(cls, pressure: Decimal) -> bool:
        """Check if pressure requires enhanced inspection/analysis"""
        return pressure > cls.PRESSURE_LIMITS["high_pressure_threshold"]
    
    @classmethod
    def is_creep_range(cls, temperature: Decimal, material: str) -> bool:
        """Check if temperature is in creep range for material"""
        if "carbon" in material.lower():
            threshold = cls.TEMPERATURE_LIMITS["creep_threshold_carbon"]
        elif "stainless" in material.lower():
            threshold = cls.TEMPERATURE_LIMITS["creep_threshold_stainless"]
        else:
            threshold = cls.TEMPERATURE_LIMITS["creep_threshold_low_alloy"]
        
        return temperature > threshold
    
    # TODO: [FEATURE] Add Level 2 and Level 3 assessment criteria
    # Implement geometry limits, stress concentration factors, and finite element thresholds
    # Required for comprehensive API 579 compliance beyond Level 1 assessments
