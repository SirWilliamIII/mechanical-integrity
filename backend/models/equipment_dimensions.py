"""
Equipment Dimensions Database for API 579 Compliance.
Safety-critical geometric data for accurate stress calculations.
"""

from decimal import Decimal
from typing import Optional
from enum import Enum
import uuid
from sqlalchemy import DECIMAL, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from models.base import BaseModel, GUID


class VesselOrientation(str, Enum):
    """Vessel orientation affects stress calculations."""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class HeadType(str, Enum):
    """Head types per ASME Section VIII."""
    ELLIPSOIDAL = "ellipsoidal"
    TORISPHERICAL = "torispherical"
    HEMISPHERICAL = "hemispherical"
    FLAT = "flat"
    CONICAL = "conical"


class EquipmentDimension(BaseModel):
    """
    Equipment dimensional data for accurate API 579 calculations.
    
    Critical geometric parameters that directly affect stress analysis
    and thickness requirements per API 579 Part 4.
    """
    __tablename__ = "equipment_dimensions"
    
    # Reference to equipment
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("equipment.id"),
        primary_key=True,
        comment="Equipment UUID reference"
    )
    
    # Primary dimensions (inches) - CRITICAL for stress calculations
    inside_diameter: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=8, scale=3),  # 99999.999 inches with ±0.001 precision
        nullable=True,
        comment="Inside diameter in inches - used for hoop stress calculations"
    )
    outside_diameter: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=8, scale=3),
        nullable=True,
        comment="Outside diameter in inches"
    )
    internal_radius: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=8, scale=3),
        nullable=True,
        comment="Internal radius in inches - CRITICAL for API 579 calculations"
    )
    
    # Length dimensions
    tangent_to_tangent_length: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=10, scale=3),  # Up to 9999999.999 inches
        nullable=True,
        comment="Tangent-to-tangent length in inches"
    )
    overall_length: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=10, scale=3),
        nullable=True,
        comment="Overall length including heads in inches"
    )
    
    # Vessel-specific geometry
    orientation: Mapped[Optional[VesselOrientation]] = mapped_column(
        nullable=True,
        comment="Vessel orientation affects stress distribution"
    )
    head_type_top: Mapped[Optional[HeadType]] = mapped_column(
        nullable=True,
        comment="Top head type per ASME Section VIII"
    )
    head_type_bottom: Mapped[Optional[HeadType]] = mapped_column(
        nullable=True,
        comment="Bottom head type per ASME Section VIII"
    )
    
    # Head dimensions (if applicable)
    head_thickness_top: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=3),
        nullable=True,
        comment="Top head thickness in inches"
    )
    head_thickness_bottom: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=3),
        nullable=True,
        comment="Bottom head thickness in inches"
    )
    
    # Piping-specific dimensions
    nominal_pipe_size: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="NPS per ASME B36.10 (e.g., '6', '8', '12')"
    )
    schedule: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Pipe schedule per ASME B36.10 (e.g., '40', '80', 'STD', 'XS')"
    )
    
    # Weight and volume
    empty_weight_lbs: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=10, scale=1),
        nullable=True,
        comment="Empty weight in pounds"
    )
    operating_weight_lbs: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=10, scale=1),
        nullable=True,
        comment="Operating weight in pounds"
    )
    internal_volume_cf: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=10, scale=3),
        nullable=True,
        comment="Internal volume in cubic feet"
    )
    
    # Support and nozzle information
    support_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Support type (e.g., 'legs', 'skirt', 'saddles', 'lugs')"
    )
    nozzle_count: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Number of nozzles for stress concentration analysis"
    )
    largest_nozzle_diameter: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=8, scale=3),
        nullable=True,
        comment="Largest nozzle diameter in inches"
    )
    
    # Manufacturing and inspection data
    fabrication_year: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Year of fabrication"
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Equipment manufacturer"
    )
    asme_code_year: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="ASME code year used for design"
    )
    
    # Verification and notes
    dimensions_verified: Mapped[bool] = mapped_column(
        default=False,
        comment="Whether dimensions have been field-verified"
    )
    verification_method: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Method used to verify dimensions (e.g., 'drawing review', 'field measurement')"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional dimensional notes or assumptions"
    )


