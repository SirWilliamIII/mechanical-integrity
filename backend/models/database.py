# backend/app/models/database.py
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Equipment(Base):
    __tablename__ = "equipment"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    equipment_type = Column(String)
    location = Column(String)
    material = Column(String)
    design_pressure = Column(Float)
    design_temperature = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class InspectionRecord(Base):
    __tablename__ = "inspection_records"
    
    id = Column(String, primary_key=True)
    equipment_id = Column(String, ForeignKey("equipment.id"))
    inspection_date = Column(DateTime)
    thickness_readings = Column(JSON)  # Array of measurements
    corrosion_rate = Column(Float)
    remaining_life = Column(Float)
    inspector_name = Column(String)
    document_reference = Column(String)  # Link to analyzed document
    
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True)
    equipment_id = Column(String, ForeignKey("equipment.id"))
    analysis_type = Column(String)  # "API_579", "RBI", etc.
    result_data = Column(JSON)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
