"""Inspection and measurement models"""
from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Inspection(Base, UUIDMixin, TimestampMixin):
    """Inspection event record"""
    __tablename__ = "inspections"
    
    # Equipment reference
    equipment_id: Mapped[str] = mapped_column(ForeignKey("equipment.id"))
    equipment: Mapped["Equipment"] = relationship(back_populates="inspections")
    
    # Inspection details
    inspection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inspector_name: Mapped[str] = mapped_column(String(100))
    inspection_type: Mapped[str] = mapped_column(String(50))  # UT, VT, etc.
    
    # Documents
    report_pdf_path: Mapped[str | None] = mapped_column(String(255))
    images_paths: Mapped[list[str] | None] = mapped_column(JSON)
    
    # Summary
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    
    # Relationships
    thickness_readings: Mapped[list["ThicknessReading"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan"
    )
    corrosion_detections: Mapped[list["CorrosionDetection"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan"
    )
    api579_calculation: Mapped["API579Calculation"] = relationship(
        back_populates="inspection",
        uselist=False
    )


class ThicknessReading(Base, UUIDMixin, TimestampMixin):
    """Individual thickness measurement (CML)"""
    __tablename__ = "thickness_readings"
    
    # Parent inspection
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"))
    inspection: Mapped["Inspection"] = relationship(back_populates="thickness_readings")
    
    # Location
    cml_number: Mapped[str] = mapped_column(String(20))  # Condition Monitoring Location
    location_description: Mapped[str] = mapped_column(String(100))
    
    # Measurement
    thickness: Mapped[float] = mapped_column(Float)  # inches
    previous_thickness: Mapped[float | None] = mapped_column(Float)
    
    # Calculated
    metal_loss: Mapped[float | None] = mapped_column(Float)  # inc
