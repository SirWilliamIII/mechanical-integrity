"""
Safety-Critical Inspection API for Mechanical Integrity Management.

This module implements API 579 compliant inspection endpoints with full audit trail,
decimal precision calculations, and comprehensive validation for regulatory compliance.

Key Safety Features:
- Decimal precision for all thickness measurements (±0.001 inches)
- Complete audit trail for regulatory requirements
- Conservative calculations with safety factors
- Human verification workflow for AI-processed data
- Fail-fast validation with detailed error messages
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict
from pydantic.types import UUID4

from models.database import get_db
from models import (
    InspectionRecord, 
    ThicknessReading, 
    API579Calculation, 
    Equipment,
    InspectionType,
    CorrosionType
)

# Configure logger for audit trail
logger = logging.getLogger("mechanical_integrity.inspections")

router = APIRouter(tags=["Inspections"])


# ========================================================================
# HELPER FUNCTIONS FOR CALCULATIONS
# ========================================================================

def _calculate_confidence_level(
    thickness_reading_count: int,
    has_historical_data: bool = False
) -> Decimal:
    """
    Calculate inspection confidence level based on reading count and historical data.
    
    Args:
        thickness_reading_count: Number of thickness measurements taken
        has_historical_data: Whether previous inspection data is available
        
    Returns:
        Confidence level as Decimal (0-100)
    """
    base_confidence = Decimal("75.0")
    
    # Increase confidence with more readings
    if thickness_reading_count >= 10:
        base_confidence = Decimal("90.0")
    elif thickness_reading_count >= 5:
        base_confidence = Decimal("85.0")
    elif thickness_reading_count >= 3:
        base_confidence = Decimal("80.0")
    
    # Adjust for historical data availability
    if has_historical_data:
        base_confidence = min(base_confidence + Decimal("5.0"), Decimal("95.0"))
    else:
        base_confidence = max(base_confidence - Decimal("5.0"), Decimal("60.0"))
    
    return base_confidence


def _calculate_corrosion_metrics(
    current_min_thickness: Decimal,
    previous_inspection: Optional[InspectionRecord],
    current_inspection_date: datetime
) -> tuple[Optional[Decimal], bool]:
    """
    Calculate corrosion rate from historical inspection data.
    
    Args:
        current_min_thickness: Current minimum thickness measurement
        previous_inspection: Previous inspection record if available
        current_inspection_date: Date of current inspection
        
    Returns:
        Tuple of (corrosion_rate, has_historical_data)
    """
    if not previous_inspection or not previous_inspection.min_thickness_found:
        return None, False
    
    thickness_loss = previous_inspection.min_thickness_found - current_min_thickness
    time_years = (current_inspection_date - previous_inspection.inspection_date).days / Decimal("365.25")
    
    if time_years > 0 and thickness_loss > 0:
        corrosion_rate = thickness_loss / time_years
        logger.info(f"Calculated corrosion rate: {corrosion_rate} in/year over {time_years} years")
        return corrosion_rate, True
    
    return None, True  # Has historical data but no measurable corrosion


# ========================================================================
# CUSTOM EXCEPTIONS FOR SAFETY-CRITICAL OPERATIONS
# ========================================================================

class InspectionNotFound(HTTPException):
    def __init__(self, inspection_id: UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection record {inspection_id} not found"
        )


class EquipmentNotFound(HTTPException):
    def __init__(self, equipment_id: UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment {equipment_id} not found or inactive"
        )


class SafetyCriticalValidationError(HTTPException):
    def __init__(self, detail: str, field: str = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"SAFETY CRITICAL VALIDATION ERROR: {detail}",
            headers={"X-Safety-Critical": "true", "X-Field-Error": field or "unknown"}
        )


class InsufficientDataError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient data for API 579 calculations: {detail}"
        )


# ========================================================================
# PYDANTIC SCHEMAS WITH SAFETY-CRITICAL VALIDATION
# ========================================================================

class ThicknessReadingCreate(BaseModel):
    """Individual thickness measurement with safety-critical validation."""
    model_config = ConfigDict(
        str_strip_whitespace=True
    )
    
    @field_serializer('thickness_measured', 'design_thickness', 'previous_thickness', when_used='json')
    def serialize_decimal_fields(self, value: Optional[Decimal]) -> Optional[str]:
        """Convert Decimal thickness fields to string for JSON serialization."""
        return str(value) if value is not None else None
    
    cml_number: str = Field(
        ..., 
        min_length=1, 
        max_length=20,
        pattern=r"^[A-Z0-9\-]+$",
        description="Condition Monitoring Location identifier (e.g., CML-01)"
    )
    location_description: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Detailed description of measurement location"
    )
    thickness_measured: Decimal = Field(
        ..., 
        ge=Decimal("0.001"), 
        le=Decimal("10.000"),
        description="Current measured thickness in inches (±0.001 precision)"
    )
    design_thickness: Decimal = Field(
        ..., 
        ge=Decimal("0.001"), 
        le=Decimal("10.000"),
        description="Original design thickness at this location"
    )
    previous_thickness: Optional[Decimal] = Field(
        None,
        ge=Decimal("0.001"), 
        le=Decimal("10.000"),
        description="Previous inspection thickness for corrosion rate calculation"
    )
    grid_reference: Optional[str] = Field(
        None,
        max_length=10,
        pattern=r"^[A-Z]\-[0-9]+$",
        description="Grid reference for location mapping (e.g., A-1, B-3)"
    )
    surface_condition: Optional[str] = Field(
        None,
        max_length=50,
        description="Surface condition affecting measurement accuracy"
    )
    
    @field_validator("thickness_measured", "design_thickness", "previous_thickness")
    @classmethod
    def validate_thickness_precision(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure thickness measurements have proper precision for safety calculations."""
        if v is None:
            return v
            
        # Validate precision to 3 decimal places (±0.001 inches)
        if v.as_tuple().exponent < -3:
            raise ValueError("Thickness precision cannot exceed ±0.001 inches for regulatory compliance")
            
        # Check for reasonable thickness values
        if v <= Decimal("0"):
            raise ValueError("Thickness must be greater than 0.000 inches")
            
        return v
    
    @field_validator("thickness_measured")
    @classmethod
    def validate_thickness_vs_design(cls, v: Decimal, info) -> Decimal:
        """Validate that measured thickness is reasonable compared to design."""
        if "design_thickness" in info.data:
            design = info.data["design_thickness"]
            if v > design * Decimal("1.1"):  # Allow 10% tolerance for measurement variation
                logger.warning(f"Measured thickness {v} exceeds design thickness {design} by more than 10%")
                # Don't fail, but log for review
        return v


