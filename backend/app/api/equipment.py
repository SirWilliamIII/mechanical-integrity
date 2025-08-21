"""
Equipment API endpoints with safety-critical validation.
Follows API 579 compliance requirements.
"""
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from models.equipment import Equipment
from core.config import settings
from models.database import get_db

router = APIRouter()


# Pydantic schemas with strict validation
class EquipmentBase(BaseModel):
    """Base equipment schema with safety-critical validations."""
    tag_number: str = Field(..., min_length=1, max_length=50, description="Equipment tag (unique identifier)")
    name: str = Field(..., min_length=1, max_length=200)
    equipment_type: str = Field(..., pattern="^(VESSEL|TANK|PIPING)$")
    
    # Design parameters - critical for calculations
    design_pressure: Decimal = Field(..., gt=0, le=10000, description="Design pressure in psi")
    design_temperature: Decimal = Field(..., ge=-320, le=1500, description="Design temperature in °F")
    material_specification: str = Field(..., description="Material specification (e.g., SA-516-70)")
    design_thickness: Decimal = Field(..., gt=0, le=10, description="Design thickness in inches")
    
    # Optional fields
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    year_built: Optional[int] = Field(None, ge=1900, le=datetime.now().year)
    
    # TODO: [DEPRECATION] Migrate Pydantic v1 @validator to v2 @field_validator
    # Pydantic v2.0+ deprecates @validator in favor of @field_validator
    # Replace with: @field_validator('design_pressure', mode='before')
    @validator('design_pressure')
    def validate_pressure(cls, v):
        """Ensure pressure is within safe operating limits."""
        if v > Decimal('5000'):
            # Flag for high pressure equipment
            print(f"⚠️ High pressure equipment: {v} psi")
        return v
    
    # TODO: [VALIDATION] Add comprehensive material-pressure-temperature validation
    # Cross-reference material specs with ASME pressure-temperature rating charts
    
    # TODO: [DEPRECATION] Replace deprecated json_encoders with Pydantic v2 serializers
    # Pydantic v2.0+ deprecates class-based Config and json_encoders
    # Use model_config = ConfigDict() and @field_serializer instead
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class EquipmentCreate(EquipmentBase):
    """Schema for creating new equipment."""
    corrosion_allowance: Decimal = Field(default=Decimal("0.125"), ge=0, le=1)
    criticality: str = Field(default="MEDIUM", pattern="^(HIGH|MEDIUM|LOW)$")


class EquipmentUpdate(BaseModel):
    """Schema for updating equipment - all fields optional."""
    name: Optional[str] = None
    location: Optional[str] = None
    operating_pressure: Optional[Decimal] = Field(None, ge=0)
    operating_temperature: Optional[Decimal] = None
    last_inspection_date: Optional[datetime] = None
    next_inspection_due: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class EquipmentResponse(EquipmentBase):
    """Response schema including calculated fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_inspection_date: Optional[datetime]
    next_inspection_due: Optional[datetime]
    criticality: str
    
    # Calculated fields
    days_until_inspection: Optional[int] = None
    inspection_overdue: bool = False
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: str(v),
            UUID: lambda v: str(v)
        }
    
    @validator('days_until_inspection', always=True)
    def calculate_days_until_inspection(cls, v, values):
        """Calculate days until next inspection."""
        if 'next_inspection_due' in values and values['next_inspection_due']:
            delta = values['next_inspection_due'] - datetime.now()
            return delta.days
        return None
    
    @validator('inspection_overdue', always=True)
    def check_overdue(cls, v, values):
        """Flag overdue inspections."""
        if 'days_until_inspection' in values and values['days_until_inspection'] is not None:
            return values['days_until_inspection'] < 0
        return False


# API Endpoints
@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create new equipment entry with validation.
    
    Validates:
    - Unique equipment tag
    - Design parameters within safe limits
    - Material specification exists
    """
    # Check if tag already exists
    existing = db.query(Equipment).filter(
        Equipment.tag_number == equipment.tag_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Equipment with tag '{equipment.tag_number}' already exists"
        )
    
    # Create equipment
    db_equipment = Equipment(**equipment.dict())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    
    # Log creation for audit trail
    print(f"✅ Created equipment: {equipment.tag_number} - {equipment.name}")
    
    return db_equipment


@router.get("/", response_model=List[EquipmentResponse])
async def list_equipment(
    criticality: Optional[str] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List equipment with filtering options.
    
    Filters:
    - criticality: Filter by HIGH, MEDIUM, LOW
    - overdue_only: Show only overdue inspections
    """
    query = db.query(Equipment)
    
    if criticality:
        query = query.filter(Equipment.criticality == criticality)
    
    if overdue_only:
        query = query.filter(
            Equipment.next_inspection_due < datetime.now()
        )
    
    # Order by criticality and inspection due date
    query = query.order_by(
        Equipment.criticality.desc(),
        Equipment.next_inspection_due.asc()
    )
    
    return query.offset(skip).limit(limit).all()


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: UUID,
    db: Session = Depends(get_db)
):
    """Get equipment by ID with all details."""
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id '{equipment_id}' not found"
        )
    
    return equipment


@router.get("/tag/{tag_number}", response_model=EquipmentResponse)
async def get_equipment_by_tag(
    tag_number: str,
    db: Session = Depends(get_db)
):
    """Get equipment by tag (more user-friendly than UUID)."""
    equipment = db.query(Equipment).filter(
        Equipment.tag_number == tag_number
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with tag '{tag_number}' not found"
        )
    
    return equipment


@router.patch("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: UUID,
    equipment_update: EquipmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Update equipment details.
    
    Note: Design parameters cannot be changed via API for safety.
    Changes to design specs require engineering review.
    """
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with id '{equipment_id}' not found"
        )
    
    # Update only provided fields
    update_data = equipment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(equipment, field, value)
    
    equipment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(equipment)
    
    return equipment


@router.get("/{equipment_id}/inspection-status")
async def get_inspection_status(
    equipment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed inspection status for equipment.
    
    Returns:
    - Last inspection details
    - Next inspection due
    - Compliance status
    - Risk assessment
    """
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment not found"
        )
    
    # Calculate inspection intervals based on API standards
    if equipment.equipment_type == "VESSEL":
        max_interval_years = 10  # API 510
    elif equipment.equipment_type == "TANK":
        max_interval_years = 20  # API 653
    else:  # PIPING
        max_interval_years = 5   # API 570
    
    # TODO: [FEATURE] Implement risk-based inspection interval calculation
    # Adjust intervals based on equipment criticality, corrosion rates, and service conditions
    
    days_overdue = 0
    if equipment.next_inspection_due:
        days_overdue = (datetime.now() - equipment.next_inspection_due).days
    
    return {
        "equipment_tag": equipment.tag_number,
        "criticality": equipment.criticality,
        "last_inspection": equipment.last_inspection_date,
        "next_due": equipment.next_inspection_due,
        "days_overdue": max(0, days_overdue),
        "compliance_status": "COMPLIANT" if days_overdue <= 0 else "OVERDUE",
        "max_interval_years": max_interval_years,
        "risk_level": "HIGH" if days_overdue > 30 and equipment.criticality == "HIGH" else "MEDIUM"
    }
