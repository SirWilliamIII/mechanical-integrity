"""
Equipment models for mechanical integrity management.

Defines equipment registry for petroleum industry assets with API 579 compliance data.
All design specifications are critical for fitness-for-service calculations.
"""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .inspection import InspectionRecord


class EquipmentType(str, Enum):
    """
    Equipment types per API standards for mechanical integrity assessment.
    
    Each type has specific inspection and calculation requirements under API 579.
    """
    PRESSURE_VESSEL = "pressure_vessel"  # API 510 - Pressure vessels
    STORAGE_TANK = "storage_tank"        # API 653 - Tank inspection
    PIPING = "piping"                    # API 570 - Piping inspection
    HEAT_EXCHANGER = "heat_exchanger"    # TEMA standards + API 579


class Equipment(Base, UUIDMixin, TimestampMixin):
    """
    Equipment master data for mechanical integrity management.
    
    Stores critical design specifications required for API 579 fitness-for-service
    calculations. All pressure, temperature, and thickness values are used in
    safety-critical calculations and must be validated.
    """
    __tablename__ = "equipment"
    
    # ========================================================================
    # IDENTIFICATION FIELDS
    # ========================================================================
    tag_number: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        index=True,
        comment="Unique equipment identifier (e.g., V-101, T-201)"
    )
    description: Mapped[str] = mapped_column(
        String(200),
        comment="Equipment description and service details"
    )
    equipment_type: Mapped[EquipmentType] = mapped_column(
        SQLEnum(EquipmentType),
        comment="Equipment classification per API standards"
    )
    
    # ========================================================================
    # DESIGN SPECIFICATIONS - CRITICAL FOR API 579 CALCULATIONS
    # ========================================================================
    design_pressure: Mapped[float] = mapped_column(
        Float,
        comment="Design pressure in PSI - used for MAWP calculations"
    )
    design_temperature: Mapped[float] = mapped_column(
        Float,
        comment="Design temperature in °F - affects material properties"
    )
    design_thickness: Mapped[float] = mapped_column(
        Float,
        comment="Original design thickness in inches - baseline for remaining life"
    )
    material_specification: Mapped[str] = mapped_column(
        String(50),
        comment="Material specification (e.g., SA-516-70, SA-106-B)"
    )
    
    # ========================================================================
    # CORROSION AND SERVICE PARAMETERS
    # ========================================================================
    corrosion_allowance: Mapped[float] = mapped_column(
        Float,
        default=0.125,
        comment="Design corrosion allowance in inches (typically 0.125)"
    )
    service_description: Mapped[str] = mapped_column(
        String(100),
        comment="Process service (e.g., Crude Oil, Steam, Cooling Water)"
    )
    installation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="Equipment installation date for age calculations"
    )
    
    # ========================================================================
    # INSPECTION TRACKING
    # ========================================================================
    last_inspection_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Date of most recent inspection"
    )
    next_inspection_due: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Next required inspection date per API standards"
    )
    
    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================
    inspection_records: Mapped[List["InspectionRecord"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan",
        lazy="select"
    )