class InspectionRecordCreate(BaseModel):
    """Schema for creating inspection records with comprehensive validation."""
    model_config = ConfigDict(
        str_strip_whitespace=True
    )
    
    equipment_id: str = Field(..., description="Equipment UUID or tag number (e.g., 'V-101' or UUID)")
    inspection_date: datetime = Field(..., description="Date of inspection")
    inspection_type: InspectionType = Field(..., description="Inspection method used")
    inspector_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Certified inspector name for traceability"
    )
    inspector_certification: Optional[str] = Field(
        None,
        max_length=50,
        pattern=r"^[A-Z0-9\-\/\s]+$",
        description="Inspector certification number (SNT-TC-1A Level II/III)"
    )
    report_number: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Unique inspection report identifier"
    )
    
    thickness_readings: List[ThicknessReadingCreate] = Field(
        ..., 
        min_length=1,
        description="At least one thickness reading required"
    )
    
    corrosion_type: Optional[CorrosionType] = Field(
        None,
        description="Type of corrosion observed"
    )
    findings: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed inspection findings and observations"
    )
    recommendations: Optional[str] = Field(
        None,
        max_length=2000,
        description="Inspector recommendations for follow-up actions"
    )
    follow_up_required: bool = Field(
        default=False,
        description="Flag indicating if immediate follow-up is required"
    )
    
    @field_validator("inspection_date")
    @classmethod
    def validate_inspection_date(cls, v: datetime) -> datetime:
        """Validate inspection date is reasonable."""
        # Handle timezone-aware and naive datetimes
        if v.tzinfo is not None:
            # Convert to UTC and make naive for comparison
            now = datetime.utcnow()
            v_utc = v.utctimetuple()
            v_naive = datetime(*v_utc[:6])
        else:
            now = datetime.now()
            v_naive = v
        
        if v_naive > now:
            raise ValueError("Inspection date cannot be in the future")
        if v_naive < now - timedelta(days=365 * 10):  # 10 years ago
            raise ValueError("Inspection date cannot be more than 10 years old")
        return v
    
    @field_validator("thickness_readings")
    @classmethod
    def validate_thickness_readings(cls, v: List[ThicknessReadingCreate]) -> List[ThicknessReadingCreate]:
        """Validate thickness readings for safety-critical requirements."""
        if not v:
            raise ValueError("At least one thickness reading is required for API 579 compliance")
        
        # Check for duplicate CML numbers
        cml_numbers = [reading.cml_number for reading in v]
        if len(cml_numbers) != len(set(cml_numbers)):
            raise ValueError("Duplicate CML numbers found - each location must be unique")
        
        # Validate minimum number of readings for statistical significance
        if len(v) < 3:
            logger.warning(f"Only {len(v)} thickness readings provided - minimum 3 recommended for statistical confidence")
        
        return v


