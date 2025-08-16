"""Equipment models"""
from enum import Enum
from sqlalchemy import String, Float, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class EquipmentType(str, Enum):
    """Types of equipment per API standards"""
    PRESSURE_VESSEL = "pressure_vessel"
    STORAGE_TANK = "storage_tank"  
    PIPING = "piping"
    HEAT_EXCHANGER = "heat_exchanger"


class Equipment(Base, UUIDMixin, TimestampMixin):
    """Equipment master data"""
    __tablename__ = "equipment"
    
    # Identification
    tag_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(200))
    equipment_type: Mapped[EquipmentType] = mapped_column(SQLEnum(EquipmentType))
    
    # Design specifications (critical for API 579)
    design_pressure: Mapped[float] = mapped_column(Float)  # PSI
    design_temperature: Mapped[float] = mapped_column(Float)  # °F
    design_thickness: Mapped[float] = mapped_column(Float)  # inches
    material_spec: Mapped[str] = mapped_column(String(50))  # e.g., "SA-516-70"
    
    # Corrosion allowance
    corrosion_allowance: Mapped[float] = mapped_column(Float, default=0.125)  # inches
    
    # Service info
    service: Mapped[str] = mapped_column(String(100))
    installation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="equipment",
        cascade="all, delete-orphan"
    )
