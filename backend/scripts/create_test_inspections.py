#!/usr/bin/env python3
"""
Create realistic test inspection data for mechanical integrity management system.

This script generates safety-critical inspection data following API 579 standards
for petroleum industry equipment. All data represents realistic field conditions
and demonstrates the system's capabilities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
import uuid
from typing import List, Dict, Any

from models.database import SessionLocal, Base, engine
from models.equipment import Equipment, EquipmentType, EquipmentCriticality
from models.material_properties import MaterialGrade
from models.inspection import (
    InspectionRecord, 
    InspectionType,
    API579Calculation
)

# Ensure all tables exist
Base.metadata.create_all(bind=engine)

class TestInspectionCreator:
    """Creates realistic test inspection data for petroleum industry equipment."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.equipment_data = []
        self.inspection_data = []
        
    def create_test_equipment(self) -> List[Equipment]:
        """Create realistic petroleum industry equipment."""
        
        # Check if equipment already exists  
        existing_count = self.session.query(Equipment).count()
        if existing_count > 0:
            print(f"Found {existing_count} existing equipment items. Loading existing data...")
            equipment_list = self.session.query(Equipment).all()
            return equipment_list
        
        equipment_configs = [
            {
                "tag_number": "V-101",
                "description": "Crude Oil Storage Tank",
                "equipment_type": EquipmentType.PRESSURE_VESSEL,
                "design_pressure": Decimal("150.0"),  # PSI
                "design_temperature": Decimal("400.0"),  # °F
                "design_thickness": Decimal("0.500"),  # inches
                "material_specification": MaterialGrade.SA_516_70.value,
                "service_description": "Crude Oil Storage",
                "corrosion_allowance": Decimal("0.125"),
                "installation_date": datetime(2010, 3, 15),
                "criticality": EquipmentCriticality.HIGH
            },
            {
                "tag_number": "E-201",
                "description": "Crude Oil Heat Exchanger",
                "equipment_type": EquipmentType.HEAT_EXCHANGER,
                "design_pressure": Decimal("600.0"),
                "design_temperature": Decimal("650.0"),
                "design_thickness": Decimal("0.375"),
                "material_specification": MaterialGrade.SA_516_70.value,
                "service_description": "Crude Oil Heating",
                "corrosion_allowance": Decimal("0.062"),
                "installation_date": datetime(2015, 6, 20),
                "criticality": EquipmentCriticality.MEDIUM
            },
            {
                "tag_number": "T-301",
                "description": "Fractionation Tower",
                "equipment_type": EquipmentType.PRESSURE_VESSEL,
                "design_pressure": Decimal("275.0"),
                "design_temperature": Decimal("750.0"),
                "design_thickness": Decimal("0.750"),
                "material_specification": MaterialGrade.SA_387_22.value,
                "service_description": "Distillation",
                "corrosion_allowance": Decimal("0.125"),
                "installation_date": datetime(2008, 11, 5),
                "criticality": EquipmentCriticality.HIGH
            },
            {
                "tag_number": "P-401A",
                "description": "Crude Oil Transfer Pump Casing",
                "equipment_type": EquipmentType.PRESSURE_VESSEL,
                "design_pressure": Decimal("450.0"),
                "design_temperature": Decimal("300.0"),
                "design_thickness": Decimal("0.250"),
                "material_specification": MaterialGrade.SA_106_B.value,
                "service_description": "Crude Oil Transfer",
                "corrosion_allowance": Decimal("0.062"),
                "installation_date": datetime(2018, 2, 12),
                "criticality": EquipmentCriticality.HIGH
            },
            {
                "tag_number": "V-501",
                "description": "Hydrogen Separator",
                "equipment_type": EquipmentType.PRESSURE_VESSEL,
                "design_pressure": Decimal("1200.0"),
                "design_temperature": Decimal("500.0"),
                "design_thickness": Decimal("1.250"),
                "material_specification": MaterialGrade.SA_387_22.value,
                "service_description": "Hydrogen Separation",
                "corrosion_allowance": Decimal("0.125"),
                "installation_date": datetime(2012, 7, 8),
                "criticality": EquipmentCriticality.HIGH
            }
        ]
        
        equipment_list = []
        for config in equipment_configs:
            equipment = Equipment(**config)
            self.session.add(equipment)
            equipment_list.append(equipment)
            
        self.session.commit()
        print(f"Created {len(equipment_list)} test equipment items")
        return equipment_list
    
    def create_thickness_measurements(self, base_thickness: Decimal, condition: str) -> List[Dict[str, Any]]:
        """Create realistic thickness measurement data based on equipment condition."""
        
        measurements = []
        
        if condition == "excellent":
            # New equipment, minimal corrosion
            thickness_reduction = Decimal("0.010")  # 10 mils
            measurements = [
                {"location": "CML-01", "thickness": base_thickness - thickness_reduction, "minimum": base_thickness - Decimal("0.015")},
                {"location": "CML-02", "thickness": base_thickness - Decimal("0.008"), "minimum": base_thickness - Decimal("0.012")},
                {"location": "CML-03", "thickness": base_thickness - Decimal("0.005"), "minimum": base_thickness - Decimal("0.010")},
                {"location": "CML-04", "thickness": base_thickness - Decimal("0.012"), "minimum": base_thickness - Decimal("0.018")},
            ]
        elif condition == "good":
            # Moderate service, some corrosion
            thickness_reduction = Decimal("0.045")  # 45 mils
            measurements = [
                {"location": "CML-01", "thickness": base_thickness - thickness_reduction, "minimum": base_thickness - Decimal("0.055")},
                {"location": "CML-02", "thickness": base_thickness - Decimal("0.038"), "minimum": base_thickness - Decimal("0.048")},
                {"location": "CML-03", "thickness": base_thickness - Decimal("0.042"), "minimum": base_thickness - Decimal("0.052")},
                {"location": "CML-04", "thickness": base_thickness - Decimal("0.050"), "minimum": base_thickness - Decimal("0.065")},
                {"location": "CML-05", "thickness": base_thickness - Decimal("0.035"), "minimum": base_thickness - Decimal("0.045")},
            ]
        elif condition == "fair":
            # Aging equipment, significant corrosion
            thickness_reduction = Decimal("0.085")  # 85 mils
            measurements = [
                {"location": "CML-01", "thickness": base_thickness - thickness_reduction, "minimum": base_thickness - Decimal("0.095")},
                {"location": "CML-02", "thickness": base_thickness - Decimal("0.078"), "minimum": base_thickness - Decimal("0.088")},
                {"location": "CML-03", "thickness": base_thickness - Decimal("0.092"), "minimum": base_thickness - Decimal("0.102")},
                {"location": "CML-04", "thickness": base_thickness - Decimal("0.088"), "minimum": base_thickness - Decimal("0.098")},
                {"location": "CML-05", "thickness": base_thickness - Decimal("0.075"), "minimum": base_thickness - Decimal("0.085")},
                {"location": "CML-06", "thickness": base_thickness - Decimal("0.095"), "minimum": base_thickness - Decimal("0.110")},
            ]
        elif condition == "critical":
            # Equipment near end of life, heavy corrosion
            thickness_reduction = Decimal("0.145")  # 145 mils - concerning
            measurements = [
                {"location": "CML-01", "thickness": base_thickness - thickness_reduction, "minimum": base_thickness - Decimal("0.155")},
                {"location": "CML-02", "thickness": base_thickness - Decimal("0.138"), "minimum": base_thickness - Decimal("0.148")},
                {"location": "CML-03", "thickness": base_thickness - Decimal("0.152"), "minimum": base_thickness - Decimal("0.162")},
                {"location": "CML-04", "thickness": base_thickness - Decimal("0.148"), "minimum": base_thickness - Decimal("0.158")},
                {"location": "CML-05", "thickness": base_thickness - Decimal("0.135"), "minimum": base_thickness - Decimal("0.145")},
                {"location": "CML-06", "thickness": base_thickness - Decimal("0.158"), "minimum": base_thickness - Decimal("0.168")},
                {"location": "CML-07", "thickness": base_thickness - Decimal("0.142"), "minimum": base_thickness - Decimal("0.152")},
            ]
        
        return measurements
    
    def create_test_inspections(self, equipment_list: List[Equipment]) -> List[InspectionRecord]:
        """Create realistic inspection records for the equipment."""
        
        # Check if inspections already exist
        existing_inspections = self.session.query(InspectionRecord).count()
        if existing_inspections > 0:
            print(f"Found {existing_inspections} existing inspection records. Loading existing data...")
            return self.session.query(InspectionRecord).all()
        
        inspection_scenarios = [
            {
                "equipment": equipment_list[0],  # V-101 Crude Oil Storage Tank
                "date": datetime.now() - timedelta(days=30),
                "type": "ROUTINE",
                "surface_condition": "GOOD",
                "method": "UT",
                "thickness_condition": "good",
                "inspector": "John Smith, API 510 Inspector #12345",
                "notes": "Routine API 653 inspection. General corrosion observed in lower sections. No pitting detected. Recommend continued monitoring."
            },
            {
                "equipment": equipment_list[1],  # E-201 Heat Exchanger
                "date": datetime.now() - timedelta(days=15),
                "type": "TURNAROUND",
                "surface_condition": "EXCELLENT",
                "method": "UT",
                "thickness_condition": "excellent",
                "inspector": "Sarah Johnson, API 510 Inspector #67890",
                "notes": "Turnaround inspection completed. Equipment in excellent condition. Recently cleaned and inspected internally. No significant corrosion found."
            },
            {
                "equipment": equipment_list[2],  # T-301 Fractionation Tower
                "date": datetime.now() - timedelta(days=60),
                "type": "TURNAROUND",
                "surface_condition": "FAIR",
                "method": "UT",
                "thickness_condition": "fair",
                "inspector": "Michael Brown, API 510 Inspector #11111",
                "notes": "Major turnaround inspection. Aging equipment showing expected corrosion patterns. Several areas approaching minimum thickness. Consider metallurgical assessment for remaining life."
            },
            {
                "equipment": equipment_list[3],  # P-401A Pump Casing
                "date": datetime.now() - timedelta(days=7),
                "type": "ROUTINE",
                "surface_condition": "EXCELLENT",
                "method": "RT",
                "thickness_condition": "excellent",
                "inspector": "Lisa Davis, Level II RT Tech #22222",
                "notes": "Radiographic inspection of pump casing. No internal defects detected. Equipment in excellent condition for continued service."
            },
            {
                "equipment": equipment_list[4],  # V-501 Hydrogen Separator
                "date": datetime.now() - timedelta(days=5),
                "type": "EMERGENCY",
                "surface_condition": "POOR",
                "method": "UT",
                "thickness_condition": "critical",
                "inspector": "Robert Wilson, API 510 Inspector #33333",
                "notes": "EMERGENCY INSPECTION - Hydrogen attack suspected. Significant thickness loss detected in multiple locations. Equipment requires immediate engineering assessment. Consider replacement."
            }
        ]
        
        inspections = []
        for scenario in inspection_scenarios:
            # Create thickness measurements
            thickness_data = self.create_thickness_measurements(
                scenario["equipment"].design_thickness, 
                scenario["thickness_condition"]
            )
            
            # Create inspection record
            inspection = InspectionRecord(
                id=uuid.uuid4(),
                equipment_id=scenario["equipment"].id,
                inspection_date=scenario["date"],
                inspection_type=scenario["type"],
                inspector_name=scenario["inspector"],
                thickness_readings=thickness_data,
                min_thickness_found=min([Decimal(str(m["minimum"])) for m in thickness_data]),
                avg_thickness=sum([Decimal(str(m["thickness"])) for m in thickness_data]) / len(thickness_data),
                confidence_level=self._calculate_confidence(scenario["surface_condition"], scenario["method"]),
                report_number=f"INSP-{scenario['equipment'].tag_number}-{scenario['date'].strftime('%Y%m%d')}"
            )
            
            self.session.add(inspection)
            inspections.append(inspection)
            
        self.session.commit()
        print(f"Created {len(inspections)} test inspections")
        return inspections
    
    def _calculate_confidence(self, surface_condition: str, method: str) -> Decimal:
        """Calculate measurement confidence based on conditions."""
        base_confidence = {
            "UT": Decimal("95.0"),
            "RT": Decimal("98.0"),
            "MT": Decimal("85.0"),
            "PT": Decimal("80.0")
        }[method]
        
        condition_modifier = {
            "EXCELLENT": Decimal("1.0"),
            "GOOD": Decimal("0.95"),
            "FAIR": Decimal("0.85"),
            "POOR": Decimal("0.70"),
            "CORRODED": Decimal("0.60")
        }[surface_condition]
        
        return base_confidence * condition_modifier
    
    def create_api579_calculations(self, inspections: List[InspectionRecord]) -> List[API579Calculation]:
        """Create API 579 fitness-for-service calculations."""
        
        # Check if calculations already exist
        existing_calculations = self.session.query(API579Calculation).count()
        if existing_calculations > 0:
            print(f"Found {existing_calculations} existing API 579 calculations. Loading existing data...")
            return self.session.query(API579Calculation).all()
            
        calculations = []
        
        for inspection in inspections:
            # Get minimum thickness from measurements
            min_thickness = min([Decimal(str(m["minimum"])) for m in inspection.thickness_readings])
            current_thickness = min([Decimal(str(m["thickness"])) for m in inspection.thickness_readings])
            
            # Calculate API 579 parameters
            equipment = inspection.equipment
            
            # Calculate minimum required thickness (simplified API 579)
            # t_min = PR / (SE - 0.6P) for internal pressure
            P = equipment.design_pressure
            R = equipment.diameter / 2  # radius
            S = Decimal("17500.0")  # allowable stress for SA-516-70 at design temp
            E = Decimal("1.0")  # joint efficiency
            
            if (S * E - Decimal("0.6") * P) > 0:
                t_min_required = (P * R) / (S * E - Decimal("0.6") * P)
            else:
                t_min_required = equipment.design_thickness  # fallback
                
            # Calculate Remaining Strength Factor (RSF)
            # RSF = (t_current - FCA - t_min) / (t_nominal - t_min)
            fca = equipment.corrosion_allowance or Decimal("0.0")
            numerator = current_thickness - fca - t_min_required
            denominator = equipment.design_thickness - t_min_required
            
            if denominator > 0:
                rsf = numerator / denominator
            else:
                rsf = Decimal("0.0")
                
            # Calculate remaining life (simplified)
            # Based on corrosion rate from thickness loss
            years_in_service = (datetime.now() - equipment.installation_date).days / 365.25
            total_loss = equipment.design_thickness - current_thickness
            corrosion_rate = total_loss / Decimal(str(years_in_service))
            
            if corrosion_rate > 0:
                allowable_loss = current_thickness - t_min_required - fca
                remaining_life = allowable_loss / corrosion_rate
            else:
                remaining_life = Decimal("50.0")  # Very long life if no corrosion
                
            # Create calculation record
            calculation = API579Calculation(
                id=uuid.uuid4(),
                inspection_record_id=inspection.id,
                calculation_type="Level 1 Assessment",
                calculation_method="General Metal Loss Assessment",
                performed_by="System Generated",
                input_parameters={
                    "design_pressure": float(P),
                    "design_thickness": float(equipment.design_thickness), 
                    "current_thickness": float(current_thickness),
                    "allowable_stress": float(S),
                    "joint_efficiency": float(E),
                    "corrosion_allowance": float(fca)
                },
                minimum_required_thickness=t_min_required,
                remaining_strength_factor=rsf,
                maximum_allowable_pressure=P * rsf,  # Simplified
                remaining_life_years=remaining_life,
                next_inspection_date=datetime.now() + timedelta(days=int(min(remaining_life * 365 / 2, 1095))),  # Half remaining life or 3 years max
                fitness_for_service="FIT" if rsf >= Decimal("0.9") else "CONDITIONAL" if rsf >= Decimal("0.7") else "UNFIT",
                risk_level="LOW" if rsf >= Decimal("0.9") else "MEDIUM" if rsf >= Decimal("0.7") else "HIGH",
                recommendations=self._generate_recommendations(rsf, remaining_life),
                assumptions={
                    "uniform_corrosion": True,
                    "no_localized_damage": True,
                    "standard_operating_conditions": True,
                    "assessment_level": "Level 1"
                },
                confidence_score=Decimal("85.0")  # Typical for Level 1 assessments
            )
            
            self.session.add(calculation)
            calculations.append(calculation)
            
        self.session.commit()
        print(f"Created {len(calculations)} API 579 calculations")
        return calculations
    
    def _generate_recommendations(self, rsf: Decimal, remaining_life: Decimal) -> str:
        """Generate safety recommendations based on calculation results."""
        recommendations = []
        
        if rsf < Decimal("0.9"):
            recommendations.append("⚠️ CRITICAL: RSF below 0.9 - Immediate engineering review required")
            recommendations.append("Consider pressure reduction or repair")
            
        if remaining_life < Decimal("2.0"):
            recommendations.append("⚠️ WARNING: Remaining life less than 2 years")
            recommendations.append("Plan for replacement or major repair")
            
        if rsf < Decimal("0.7"):
            recommendations.append("🚨 URGENT: Equipment may be unsafe for continued operation")
            recommendations.append("Consider immediate shutdown pending further assessment")
            
        if Decimal("0.9") <= rsf <= Decimal("1.0") and remaining_life >= Decimal("5.0"):
            recommendations.append("✅ Equipment acceptable for continued service")
            recommendations.append("Monitor with routine inspection program")
            
        if not recommendations:
            recommendations.append("✅ Equipment in good condition")
            recommendations.append("Continue normal inspection intervals")
            
        return " | ".join(recommendations)
    
    def run(self):
        """Execute the complete test data creation process."""
        try:
            print("🏭 Creating test data for Mechanical Integrity Management System")
            print("=" * 60)
            
            # Create equipment
            equipment_list = self.create_test_equipment()
            
            # Create inspections
            inspections = self.create_test_inspections(equipment_list)
            
            # Create API 579 calculations
            calculations = self.create_api579_calculations(inspections)
            
            print("\n✅ Test data creation completed successfully!")
            print(f"📊 Summary:")
            print(f"   • Equipment items: {len(equipment_list)}")
            print(f"   • Inspection records: {len(inspections)}")
            print(f"   • API 579 calculations: {len(calculations)}")
            print("\n🔗 Access the data:")
            print("   • Backend API: http://localhost:8000/docs")
            print("   • Frontend: http://localhost:5173")
            print("   • Equipment list: GET /api/v1/equipment")
            print("   • Inspections: GET /api/v1/inspections")
            print("   • Calculations: GET /api/v1/calculations")
            
        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            self.session.rollback()
            raise
        finally:
            self.session.close()

if __name__ == "__main__":
    creator = TestInspectionCreator()
    creator.run()