class InspectionRecordResponse(BaseModel):
    """Response schema with calculated fields and audit information."""
    model_config = ConfigDict(
        from_attributes=True
    )
    
    @field_serializer('min_thickness_found', 'avg_thickness', 'corrosion_rate_calculated', 
                     'confidence_level', 'ai_confidence_score', when_used='json')
    def serialize_decimal_fields(self, value: Optional[Decimal]) -> Optional[str]:
        """Convert Decimal fields to string for JSON serialization."""
        return str(value) if value is not None else None
    
    @field_serializer('id', when_used='json')
    def serialize_uuid(self, value: UUID) -> str:
        """Convert UUID to string for JSON serialization."""
        return str(value)
    
    @field_serializer('inspection_date', 'verified_at', 'created_at', 'updated_at', when_used='json')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Convert datetime to ISO format for JSON serialization."""
        return value.isoformat() if value is not None else None
    
    id: UUID4
    equipment_id: str
    inspection_date: datetime
    inspection_type: InspectionType
    inspector_name: str
    inspector_certification: Optional[str]
    report_number: str
    
    # Calculated thickness fields
    min_thickness_found: Decimal
    avg_thickness: Decimal
    
    # Corrosion analysis
    corrosion_type: Optional[CorrosionType]
    corrosion_rate_calculated: Optional[Decimal]
    confidence_level: Decimal
    
    # Audit fields
    ai_processed: bool
    ai_confidence_score: Optional[Decimal]
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    
    # Related data counts
    thickness_readings_count: Optional[int] = None
    calculations_count: Optional[int] = None


class ThicknessReadingBulkCreate(BaseModel):
    """Schema for adding thickness readings to existing inspection."""
    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: str(v)},
        str_strip_whitespace=True
    )
    
    readings: List[ThicknessReadingCreate] = Field(
        ..., 
        min_length=1,
        max_length=100,  # Reasonable limit per batch
        description="List of thickness readings to add"
    )
    operator_notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional notes from the operator"
    )


class API579CalculationResponse(BaseModel):
    """Response schema for API 579 calculation results."""
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: str(v),
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }
    )
    
    id: UUID4
    inspection_record_id: UUID4
    calculation_type: str
    calculation_method: str
    performed_by: str
    
    # Input parameters (for audit trail)
    input_parameters: Dict[str, Any]
    
    # Results
    minimum_required_thickness: Decimal
    remaining_strength_factor: Decimal
    maximum_allowable_pressure: Decimal
    remaining_life_years: Optional[Decimal]
    next_inspection_date: Optional[datetime]
    
    # Safety assessments
    fitness_for_service: str
    risk_level: str
    
    # Recommendations
    recommendations: str
    warnings: Optional[str]
    assumptions: Dict[str, Any]
    
    # Confidence
    confidence_score: Decimal
    uncertainty_factors: Optional[Dict[str, Any]]
    
    created_at: datetime


# ========================================================================
# FASTAPI DEPENDENCIES FOR SAFETY-CRITICAL VALIDATION
# ========================================================================

def get_equipment_by_id_or_tag(equipment_identifier: str, db: Session) -> Equipment:
    """Get equipment by UUID or tag number."""
    # Try UUID first
    try:
        equipment = db.query(Equipment).filter(Equipment.id == str(equipment_identifier)).first()
        if equipment:
            return equipment
    except (ValueError, SQLAlchemyError):
        # Invalid UUID format or database error - fall through to tag lookup
        pass
    
    # Try tag number
    equipment = db.query(Equipment).filter(Equipment.tag_number == equipment_identifier).first()
    if equipment:
        return equipment
    
    # Not found
    logger.error(f"Equipment validation failed: {equipment_identifier} not found")
    raise EquipmentNotFound(equipment_identifier)


async def valid_inspection_id(inspection_id: UUID4, db: Session = Depends(get_db)) -> InspectionRecord:
    """Validate inspection record exists."""
    inspection = db.query(InspectionRecord).filter(InspectionRecord.id == str(inspection_id)).first()
    if not inspection:
        logger.error(f"Inspection validation failed: {inspection_id} not found")
        raise InspectionNotFound(inspection_id)
    
    logger.info(f"Inspection validation passed: {inspection.report_number} ({inspection_id})")
    return inspection


# ========================================================================
# API ENDPOINTS
# ========================================================================

@router.post("/", 
             response_model=InspectionRecordResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create New Inspection Record",
             description="Create a new inspection record with thickness measurements and automatic calculations")
async def create_inspection_record(
    inspection_data: InspectionRecordCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create new inspection record with complete safety-critical validation.
    
    This endpoint:
    - Validates all input data against API 579 requirements
    - Calculates thickness statistics with Decimal precision
    - Computes corrosion rates from historical data
    - Updates equipment inspection tracking
    - Logs all operations for audit trail
    """
    try:
        # Validate equipment exists
        equipment = get_equipment_by_id_or_tag(inspection_data.equipment_id, db)
        logger.info(f"Creating inspection for equipment {equipment.tag_number}")
        
        # Extract and validate thickness measurements
        thickness_values = [reading.thickness_measured for reading in inspection_data.thickness_readings]
        min_thickness = min(thickness_values)
        avg_thickness = sum(thickness_values) / len(thickness_values)
        
        # Calculate corrosion metrics from historical data
        previous_inspection = db.query(InspectionRecord).filter(
            InspectionRecord.equipment_id == str(equipment.id),
            InspectionRecord.inspection_date < inspection_data.inspection_date
        ).order_by(InspectionRecord.inspection_date.desc()).first()
        
        corrosion_rate, has_historical_data = _calculate_corrosion_metrics(
            min_thickness, previous_inspection, inspection_data.inspection_date
        )
        
        # Calculate confidence level based on reading count and historical data
        confidence_level = _calculate_confidence_level(
            len(thickness_values), has_historical_data
        )
        
        # Create main inspection record
        db_inspection = InspectionRecord(
            equipment_id=str(equipment.id),
            inspection_date=inspection_data.inspection_date,
            inspection_type=inspection_data.inspection_type,
            inspector_name=inspection_data.inspector_name,
            inspector_certification=inspection_data.inspector_certification,
            report_number=inspection_data.report_number,
            thickness_readings=[reading.model_dump(mode='json') for reading in inspection_data.thickness_readings],
            min_thickness_found=min_thickness,
            avg_thickness=avg_thickness,
            corrosion_type=inspection_data.corrosion_type,
            corrosion_rate_calculated=corrosion_rate,
            confidence_level=confidence_level,
            findings=inspection_data.findings,
            recommendations=inspection_data.recommendations,
            follow_up_required=inspection_data.follow_up_required,
            ai_processed=False
        )
        
        db.add(db_inspection)
        db.flush()  # Flush to get the inspection ID before creating thickness readings
        
        # Create detailed thickness readings
        for reading_data in inspection_data.thickness_readings:
            db_reading = ThicknessReading(
                inspection_record_id=db_inspection.id,
                cml_number=reading_data.cml_number,
                location_description=reading_data.location_description,
                thickness_measured=reading_data.thickness_measured,
                design_thickness=reading_data.design_thickness,
                previous_thickness=reading_data.previous_thickness,
                grid_reference=reading_data.grid_reference,
                surface_condition=reading_data.surface_condition,
                metal_loss_total=reading_data.design_thickness - reading_data.thickness_measured if reading_data.design_thickness else None,
                metal_loss_period=reading_data.previous_thickness - reading_data.thickness_measured if reading_data.previous_thickness else None
            )
            db.add(db_reading)
        
        # Update equipment tracking
        equipment.last_inspection_date = inspection_data.inspection_date
        
        # Calculate next inspection due date using API 653 methodology
        if corrosion_rate and corrosion_rate > 0:
            t_minimum = equipment.design_thickness * Decimal("0.5")  # 50% as minimum threshold
            remaining_allowance = min_thickness - t_minimum
            
            if remaining_allowance > 0:
                # API 653: interval = (t_current - t_minimum) / (2 * corrosion_rate)
                interval_years = remaining_allowance / (2 * corrosion_rate)
                interval_years = min(interval_years, Decimal("5"))  # Max 5 years per API standards
                interval_years = max(interval_years, Decimal("1"))  # Min 1 year
                
                equipment.next_inspection_due = inspection_data.inspection_date + timedelta(
                    days=int(interval_years * 365)
                )
                
                logger.info(f"Next inspection due: {equipment.next_inspection_due}")
        
        # Commit transaction
        db.commit()
        db.refresh(db_inspection)
        
        # Schedule background calculations
        background_tasks.add_task(
            trigger_api579_calculations,
            inspection_id=db_inspection.id,
            equipment_id=equipment.id
        )
        
        logger.info(f"Inspection {db_inspection.id} created successfully")
        
        # Prepare response with additional counts
        response_data = InspectionRecordResponse.model_validate(db_inspection)
        response_data.thickness_readings_count = len(inspection_data.thickness_readings)
        response_data.calculations_count = 0  # Will be updated by background task
        
        return response_data
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating inspection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during inspection creation"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating inspection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during inspection creation"
        )


