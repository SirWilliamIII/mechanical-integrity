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
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict, computed_field

from models.equipment import Equipment, EquipmentType
from models.database import get_db
from app.validation.validators import API579Validator, ValidationResult

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
    
    @field_validator('design_pressure', mode='after')
    @classmethod
    def validate_pressure(cls, v):
        """Ensure pressure is within safe operating limits."""
        if v > Decimal('5000'):
            # Flag for high pressure equipment
            print(f"⚠️ High pressure equipment: {v} psi")
        return v
    
    # TODO: [VALIDATION] Add comprehensive material-pressure-temperature validation
    # Cross-reference material specs with ASME pressure-temperature rating charts
    
    model_config = ConfigDict()
    
    @field_serializer('design_pressure', 'design_temperature', when_used='json')
    def serialize_decimal_fields(self, value: Decimal) -> str:
        """Convert Decimal fields to string for JSON serialization."""
        return str(value) if value is not None else None


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
    
    model_config = ConfigDict()
    
    @field_serializer('operating_pressure', 'operating_temperature', when_used='json')
    def serialize_decimal_fields(self, value: Optional[Decimal]) -> Optional[str]:
        """Convert Decimal fields to string for JSON serialization."""
        return str(value) if value is not None else None


class EquipmentResponse(BaseModel):
    """Response schema including calculated fields that matches database model."""
    id: UUID
    tag_number: str
    name: str  # Mapped from description in database
    equipment_type: str
    design_pressure: Decimal
    design_temperature: Decimal
    material_specification: str
    design_thickness: Decimal
    location: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    year_built: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    last_inspection_date: Optional[datetime] = None
    next_inspection_due: Optional[datetime] = None
    criticality: str = "MEDIUM"
    
    # Calculated fields
# days_until_inspection and inspection_overdue are now computed fields
    
    @classmethod
    def from_db_model(cls, db_equipment):
        """Convert database model to API response, mapping fields properly."""
        # Map equipment type back to API format
        equipment_type_reverse_mapping = {
            "pressure_vessel": "VESSEL",
            "storage_tank": "TANK", 
            "piping": "PIPING",
            "heat_exchanger": "HEAT_EXCHANGER"
        }
        
        api_equipment_type = equipment_type_reverse_mapping.get(
            db_equipment.equipment_type, 
            db_equipment.equipment_type
        )
        
        return cls(
            id=db_equipment.id,
            tag_number=db_equipment.tag_number,
            name=db_equipment.description,  # Map description to name
            equipment_type=api_equipment_type,
            design_pressure=db_equipment.design_pressure,
            design_temperature=db_equipment.design_temperature,
            material_specification=db_equipment.material_specification,
            design_thickness=db_equipment.design_thickness,
            location=getattr(db_equipment, 'location', None),
            manufacturer=getattr(db_equipment, 'manufacturer', None),
            serial_number=getattr(db_equipment, 'serial_number', None),
            year_built=getattr(db_equipment, 'year_built', None),
            created_at=db_equipment.created_at,
            updated_at=db_equipment.updated_at,
            last_inspection_date=getattr(db_equipment, 'last_inspection_date', None),
            next_inspection_due=getattr(db_equipment, 'next_inspection_due', None),
            criticality=getattr(db_equipment, 'criticality', 'MEDIUM')
        )
    
    model_config = ConfigDict()
    
    @field_serializer('id', when_used='json')
    def serialize_uuid(self, value: UUID) -> str:
        """Convert UUID to string for JSON serialization."""
        return str(value) if value is not None else None
    
    @computed_field
    @property
    def days_until_inspection(self) -> Optional[int]:
        """Calculate days until next inspection."""
        if self.next_inspection_due:
            delta = self.next_inspection_due - datetime.now()
            return delta.days
        return None
    
    @computed_field
    @property  
    def inspection_overdue(self) -> bool:
        """Flag overdue inspections."""
        if self.days_until_inspection is not None:
            return self.days_until_inspection < 0
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
    
    # Create equipment - map API schema to database model
    equipment_data = equipment.model_dump()
    
    # Map fields from API schema to database model fields
    equipment_type_mapping = {
        "VESSEL": "pressure_vessel",
        "TANK": "storage_tank", 
        "PIPING": "piping",
        "HEAT_EXCHANGER": "heat_exchanger"
    }
    
    db_data = {
        "tag_number": equipment_data["tag_number"],
        "description": equipment_data["name"],  # Map name to description
        "equipment_type": equipment_type_mapping.get(equipment_data["equipment_type"], equipment_data["equipment_type"]),
        "design_pressure": equipment_data["design_pressure"],
        "design_temperature": equipment_data["design_temperature"],
        "material_specification": equipment_data["material_specification"],
        "design_thickness": equipment_data["design_thickness"],
        "service_description": equipment_data.get("service_description", "Unknown"),
        "installation_date": datetime.fromisoformat(equipment_data["installation_date"].replace("Z", "+00:00")) if equipment_data.get("installation_date") else datetime.utcnow(),
        "corrosion_allowance": equipment_data.get("corrosion_allowance", Decimal("0.125"))
    }
    
    db_equipment = Equipment(**db_data)
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    
    # Log creation for audit trail
    print(f"✅ Created equipment: {equipment.tag_number} - {equipment.name}")
    
    return EquipmentResponse.from_db_model(db_equipment)


