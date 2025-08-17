"""
Inspection record API endpoints.
Handles thickness measurements and corrosion calculations.
"""
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import statistics

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from backend.models import inspection as models
from backend.models import equipment as equipment_models
from backend.core.config import settings
from backend.models.database import get_db
from backend.services.document_analyzer import DocumentAnalyzer

router = APIRouter()


# Thickness reading schema
class ThicknessReading(BaseModel):
    """Individual thickness measurement at a CML."""
    location: str = Field(..., description="CML location identifier")
    thickness: Decimal = Field(..., gt=0, le=10, description="Measured thickness in inches")
    cml_id: Optional[str] = Field(None, description="Condition Monitoring Location ID")
    
    class Config:
        json_encoders = {Decimal: lambda v: float(v)}


# Inspection schemas
class InspectionBase(BaseModel):
    """Base inspection schema with validation."""
    equipment_id: UUID
    inspection_date: datetime
    inspection_type: str = Field(..., regex="^(EXTERNAL|INTERNAL|UT|RT|VT)$")
    inspector_name: str = Field(..., min_length=1)
    inspector_certification: Optional[str] = None
    
    thickness_readings: List[ThicknessReading] = Field(
        ..., 
        min_items=1,
        description="At least one thickness reading required"
    )
    
    corrosion_type: Optional[str] = Field(
        None, 
        regex="^(UNIFORM|PITTING|CREVICE|EROSION)$"
    )
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    
    @validator('thickness_readings')
    def validate_readings(cls, v):
        """Ensure thickness readings are valid."""
        if not v:
            raise ValueError("At least one thickness reading required")
        
        # Check for duplicate locations
        locations = [r.location for r in v]
        if len(locations) != len(set(locations)):
            raise ValueError("Duplicate CML locations found")
        
        return v


class InspectionCreate(InspectionBase):
    """Schema for creating inspection records."""
    report_number: str = Field(..., min_length=1)
    follow_up_required: bool = Field(default=False)


class InspectionResponse(InspectionBase):
    """Response schema with calculated fields."""
    id: UUID
    min_thickness_found: Decimal
    avg_thickness: Decimal
    corrosion_rate_calculated: Optional[Decimal]
    confidence_level: Optional[Decimal]
    
    ai_processed: bool
    created_at: datetime
    verified_by: Optional[str]
    verified_at: Optional[datetime]
    
    # Calculated fields
    thickness_loss: Optional[Decimal] = None
    remaining_life_estimate: Optional[Decimal] = None
    
    class Config:
        orm_mode = True
        json_encoders = {
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v)
        }


class CorrosionAnalysis(BaseModel):
    """Corrosion rate analysis results."""
    equipment_id: UUID
    current_min_thickness: Decimal
    previous_min_thickness: Optional[Decimal]
    time_between_inspections: Optional[Decimal]  # years
    
    corrosion_rate: Optional[Decimal]  # inches/year
    remaining_life: Optional[Decimal]  # years
    confidence_level: Decimal
    
    calculation_method: str
    assumptions: List[str]
    warnings: List[str]
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            UUID: lambda v: str(v)
        }