@router.post("/{inspection_id}/thickness-readings",
             response_model=Dict[str, Any],
             summary="Add Thickness Readings to Existing Inspection",
             description="Add additional thickness readings to an existing inspection record")
async def add_thickness_readings(
    inspection_id: UUID4,
    readings_data: ThicknessReadingBulkCreate,
    background_tasks: BackgroundTasks,
    inspection: InspectionRecord = Depends(valid_inspection_id),
    db: Session = Depends(get_db)
):
    """
    Add thickness readings to an existing inspection record.
    
    This endpoint:
    - Validates inspection exists and is modifiable
    - Adds new thickness readings with full validation
    - Recalculates inspection statistics
    - Updates corrosion analysis
    - Triggers background recalculations
    """
    try:
        logger.info(f"Adding {len(readings_data.readings)} thickness readings to inspection {inspection_id}")
        
        # Validate inspection is not locked (e.g., verified)
        if inspection.verified_by:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot modify thickness readings on verified inspection record"
            )
        
        # Check for duplicate CML numbers with existing readings
        existing_cmls = {reading["cml_number"] for reading in inspection.thickness_readings}
        new_cmls = {reading.cml_number for reading in readings_data.readings}
        
        duplicates = existing_cmls.intersection(new_cmls)
        if duplicates:
            raise SafetyCriticalValidationError(
                f"CML numbers already exist in this inspection: {', '.join(duplicates)}",
                field="cml_number"
            )
        
        # Add new thickness readings
        new_readings = []
        for reading_data in readings_data.readings:
            db_reading = ThicknessReading(
                inspection_record_id=str(inspection_id),
                cml_number=reading_data.cml_number,
                location_description=reading_data.location_description,
                thickness_measured=reading_data.thickness_measured,
                design_thickness=reading_data.design_thickness,
                previous_thickness=reading_data.previous_thickness,
                grid_reference=reading_data.grid_reference,
                surface_condition=reading_data.surface_condition,
                metal_loss_total=reading_data.design_thickness - reading_data.thickness_measured if reading_data.design_thickness else None,
                metal_loss_period=reading_data.previous_thickness - reading_data.thickness_measured if reading_data.previous_thickness else None
            )
            db.add(db_reading)
            new_readings.append(db_reading)
        
        # Recalculate inspection statistics
        all_thickness_readings = list(inspection.thickness_readings) + [r.model_dump() for r in readings_data.readings]
        all_thickness_values = [Decimal(str(r["thickness_measured"])) if isinstance(r, dict) else r.thickness_measured for r in all_thickness_readings]
        
        inspection.min_thickness_found = min(all_thickness_values)
        inspection.avg_thickness = sum(all_thickness_values) / len(all_thickness_values)
        inspection.thickness_readings = [r.model_dump() if hasattr(r, 'model_dump') else r for r in all_thickness_readings]
        
        # Update confidence level based on new reading count
        total_readings = len(all_thickness_values)
        if total_readings >= 10:
            inspection.confidence_level = Decimal("95.0")
        elif total_readings >= 5:
            inspection.confidence_level = Decimal("85.0")
        else:
            inspection.confidence_level = Decimal("70.0")
        
        db.commit()
        
        # Schedule background recalculations
        background_tasks.add_task(
            trigger_api579_calculations,
            inspection_id=inspection_id,
            equipment_id=UUID4(inspection.equipment_id),
            recalculate=True
        )
        
        logger.info(f"Added {len(new_readings)} thickness readings to inspection {inspection_id}")
        
        return {
            "message": f"Successfully added {len(new_readings)} thickness readings",
            "inspection_id": str(inspection_id),
            "new_readings_count": len(new_readings),
            "total_readings_count": total_readings,
            "updated_statistics": {
                "min_thickness_found": float(inspection.min_thickness_found),
                "avg_thickness": float(inspection.avg_thickness),
                "confidence_level": float(inspection.confidence_level)
            },
            "operator_notes": readings_data.operator_notes
        }
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error adding thickness readings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while adding thickness readings"
        )