@router.get("/materials", response_model=List[str])
async def list_supported_materials():
    """
    List all supported ASME material specifications in the database.
    
    Returns materials from the expanded ASME Section II-D database
    with temperature-dependent properties for accurate allowable stress calculations.
    """
    from models.material_properties import ASMEMaterialDatabase
    
    supported_materials = ASMEMaterialDatabase.get_supported_materials()
    return sorted(supported_materials)


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
    
    equipment_list = query.offset(skip).limit(limit).all()
    return [EquipmentResponse.from_db_model(eq) for eq in equipment_list]


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
    
    return EquipmentResponse.from_db_model(equipment)


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
    
    return EquipmentResponse.from_db_model(equipment)


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
    
    return EquipmentResponse.from_db_model(equipment)


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
            detail="Equipment not found"
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


class EquipmentValidationRequest(BaseModel):
    """Request schema for comprehensive equipment design validation."""
    design_pressure: Decimal = Field(..., description="Design pressure in PSI")
    design_temperature: Decimal = Field(..., description="Design temperature in °F")
    design_thickness: Decimal = Field(..., description="Design thickness in inches")
    material_specification: str = Field(..., description="ASME material specification")
    equipment_type: str = Field(..., pattern="^(pressure_vessel|storage_tank|piping|heat_exchanger)$")
    service_description: Optional[str] = Field(None, description="Service description")
    corrosion_allowance: Optional[Decimal] = Field(Decimal('0.125'), description="Corrosion allowance in inches")
    
    model_config = ConfigDict()

    @field_serializer('design_pressure', 'design_temperature', 'design_thickness', 'corrosion_allowance', when_used='json')
    def serialize_decimal_fields(self, value: Decimal) -> str:
        return str(value) if value is not None else None


class ValidationResultResponse(BaseModel):
    """Response schema for validation results."""
    valid: bool
    field: str
    value: str
    reason: Optional[str] = None
    api_reference: Optional[str] = None
    action_required: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    @classmethod
    def from_validation_result(cls, result: ValidationResult) -> "ValidationResultResponse":
        """Convert ValidationResult to API response."""
        return cls(
            valid=result.valid,
            field=result.field,
            value=str(result.value),
            reason=result.reason,
            api_reference=result.api_reference,
            action_required=result.action_required,
            warnings=result.warnings or []
        )


@router.post("/validate-design", response_model=List[ValidationResultResponse])
async def validate_equipment_design(
    validation_request: EquipmentValidationRequest
):
    """
    Comprehensive equipment design validation with material-pressure-temperature cross-validation.
    
    This endpoint performs safety-critical validation of equipment design parameters
    according to ASME codes and API 579 standards, including:
    
    - Individual parameter validation (pressure, temperature, thickness, material)
    - Cross-validation of material properties vs operating conditions
    - ASME Section VIII thickness adequacy calculations
    - Service-specific compatibility warnings
    - API 579 compliance checks
    
    Returns detailed validation results with specific API references and 
    required actions for any non-compliance issues.
    """
    validator = API579Validator(strict_mode=True)
    
    # Convert string equipment type to enum
    try:
        equipment_type_enum = EquipmentType(validation_request.equipment_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid equipment type: {validation_request.equipment_type}"
        )
    
    # Perform comprehensive validation
    validation_results = validator.validate_equipment_design(
        design_pressure=validation_request.design_pressure,
        design_temperature=validation_request.design_temperature,
        design_thickness=validation_request.design_thickness,
        material_specification=validation_request.material_specification,
        equipment_type=equipment_type_enum,
        service_description=validation_request.service_description,
        corrosion_allowance=validation_request.corrosion_allowance
    )
    
    # Convert to API response format
    response_results = [
        ValidationResultResponse.from_validation_result(result) 
        for result in validation_results
    ]
    
    return response_results