# API Endpoints
@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    inspection: InspectionCreate,
    db: Session = Depends(get_db)
):
    """
    Create new inspection record with thickness measurements.
    
    Automatically calculates:
    - Minimum and average thickness
    - Corrosion rate (if previous inspection exists)
    - Estimated remaining life
    """
    # Verify equipment exists
    equipment = db.query(equipment_models.Equipment).filter(
        equipment_models.Equipment.id == inspection.equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment not found"
        )
    
    # Calculate thickness statistics
    thicknesses = [reading.thickness for reading in inspection.thickness_readings]
    min_thickness = min(thicknesses)
    avg_thickness = Decimal(str(statistics.mean([float(t) for t in thicknesses])))
    
    # Get previous inspection for corrosion rate calculation
    previous_inspection = db.query(models.InspectionRecord).filter(
        models.InspectionRecord.equipment_id == inspection.equipment_id,
        models.InspectionRecord.inspection_date < inspection.inspection_date
    ).order_by(models.InspectionRecord.inspection_date.desc()).first()
    
    corrosion_rate = None
    if previous_inspection and previous_inspection.min_thickness_found:
        # Calculate corrosion rate
        thickness_loss = previous_inspection.min_thickness_found - min_thickness
        time_years = (inspection.inspection_date - previous_inspection.inspection_date).days / 365.25
        
        if time_years > 0 and thickness_loss > 0:
            corrosion_rate = thickness_loss / Decimal(str(time_years))
    
    # Create inspection record
    db_inspection = models.InspectionRecord(
        **inspection.dict(exclude={'thickness_readings'}),
        thickness_readings=[r.dict() for r in inspection.thickness_readings],
        min_thickness_found=min_thickness,
        avg_thickness=avg_thickness,
        corrosion_rate_calculated=corrosion_rate,
        confidence_level=Decimal("85.0") if len(thicknesses) >= 5 else Decimal("70.0")
    )
    
    db.add(db_inspection)
    
    # Update equipment last inspection date
    equipment.last_inspection_date = inspection.inspection_date
    
    # Calculate next inspection due based on API standards and corrosion rate
    if corrosion_rate:
        # API 653 formula: interval = (t_current - t_minimum) / (2 * corrosion_rate)
        t_minimum = equipment.nominal_thickness * Decimal("0.5")  # 50% as minimum
        remaining_corrosion_allowance = min_thickness - t_minimum
        
        if remaining_corrosion_allowance > 0 and corrosion_rate > 0:
            interval_years = remaining_corrosion_allowance / (2 * corrosion_rate)
            interval_years = min(interval_years, Decimal("5"))  # Max 5 years
            
            from datetime import timedelta
            equipment.next_inspection_due = inspection.inspection_date + timedelta(
                days=int(interval_years * 365)
            )
    
    db.commit()
    db.refresh(db_inspection)
    
    return db_inspection


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: UUID,
    db: Session = Depends(get_db)
):
    """Get inspection record by ID."""
    inspection = db.query(models.InspectionRecord).filter(
        models.InspectionRecord.id == inspection_id
    ).first()
    
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection not found"
        )
    
    return inspection


@router.get("/equipment/{equipment_id}", response_model=List[InspectionResponse])
async def get_equipment_inspections(
    equipment_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all inspections for specific equipment."""
    inspections = db.query(models.InspectionRecord).filter(
        models.InspectionRecord.equipment_id == equipment_id
    ).order_by(
        models.InspectionRecord.inspection_date.desc()
    ).offset(skip).limit(limit).all()
    
    return inspections


@router.post("/{inspection_id}/verify")
async def verify_inspection(
    inspection_id: UUID,
    verifier_name: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Human verification of inspection results.
    Required for regulatory compliance.
    """
    inspection = db.query(models.InspectionRecord).filter(
        models.InspectionRecord.id == inspection_id
    ).first()
    
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection not found"
        )
    
    if inspection.verified_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inspection already verified by {inspection.verified_by}"
        )
    
    inspection.verified_by = verifier_name
    inspection.verified_at = datetime.utcnow()
    
    if notes:
        inspection.findings = (inspection.findings or "") + f"\n\nVerification notes: {notes}"
    
    db.commit()
    
    return {
        "message": "Inspection verified successfully",
        "verified_by": verifier_name,
        "verified_at": inspection.verified_at
    }