@router.get("/{inspection_id}/calculations",
            response_model=List[API579CalculationResponse],
            summary="Get API 579 Calculations for Inspection",
            description="Retrieve all API 579 fitness-for-service calculations for an inspection")
async def get_inspection_calculations(
    inspection_id: UUID4,
    inspection: InspectionRecord = Depends(valid_inspection_id),
    db: Session = Depends(get_db)
):
    """
    Get all API 579 calculations for an inspection record.
    
    Returns complete calculation results including:
    - Input parameters for audit trail
    - Remaining strength factor and life estimates
    - Safety assessments and recommendations
    - Confidence scores and uncertainty factors
    """
    try:
        calculations = db.query(API579Calculation).filter(
            API579Calculation.inspection_record_id == str(inspection_id)
        ).order_by(API579Calculation.created_at.desc()).all()
        
        logger.info(f"Retrieved {len(calculations)} calculations for inspection {inspection_id}")
        
        return [API579CalculationResponse.model_validate(calc) for calc in calculations]
        
    except Exception as e:
        logger.error(f"Error retrieving calculations for inspection {inspection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving calculation results"
        )


@router.get("/{inspection_id}",
            response_model=InspectionRecordResponse,
            summary="Get Inspection Record by ID",
            description="Retrieve detailed inspection record with all associated data")
