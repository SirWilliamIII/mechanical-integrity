"""
Inspection and measurement models for mechanical integrity management.

Designed for safety-critical API 579 compliance with full audit trail.
All thickness measurements use Decimal precision for regulatory accuracy.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, Float, ForeignKey, Text, JSON, DateTime, Boolean, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .equipment import Equipment


class InspectionType(str, Enum):
    """Standard inspection methods per API codes."""
    EXTERNAL = "EXTERNAL"  # Visual external inspection
    INTERNAL = "INTERNAL"  # Internal visual inspection
    UT = "UT"              # Ultrasonic thickness testing
    RT = "RT"              # Radiographic testing
    VT = "VT"              # Visual testing
    MT = "MT"              # Magnetic particle testing
    PT = "PT"              # Penetrant testing


class CorrosionType(str, Enum):
    """Types of corrosion patterns found."""
    UNIFORM = "UNIFORM"    # General uniform corrosion
    PITTING = "PITTING"    # Localized pitting corrosion
    CREVICE = "CREVICE"    # Crevice corrosion
    EROSION = "EROSION"    # Erosion-corrosion
    GALVANIC = "GALVANIC"  # Galvanic corrosion
    STRESS = "STRESS"      # Stress corrosion cracking


class InspectionRecord(Base, UUIDMixin, TimestampMixin):
    """
    Master inspection record with complete audit trail.
    
    This is the primary table for storing inspection events and calculated results.
    All fields align with API 579 fitness-for-service assessment requirements.
    """
    __tablename__ = "inspection_records"
    
    # ========================================================================
    # EQUIPMENT REFERENCE
    # ========================================================================
    equipment_id: Mapped[str] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"),
        index=True,
        comment="Reference to equipment being inspected"
    )
    equipment: Mapped["Equipment"] = relationship(
        back_populates="inspection_records",
        lazy="select"
    )
    
    # ========================================================================
    # INSPECTION METADATA
    # ========================================================================
    inspection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        comment="Date of inspection - critical for corrosion rate calculations"
    )
    inspection_type: Mapped[InspectionType] = mapped_column(
        String(20),
        comment="Inspection method used (UT, VT, etc.)"
    )
    inspector_name: Mapped[str] = mapped_column(
        String(100),
        comment="Certified inspector name for traceability"
    )
    inspector_certification: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Inspector certification number (SNT-TC-1A Level II/III)"
    )
    report_number: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="Unique inspection report identifier"
    )
    
    # ========================================================================
    # THICKNESS MEASUREMENTS - SAFETY CRITICAL
    # ========================================================================
    thickness_readings: Mapped[dict] = mapped_column(
        JSON,
        comment="Array of thickness readings with CML locations"
    )
    min_thickness_found: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Minimum thickness found - critical for fitness assessment"
    )
    avg_thickness: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Average thickness across all CMLs"
    )
    
    # ========================================================================
    # CORROSION ANALYSIS
    # ========================================================================
    corrosion_type: Mapped[Optional[CorrosionType]] = mapped_column(
        String(20),
        comment="Type of corrosion observed"
    )
    corrosion_rate_calculated: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=8, scale=5),
        comment="Calculated corrosion rate in inches/year"
    )
    confidence_level: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=5, scale=2),
        default=Decimal('75.00'),
        comment="Statistical confidence in corrosion rate (0-100%)"
    )
    
    # ========================================================================
    # FINDINGS AND RECOMMENDATIONS
    # ========================================================================
    findings: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Detailed inspection findings and observations"
    )
    recommendations: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Inspector recommendations for follow-up actions"
    )
    follow_up_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Flag indicating if immediate follow-up is required"
    )
    
    # ========================================================================
    # AI PROCESSING METADATA
    # ========================================================================
    ai_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this inspection was processed by AI document analyzer"
    )
    ai_extraction_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        comment="Raw AI extraction results for audit trail"
    )
    ai_confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=5, scale=2),
        comment="AI confidence score for extracted data (0-100%)"
    )
    
    # ========================================================================
    # VERIFICATION AND AUDIT TRAIL
    # ========================================================================
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Name of person who verified AI-extracted data"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Timestamp of human verification"
    )
    document_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Path to source inspection report/document"
    )
    
    # ========================================================================
    # RELATIONSHIPS
    # ========================================================================
    thickness_readings_detailed: Mapped[List["ThicknessReading"]] = relationship(
        back_populates="inspection_record",
        cascade="all, delete-orphan",
        lazy="select"
    )
    api579_calculations: Mapped[List["API579Calculation"]] = relationship(
        back_populates="inspection_record",
        cascade="all, delete-orphan",
        lazy="select"
    )


class ThicknessReading(Base, UUIDMixin, TimestampMixin):
    """
    Individual thickness measurement at a Condition Monitoring Location (CML).
    
    Each reading represents a precise ultrasonic thickness measurement
    used for corrosion rate calculations and remaining life assessment.
    """
    __tablename__ = "thickness_readings"
    
    # ========================================================================
    # PARENT INSPECTION
    # ========================================================================
    inspection_record_id: Mapped[str] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"),
        index=True,
        comment="Parent inspection record"
    )
    inspection_record: Mapped["InspectionRecord"] = relationship(
        back_populates="thickness_readings_detailed"
    )
    
    # ========================================================================
    # LOCATION IDENTIFICATION
    # ========================================================================
    cml_number: Mapped[str] = mapped_column(
        String(20),
        comment="Condition Monitoring Location identifier (e.g., CML-01)"
    )
    location_description: Mapped[str] = mapped_column(
        String(200),
        comment="Detailed description of measurement location"
    )
    grid_reference: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="Grid reference for location mapping (e.g., A-1, B-3)"
    )
    
    # ========================================================================
    # THICKNESS MEASUREMENTS - DECIMAL PRECISION REQUIRED
    # ========================================================================
    thickness_measured: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Current measured thickness in inches (±0.001 precision)"
    )
    previous_thickness: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Previous inspection thickness for corrosion rate calculation"
    )
    design_thickness: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Original design thickness at this location"
    )
    
    # ========================================================================
    # CALCULATED VALUES
    # ========================================================================
    metal_loss_total: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Total metal loss from original thickness (inches)"
    )
    metal_loss_period: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Metal loss since previous inspection (inches)"
    )
    corrosion_rate_local: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=8, scale=5),
        comment="Local corrosion rate at this CML (inches/year)"
    )
    
    # ========================================================================
    # MEASUREMENT QUALITY
    # ========================================================================
    measurement_confidence: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=5, scale=2),
        default=Decimal('95.00'),
        comment="Measurement confidence based on surface conditions"
    )
    surface_condition: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Surface condition affecting measurement accuracy"
    )
    temperature_compensation: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Temperature compensation applied to measurement"
    )


class API579Calculation(Base, UUIDMixin, TimestampMixin):
    """
    API 579 Fitness-for-Service calculation results.
    
    Stores complete calculation audit trail for regulatory compliance.
    All calculations must be traceable and reproducible.
    """
    __tablename__ = "api579_calculations"
    
    # ========================================================================
    # PARENT INSPECTION
    # ========================================================================
    inspection_record_id: Mapped[str] = mapped_column(
        ForeignKey("inspection_records.id", ondelete="CASCADE"),
        index=True,
        comment="Source inspection for this calculation"
    )
    inspection_record: Mapped["InspectionRecord"] = relationship(
        back_populates="api579_calculations"
    )
    
    # ========================================================================
    # CALCULATION METADATA
    # ========================================================================
    calculation_type: Mapped[str] = mapped_column(
        String(50),
        comment="Type of API 579 assessment (Level 1, 2, or 3)"
    )
    calculation_method: Mapped[str] = mapped_column(
        String(100),
        comment="Specific calculation method used"
    )
    performed_by: Mapped[str] = mapped_column(
        String(100),
        comment="Engineer who performed the calculation"
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Engineer who reviewed the calculation"
    )
    
    # ========================================================================
    # INPUT PARAMETERS - AUDIT TRAIL
    # ========================================================================
    input_parameters: Mapped[dict] = mapped_column(
        JSON,
        comment="Complete set of input parameters used in calculation"
    )
    
    # ========================================================================
    # CALCULATION RESULTS
    # ========================================================================
    minimum_required_thickness: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=6, scale=3),
        comment="Minimum required thickness (t_min) in inches"
    )
    remaining_strength_factor: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=6, scale=4),
        comment="Remaining Strength Factor (RSF) - critical safety metric"
    )
    maximum_allowable_pressure: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=8, scale=2),
        comment="Maximum Allowable Working Pressure (MAWP) in PSI"
    )
    remaining_life_years: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(precision=6, scale=2),
        comment="Estimated remaining life in years"
    )
    next_inspection_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Recommended next inspection date based on calculations"
    )
    
    # ========================================================================
    # SAFETY ASSESSMENTS
    # ========================================================================
    fitness_for_service: Mapped[str] = mapped_column(
        String(20),
        comment="Overall fitness assessment: FIT, UNFIT, or CONDITIONAL"
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        comment="Risk assessment: LOW, MEDIUM, HIGH, CRITICAL"
    )
    
    # ========================================================================
    # RECOMMENDATIONS AND WARNINGS
    # ========================================================================
    recommendations: Mapped[str] = mapped_column(
        Text,
        comment="Engineering recommendations based on calculations"
    )
    warnings: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Critical warnings requiring immediate attention"
    )
    assumptions: Mapped[dict] = mapped_column(
        JSON,
        comment="List of assumptions made in calculations"
    )
    
    # ========================================================================
    # CALCULATION CONFIDENCE
    # ========================================================================
    confidence_score: Mapped[Decimal] = mapped_column(
        DECIMAL(precision=5, scale=2),
        comment="Overall confidence in calculation results (0-100%)"
    )
    uncertainty_factors: Mapped[Optional[dict]] = mapped_column(
        JSON,
        comment="Factors contributing to calculation uncertainty"
    )