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
from decimal import Decimal, InvalidOperation
from uuid import UUID
import logging
import statistics

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, field_validator, ConfigDict
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
from app.services.document_analyzer import DocumentAnalyzer
from app.calculations.dual_path_calculator import API579Calculator

# Configure logger for audit trail
logger = logging.getLogger("mechanical_integrity.inspections")

router = APIRouter(tags=["Inspections"])


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
        json_encoders={Decimal: lambda v: str(v)},
        str_strip_whitespace=True
    )
    
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
        json_encoders={Decimal: lambda v: str(v)},
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
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: str(v),
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }
    )
    
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
    except:
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
        
        # Calculate corrosion rate from previous inspections
        corrosion_rate = None
        confidence_level = Decimal("75.0")  # Default confidence
        
        previous_inspection = db.query(InspectionRecord).filter(
            InspectionRecord.equipment_id == str(equipment.id),
            InspectionRecord.inspection_date < inspection_data.inspection_date
        ).order_by(InspectionRecord.inspection_date.desc()).first()
        
        if previous_inspection and previous_inspection.min_thickness_found:
            thickness_loss = previous_inspection.min_thickness_found - min_thickness
            time_years = (inspection_data.inspection_date - previous_inspection.inspection_date).days / Decimal("365.25")
            
            if time_years > 0 and thickness_loss > 0:
                corrosion_rate = thickness_loss / time_years
                confidence_level = Decimal("85.0") if len(thickness_values) >= 5 else Decimal("70.0")
                
                logger.info(f"Calculated corrosion rate: {corrosion_rate} in/year over {time_years} years")
        
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
            API579Calculation.inspection_id == str(inspection_id)
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
            API579Calculation.inspection_id == str(inspection_id)
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
        
        # Create database session for background task
        db = SessionLocal()
        
        try:
            # Initialize service and perform complete assessment
            api579_service = API579Service(db)
            
            # Check if calculations already exist and recalculation is not forced
            if not recalculate:
                existing_calculations = db.query(API579Calculation).filter(
                    API579Calculation.inspection_id == inspection_id
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
                
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Error in background API 579 calculations: {str(e)}", exc_info=True)
        # Don't re-raise - this is a background task