async def get_inspection_record(
    inspection_id: UUID4,
    inspection: InspectionRecord = Depends(valid_inspection_id),
    db: Session = Depends(get_db)
):
    """Get detailed inspection record by ID."""
    try:
        # Count related records
        thickness_count = len(inspection.thickness_readings_detailed)
        calculations_count = db.query(API579Calculation).filter(
            API579Calculation.inspection_record_id == str(inspection_id)
        ).count()
        
        response_data = InspectionRecordResponse.model_validate(inspection)
        response_data.thickness_readings_count = thickness_count
        response_data.calculations_count = calculations_count
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error retrieving inspection {inspection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving inspection record"
        )


@router.get("/equipment/{equipment_id}",
            response_model=List[InspectionRecordResponse],
            summary="Get All Inspections for Equipment",
            description="Retrieve all inspection records for a specific equipment, ordered by date (newest first)")
async def get_equipment_inspections(
    equipment_id: UUID4,
    db: Session = Depends(get_db)
):
    """
    Get all inspection records for a specific equipment.
    
    Returns inspections ordered by inspection date (newest first) with:
    - Complete inspection record data
    - Thickness reading counts
    - Associated calculation counts
    - Verification status
    """
    try:
        # Verify equipment exists
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment with id '{equipment_id}' not found"
            )
        
        # Get all inspections for the equipment
        inspections = db.query(InspectionRecord).filter(
            InspectionRecord.equipment_id == equipment_id
        ).order_by(InspectionRecord.inspection_date.desc()).all()
        
        # Build response with counts
        response_data = []
        for inspection in inspections:
            inspection_response = InspectionRecordResponse.model_validate(inspection)
            
            # Add counts
            inspection_response.thickness_readings_count = len(inspection.thickness_readings_detailed)
            inspection_response.calculations_count = db.query(API579Calculation).filter(
                API579Calculation.inspection_record_id == str(inspection.id)
            ).count()
            
            response_data.append(inspection_response)
        
        logger.info(f"Retrieved {len(inspections)} inspections for equipment {equipment_id}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving inspections for equipment {equipment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving equipment inspections"
        )


@router.post("/{inspection_id}/verify",
            response_model=InspectionRecordResponse,
            summary="Verify Inspection Record",
            description="Human verification of inspection record with audit trail for regulatory compliance")