class EquipmentDimensionService:
    """
    Service for managing equipment dimensions and calculating derived parameters.
    
    Provides safety-critical geometric calculations per API 579 requirements.
    """
    
    @staticmethod
    def calculate_internal_radius(
        inside_diameter: Optional[Decimal] = None,
        outside_diameter: Optional[Decimal] = None,
        wall_thickness: Optional[Decimal] = None
    ) -> Optional[Decimal]:
        """
        Calculate internal radius from available dimensions.
        
        Args:
            inside_diameter: Inside diameter in inches
            outside_diameter: Outside diameter in inches  
            wall_thickness: Current wall thickness in inches
            
        Returns:
            Internal radius in inches, or None if insufficient data
        """
        if inside_diameter:
            return inside_diameter / Decimal('2')
        elif outside_diameter and wall_thickness:
            inside_diameter = outside_diameter - (wall_thickness * Decimal('2'))
            return inside_diameter / Decimal('2')
        else:
            return None
    
    @staticmethod
    def validate_dimensions(dimensions: EquipmentDimension) -> list[str]:
        """
        Validate equipment dimensions for API 579 compliance.
        
        Args:
            dimensions: Equipment dimension record
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for minimum required dimensions
        if not dimensions.internal_radius and not dimensions.inside_diameter:
            if not (dimensions.outside_diameter and dimensions.head_thickness_top):
                errors.append("Internal radius or inside diameter required for stress calculations")
        
        # Validate dimension relationships
        if dimensions.inside_diameter and dimensions.outside_diameter:
            if dimensions.inside_diameter >= dimensions.outside_diameter:
                errors.append("Inside diameter cannot be greater than or equal to outside diameter")
        
        # Check for reasonable values
        if dimensions.internal_radius and dimensions.internal_radius <= Decimal('0'):
            errors.append("Internal radius must be positive")
            
        if dimensions.inside_diameter and dimensions.inside_diameter <= Decimal('0'):
            errors.append("Inside diameter must be positive")
        
        # API 579 geometric limits
        if dimensions.internal_radius and dimensions.internal_radius > Decimal('600'):
            errors.append("Internal radius exceeds typical API 579 application range (>600 inches)")
            
        return errors
    
    @staticmethod
    def estimate_dimensions_from_nps(nps: str, schedule: str) -> dict:
        """
        Estimate pipe dimensions from NPS and schedule per ASME B36.10.
        
        Args:
            nps: Nominal pipe size (e.g., "6", "8", "12")
            schedule: Pipe schedule (e.g., "40", "80", "STD", "XS")
            
        Returns:
            Dictionary with estimated dimensions
        """
        # Common pipe dimensions per ASME B36.10
        pipe_data = {
            # NPS: {schedule: (OD, wall_thickness)}
            "6": {
                "STD": (6.625, 0.280),
                "40": (6.625, 0.280),
                "XS": (6.625, 0.432),
                "80": (6.625, 0.432),
            },
            "8": {
                "STD": (8.625, 0.322),
                "40": (8.625, 0.322),
                "XS": (8.625, 0.500),
                "80": (8.625, 0.500),
            },
            "12": {
                "STD": (12.75, 0.375),
                "40": (12.75, 0.406),
                "XS": (12.75, 0.562),
                "80": (12.75, 0.562),
            }
        }
        
        if nps not in pipe_data or schedule not in pipe_data[nps]:
            return {"error": f"Unknown NPS {nps} Schedule {schedule} combination"}
        
        od, wall_thickness = pipe_data[nps][schedule]
        id_inches = od - (2 * wall_thickness)
        internal_radius = id_inches / 2
        
        return {
            "outside_diameter": Decimal(str(od)),
            "inside_diameter": Decimal(str(id_inches)),
            "internal_radius": Decimal(str(internal_radius)),
            "wall_thickness": Decimal(str(wall_thickness)),
            "source": "ASME_B36_10"
        }