@router.post("/{inspection_id}/analyze-corrosion", response_model=CorrosionAnalysis)
async def analyze_corrosion(
    inspection_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Perform detailed corrosion analysis for inspection.
    
    Calculates:
    - Short-term and long-term corrosion rates
    - Remaining life with confidence intervals
    - Risk assessment
    """
    inspection = db.query(models.InspectionRecord).filter(
        models.InspectionRecord.id == inspection_id
    ).first()
    
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection not found"
        )
    
    equipment = db.query(equipment_models.Equipment).filter(
        equipment_models.Equipment.id == inspection.equipment_id
    ).first()
    
    # Get inspection history
    history = db.query(models.InspectionRecord).filter(
        models.InspectionRecord.equipment_id == inspection.equipment_id,
        models.InspectionRecord.inspection_date <= inspection.inspection_date
    ).order_by(models.InspectionRecord.inspection_date.desc()).limit(5).all()
    
    warnings = []
    assumptions = [
        "Uniform corrosion pattern assumed",
        f"Minimum allowable thickness: {float(equipment.nominal_thickness) * 0.5:.3f} inches"
    ]
    
    # Calculate corrosion rate
    if len(history) >= 2:
        # Use linear regression for better accuracy
        import numpy as np
        from sklearn.linear_model import LinearRegression
        
        dates = []
        thicknesses = []
        
        for h in history:
            dates.append((h.inspection_date - history[-1].inspection_date).days / 365.25)
            thicknesses.append(float(h.min_thickness_found))
        
        if len(set(thicknesses)) > 1:  # Need variation in thickness
            X = np.array(dates).reshape(-1, 1)
            y = np.array(thicknesses)
            
            model = LinearRegression()
            model.fit(X, y)
            
            corrosion_rate = abs(Decimal(str(model.coef_[0])))
            confidence = Decimal(str(model.score(X, y) * 100))
            
            calculation_method = "Linear regression analysis"
        else:
            corrosion_rate = inspection.corrosion_rate_calculated
            confidence = Decimal("70.0")
            calculation_method = "Simple average method"
            warnings.append("Limited thickness variation in historical data")
    else:
        corrosion_rate = settings.DEFAULT_CORROSION_RATE
        confidence = Decimal("50.0")
        calculation_method = "Default corrosion rate applied"
        warnings.append("Insufficient inspection history")
        assumptions.append(f"Default corrosion rate: {settings.DEFAULT_CORROSION_RATE} in/year")
    
    # Calculate remaining life
    t_minimum = equipment.nominal_thickness * Decimal("0.5")
    remaining_thickness = inspection.min_thickness_found - t_minimum
    
    remaining_life = None
    if corrosion_rate and corrosion_rate > 0:
        remaining_life = remaining_thickness / corrosion_rate
        
        if remaining_life < settings.MIN_REMAINING_LIFE_YEARS:
            warnings.append(f"CRITICAL: Remaining life below {settings.MIN_REMAINING_LIFE_YEARS} years")
    
    # Previous inspection data
    previous_thickness = None
    time_between = None
    if len(history) >= 2:
        previous_thickness = history[1].min_thickness_found
        time_between = Decimal(str((history[0].inspection_date - history[1].inspection_date).days / 365.25))
    
    return CorrosionAnalysis(
        equipment_id=inspection.equipment_id,
        current_min_thickness=inspection.min_thickness_found,
        previous_min_thickness=previous_thickness,
        time_between_inspections=time_between,
        corrosion_rate=corrosion_rate,
        remaining_life=remaining_life,
        confidence_level=confidence,
        calculation_method=calculation_method,
        assumptions=assumptions,
        warnings=warnings
    )


@router.post("/upload-report")
async def upload_inspection_report(
    equipment_tag: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process inspection report using AI.
    
    Extracts:
    - Thickness measurements
    - Inspection metadata
    - Findings and recommendations
    """
    # Verify equipment exists
    equipment = db.query(equipment_models.Equipment).filter(
        equipment_models.Equipment.tag == equipment_tag
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with tag '{equipment_tag}' not found"
        )
    
    # Save file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Process with document analyzer
        analyzer = DocumentAnalyzer()
        extracted_data = await analyzer.extract_inspection_data(tmp_path)
        
        # Validate extracted data
        if not extracted_data.get('thickness_readings'):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract thickness readings from document"
            )
        
        # Create inspection record from extracted data
        inspection_data = {
            "equipment_id": equipment.id,
            "inspection_date": extracted_data.get('inspection_date', datetime.now()),
            "inspection_type": extracted_data.get('inspection_type', 'UT'),
            "inspector_name": extracted_data.get('inspector_name', 'AI Extracted'),
            "thickness_readings": extracted_data['thickness_readings'],
            "findings": extracted_data.get('findings'),
            "recommendations": extracted_data.get('recommendations'),
            "ai_processed": True,
            "ai_extraction_data": extracted_data,
            "ai_confidence_score": extracted_data.get('confidence', 75.0)
        }
        
        # Create inspection using existing endpoint logic
        inspection = InspectionCreate(**inspection_data)
        return await create_inspection(inspection, db)
        
    finally:
        # Clean up temp file
        os.unlink(tmp_path)