async def verify_inspection(
    inspection_id: UUID4,
    verifier_name: str,
    notes: Optional[str] = None,
    inspection: InspectionRecord = Depends(valid_inspection_id),
    db: Session = Depends(get_db)
):
    """
    Mark an inspection record as verified by a human expert.
    
    This endpoint provides critical human oversight for safety-critical calculations,
    especially for AI-processed inspection data that requires regulatory validation.
    
    Args:
        inspection_id: UUID of the inspection record
        verifier_name: Name and credentials of the verifying engineer
        notes: Optional verification notes for audit trail
        inspection: Inspection record from dependency
        db: Database session
        
    Returns:
        Complete inspection record with verification audit trail
        
    Raises:
        404: If inspection record not found
        400: If inspection already verified
        422: If verification data invalid
    """
    try:
        
        # Check if already verified
        if inspection.verified_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inspection {inspection_id} already verified by {inspection.verified_by}"
            )
        
        # Update verification fields
        inspection.verified_by = verifier_name
        inspection.verified_at = datetime.utcnow()
        
        # Add verification notes to findings if provided
        if notes:
            if inspection.findings:
                inspection.findings += f"\n\nVerification Notes: {notes}"
            else:
                inspection.findings = f"Verification Notes: {notes}"
        
        db.commit()
        db.refresh(inspection)
        
        # Build response with counts
        response = InspectionRecordResponse.model_validate(inspection)
        response.thickness_readings_count = len(inspection.thickness_readings_detailed)
        response.calculations_count = db.query(API579Calculation).filter(
            API579Calculation.inspection_record_id == str(inspection.id)
        ).count()
        
        logger.info(f"Inspection {inspection_id} verified by {verifier_name}")
        
        return response
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error verifying inspection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying inspection record"
        )


class CorrosionAnalysisResponse(BaseModel):
    """Response schema for corrosion analysis results."""
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: str(v),
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }
    )
    
    equipment_id: str
    inspection_id: str
    current_min_thickness: float
    corrosion_rate: Optional[float]
    remaining_life: Optional[float]
    confidence_level: float
    calculation_method: str
    assumptions: List[str]
    warnings: List[str]
    analysis_date: datetime


@router.post("/{inspection_id}/analyze-corrosion",
            response_model=CorrosionAnalysisResponse,
            summary="Analyze Corrosion Trends",
            description="Perform corrosion analysis with historical data for remaining life assessment")
async def analyze_corrosion(
    inspection_id: UUID4,
    current_inspection: InspectionRecord = Depends(valid_inspection_id),
    db: Session = Depends(get_db)
):
    """
    Analyze corrosion trends using historical inspection data.
    
    This endpoint performs time-based corrosion analysis using inspection history
    to calculate corrosion rates and estimate remaining equipment life according
    to API 579 fitness-for-service principles.
    
    Args:
        inspection_id: UUID of the current inspection record
        current_inspection: Current inspection record from dependency
        db: Database session
        
    Returns:
        Corrosion analysis results with remaining life estimates
        
    Raises:
        404: If inspection record not found
        422: If insufficient data for analysis
    """
    try:
        
        # Get equipment information
        equipment = db.query(Equipment).filter(
            Equipment.id == current_inspection.equipment_id
        ).first()
        
        if not equipment:
            raise EquipmentNotFound(current_inspection.equipment_id)
        
        # Get historical inspections for this equipment
        historical_inspections = db.query(InspectionRecord).filter(
            InspectionRecord.equipment_id == current_inspection.equipment_id,
            InspectionRecord.inspection_date < current_inspection.inspection_date,
            InspectionRecord.id != current_inspection.id
        ).order_by(InspectionRecord.inspection_date.desc()).all()
        
        # Initialize response data
        assumptions = ["Uniform corrosion pattern assumed"]
        warnings = []
        corrosion_rate = None
        remaining_life = None
        calculation_method = "Single point analysis - no historical data"
        
        # Calculate confidence level based on thickness readings and historical data
        thickness_reading_count = len(current_inspection.thickness_readings_detailed) if current_inspection.thickness_readings_detailed else 0
        has_historical_data = len(historical_inspections) > 0
        confidence_level = float(_calculate_confidence_level(thickness_reading_count, has_historical_data))
        
        # Calculate corrosion rate if historical data exists
        if historical_inspections:
            previous_inspection = historical_inspections[0]
            
            # Calculate time difference in years
            time_diff = current_inspection.inspection_date - previous_inspection.inspection_date
            time_diff_years = float(time_diff.days) / 365.25
            
            if time_diff_years > 0.1:  # At least ~5 weeks apart
                # Calculate metal loss
                metal_loss = float(previous_inspection.min_thickness_found - current_inspection.min_thickness_found)
                
                if metal_loss > 0:
                    corrosion_rate = metal_loss / time_diff_years
                    calculation_method = "Linear regression from most recent inspection"
                    confidence_level = min(95.0, 70.0 + (len(historical_inspections) * 5))
                    
                    # Calculate remaining life
                    current_thickness = float(current_inspection.min_thickness_found)
                    # Use conservative minimum thickness (50% of design thickness)
                    min_allowable = float(equipment.design_thickness) * 0.5
                    
                    if current_thickness > min_allowable and corrosion_rate > 0:
                        remaining_life = (current_thickness - min_allowable) / corrosion_rate
                        
                        # Add conservative assumptions
                        assumptions.extend([
                            "Linear corrosion progression assumed",
                            f"Minimum allowable thickness: {min_allowable:.3f}\" (50% of design)",
                            f"Based on {len(historical_inspections) + 1} inspection(s)"
                        ])
                        
                        # Generate warnings for critical conditions
                        if remaining_life < 2.0:
                            warnings.append("CRITICAL: Remaining life less than 2 years - immediate assessment required")
                        elif remaining_life < 5.0:
                            warnings.append("WARNING: Remaining life less than 5 years - increased monitoring recommended")
                        
                        if corrosion_rate > 0.010:  # > 10 mils/year
                            warnings.append("WARNING: High corrosion rate detected - review operating conditions")
                    
        # Check for thin areas relative to design
        thickness_ratio = float(current_inspection.min_thickness_found) / float(equipment.design_thickness)
        if thickness_ratio < 0.6:
            warnings.append("CRITICAL: Current thickness below 60% of design thickness - immediate action required")
        elif thickness_ratio < 0.7:
            warnings.append("WARNING: Current thickness below 70% of design thickness")
        elif thickness_ratio < 0.8:
            warnings.append("CAUTION: Current thickness below 80% of design thickness")
        
        # Build response
        response = CorrosionAnalysisResponse(
            equipment_id=str(current_inspection.equipment_id),
            inspection_id=str(inspection_id),
            current_min_thickness=float(current_inspection.min_thickness_found),
            corrosion_rate=corrosion_rate,
            remaining_life=remaining_life,
            confidence_level=confidence_level,
            calculation_method=calculation_method,
            assumptions=assumptions,
            warnings=warnings,
            analysis_date=datetime.utcnow()
        )
        
        rate_str = f"{corrosion_rate:.5f}" if corrosion_rate else "N/A"
        life_str = f"{remaining_life:.1f}" if remaining_life else "N/A"
        
        logger.info(
            f"Corrosion analysis completed for inspection {inspection_id}. "
            f"Rate: {rate_str} in/yr, "
            f"Remaining life: {life_str} years"
        )
        
        return response
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in corrosion analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing corrosion analysis"
        )


# ========================================================================
# BACKGROUND TASKS
# ========================================================================

async def trigger_api579_calculations(inspection_id: UUID, equipment_id: UUID, recalculate: bool = False):
    """
    Background task to trigger API 579 fitness-for-service calculations.
    
    This ensures calculations don't block the API response while providing
    comprehensive safety assessments asynchronously.
    """
    try:
        logger.info(f"Starting API 579 calculations for inspection {inspection_id}")
        
        # Import here to avoid circular dependencies
        from app.services.api579_service import API579Service
        from models.database import SessionLocal
        
        # Initialize service with session factory for proper isolation
        api579_service = API579Service(SessionLocal)
        
        # Use session per task for background operations
        with SessionLocal() as db:
            try:
                # Check if calculations already exist and recalculation is not forced
                if not recalculate:
                    existing_calculations = db.query(API579Calculation).filter(
                        API579Calculation.inspection_record_id == inspection_id
                    ).first()
                    
                    if existing_calculations:
                        logger.info(f"API 579 calculations already exist for inspection {inspection_id}")
                        return
                
                # Perform complete API 579 assessment
                results = await api579_service.perform_complete_assessment(
                    inspection_id=str(inspection_id),
                    performed_by="API579Calculator-v1.0",
                    calculation_level="Level 1"
                )
                
                logger.info(
                    f"Completed API 579 calculations for inspection {inspection_id}. "
                    f"RSF: {results.get('rsf', 'N/A')}, "
                    f"Remaining Life: {results.get('remaining_life', 'N/A')} years"
                )
                
                # Log any critical findings
                if results.get('rsf') and results['rsf'] < Decimal("0.90"):
                    logger.warning(
                        f"CRITICAL: RSF {results['rsf']:.3f} below acceptance criteria "
                        f"for inspection {inspection_id}"
                    )
                
                if results.get('remaining_life') and results['remaining_life'] < Decimal("2.0"):
                    logger.warning(
                        f"CRITICAL: Remaining life {results['remaining_life']:.1f} years "
                        f"below 2-year threshold for inspection {inspection_id}"
                    )
            
            except Exception as e:
                logger.error(f"Error in background API 579 calculations: {str(e)}", exc_info=True)
                # Don't re-raise - this is a background task
        
    except Exception as e:
        logger.error(f"Error in background API 579 calculations: {str(e)}", exc_info=True)
        # Don't re-raise - this is a background task