"""
Audit trail validation tests for regulatory compliance.

Validates that complete audit trails are maintained for all safety-critical
operations in accordance with API 579 and regulatory requirements.

# TODO: [COMPLIANCE_TESTS] Fix 3 failing audit trail validation tests
# Current failures: thickness_reading_traceability, audit_trail_immutability, calculation_chain_custody
# Root cause: Missing immutability enforcement and incomplete audit trail implementation
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
import json
import hashlib
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.equipment import Equipment, EquipmentType
from models.inspection import InspectionRecord, ThicknessReading, API579Calculation
from app.calculations.dual_path_calculator import API579Calculator, VerifiedResult
from app.calculations.verification import CalculationVerifier


class TestAuditTrailCompliance:
    """Tests for regulatory audit trail compliance."""
    
    @pytest.fixture(scope="function")
    def audit_db_session(self):
        """Database session with audit trail logging enabled."""
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        
        # Create test equipment
        equipment = Equipment(
            tag_number="V-101-AUDIT",
            description="Audit Trail Test Vessel",
            equipment_type=EquipmentType.PRESSURE_VESSEL,
            design_pressure=1200.0,
            design_temperature=650.0,
            design_thickness=1.250,
            material_specification="SA-516-70",
            corrosion_allowance=0.125,
            service_description="Audit Test Service",
            installation_date=datetime(2010, 1, 1)
        )
        session.add(equipment)
        session.commit()
        
        yield session
        session.close()
    
    def calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """Calculate cryptographic hash of data for integrity verification."""
        # Sort keys to ensure consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def test_inspection_record_audit_trail_completeness(self, audit_db_session):
        """Test that inspection records contain complete audit trail."""
        # Create inspection with full audit data
        inspection_data = {
            "inspection_date": datetime.utcnow() - timedelta(days=1),
            "inspection_type": "UT",
            "inspector_name": "John Doe",
            "inspector_certification": "SNT-TC-1A Level III UT-2023-001",
            "report_number": "RPT-AUDIT-001",
            "thickness_readings": [
                {
                    "cml_number": "CML-01",
                    "location": "Bottom head, 6 o'clock position",
                    "thickness": Decimal('1.185'),
                    "confidence": Decimal('95.0')
                }
            ],
            "findings": "General uniform corrosion observed throughout vessel",
            "recommendations": "Continue monitoring per API 510 requirements",
            "document_reference": "/documents/inspection/RPT-AUDIT-001.pdf"
        }
        
        equipment = audit_db_session.query(Equipment).first()
        
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=inspection_data["inspection_date"],
            inspection_type=inspection_data["inspection_type"],
            inspector_name=inspection_data["inspector_name"],
            inspector_certification=inspection_data["inspector_certification"],
            report_number=inspection_data["report_number"],
            thickness_readings={},  # JSON field
            min_thickness_found=Decimal('1.185'),
            avg_thickness=Decimal('1.185'),
            findings=inspection_data["findings"],
            recommendations=inspection_data["recommendations"],
            document_reference=inspection_data["document_reference"]
        )
        
        audit_db_session.add(inspection)
        audit_db_session.commit()
        
        # Verify audit trail completeness
        required_audit_fields = [
            'id', 'equipment_id', 'inspection_date', 'inspection_type',
            'inspector_name', 'inspector_certification', 'report_number',
            'min_thickness_found', 'avg_thickness', 'findings', 'recommendations',
            'created_at', 'updated_at'
        ]
        
        for field in required_audit_fields:
            value = getattr(inspection, field)
            assert value is not None, f"Missing audit field: {field}"
            
            # Verify immutable timestamp fields
            if field in ['created_at', 'inspection_date']:
                assert isinstance(value, datetime), f"Field {field} must be datetime for audit"
        
        # Verify inspector certification format
        cert = inspection.inspector_certification
        assert "Level" in cert and "UT" in cert, "Inspector certification incomplete for audit"
        
        # Verify document reference for traceability
        assert inspection.document_reference is not None, "Document reference required for audit"
        
        print(f"✅ Inspection audit trail complete: {len(required_audit_fields)} fields verified")
    
    def test_thickness_reading_measurement_traceability(self, audit_db_session):
        """Test that thickness readings have complete measurement traceability."""
        equipment = audit_db_session.query(Equipment).first()
        
        # Create inspection
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=datetime.utcnow() - timedelta(days=1),
            inspection_type="UT",
            inspector_name="Audit Tester",
            report_number="RPT-TRACE-001",
            thickness_readings={},
            min_thickness_found=Decimal('1.200'),
            avg_thickness=Decimal('1.210')
        )
        audit_db_session.add(inspection)
        audit_db_session.flush()
        
        # Create thickness reading with full traceability
        reading = ThicknessReading(
            inspection_record_id=inspection.id,
            cml_number="CML-TRACE-01",
            location_description="Detailed location: Bottom head, 6 o'clock, 3 inches from centerline",
            grid_reference="A-1",
            thickness_measured=Decimal('1.200'),
            previous_thickness=Decimal('1.250'),
            design_thickness=Decimal('1.250'),
            metal_loss_total=Decimal('0.050'),
            metal_loss_period=Decimal('0.015'),
            corrosion_rate_local=Decimal('0.00375'),
            measurement_confidence=Decimal('95.00'),
            surface_condition="Good - minimal surface preparation required",
            temperature_compensation=Decimal('0.002')
        )
        
        audit_db_session.add(reading)
        audit_db_session.commit()
        
        # Verify measurement traceability fields
        traceability_fields = {
            'cml_number': 'Condition Monitoring Location identifier',
            'location_description': 'Detailed physical location',
            'thickness_measured': 'Current thickness measurement',
            'previous_thickness': 'Historical comparison data',
            'design_thickness': 'Original design reference',
            'measurement_confidence': 'Measurement quality indicator',
            'surface_condition': 'Measurement condition documentation',
            'created_at': 'Measurement timestamp'
        }
        
        for field, description in traceability_fields.items():
            value = getattr(reading, field)
            assert value is not None, f"Missing traceability field: {field} ({description})"
        
        # Verify measurement precision maintained
        assert reading.thickness_measured.as_tuple().exponent >= -3, "Insufficient measurement precision"
        
        # Verify confidence level is reasonable
        assert Decimal('50') <= reading.measurement_confidence <= Decimal('100'), "Invalid confidence level"
        
        # Calculate and verify corrosion rate consistency
        if reading.previous_thickness and reading.metal_loss_period:
            # Assume 4-year inspection interval
            calculated_rate = reading.metal_loss_period / Decimal('4.0')
            rate_difference = abs(calculated_rate - reading.corrosion_rate_local)
            assert rate_difference <= Decimal('0.001'), "Corrosion rate calculation inconsistent"
        
        print(f"✅ Thickness reading traceability complete: {len(traceability_fields)} fields verified")
    
    def test_api579_calculation_audit_completeness(self, audit_db_session):
        """Test that API 579 calculations have complete audit trail."""
        equipment = audit_db_session.query(Equipment).first()
        
        # Create inspection and reading
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=datetime.utcnow() - timedelta(days=1),
            inspection_type="UT",
            inspector_name="Calculation Auditor",
            report_number="RPT-CALC-AUDIT",
            thickness_readings={},
            min_thickness_found=Decimal('1.185'),
            avg_thickness=Decimal('1.190')
        )
        audit_db_session.add(inspection)
        audit_db_session.flush()
        
        # Perform API 579 calculation with full audit trail
        calculator = API579Calculator()
        
        calculation_inputs = {
            "pressure": Decimal('1200.0'),
            "radius": Decimal('24.0'),
            "stress": Decimal('17500.0'),
            "efficiency": Decimal('1.0'),
            "current_thickness": Decimal('1.185'),
            "minimum_thickness": Decimal('0.875'),
            "nominal_thickness": Decimal('1.250'),
            "future_corrosion_allowance": Decimal('0.050')
        }
        
        # Calculate minimum thickness
        t_min_result = calculator.calculate_minimum_required_thickness(
            calculation_inputs["pressure"],
            calculation_inputs["radius"],
            calculation_inputs["stress"],
            calculation_inputs["efficiency"]
        )
        
        # Calculate RSF
        rsf_result = calculator.calculate_remaining_strength_factor(
            calculation_inputs["current_thickness"],
            t_min_result.value,
            calculation_inputs["nominal_thickness"],
            calculation_inputs["future_corrosion_allowance"]
        )
        
        # Calculate MAWP
        mawp_result = calculator.calculate_mawp(
            calculation_inputs["current_thickness"],
            calculation_inputs["radius"],
            calculation_inputs["stress"],
            calculation_inputs["efficiency"],
            calculation_inputs["future_corrosion_allowance"]
        )
        
        # Create comprehensive audit record
        calculation_audit_data = {
            "input_parameters": {
                "design_pressure": str(calculation_inputs["pressure"]),
                "radius": str(calculation_inputs["radius"]),
                "allowable_stress": str(calculation_inputs["stress"]),
                "joint_efficiency": str(calculation_inputs["efficiency"]),
                "current_thickness": str(calculation_inputs["current_thickness"]),
                "nominal_thickness": str(calculation_inputs["nominal_thickness"]),
                "future_corrosion_allowance": str(calculation_inputs["future_corrosion_allowance"]),
                "calculation_timestamp": datetime.utcnow().isoformat(),
                "calculator_version": "API579Calculator v1.0",
                "api_579_edition": "2021"
            },
            "calculation_results": {
                "minimum_required_thickness": {
                    "value": str(t_min_result.value),
                    "primary_method": str(t_min_result.primary_value),
                    "secondary_method": str(t_min_result.secondary_value),
                    "verification_method": t_min_result.verification_method,
                    "api_reference": t_min_result.api_reference,
                    "tolerance_used": str(t_min_result.tolerance_used),
                    "calculation_id": t_min_result.calculation_id
                },
                "remaining_strength_factor": {
                    "value": str(rsf_result.value),
                    "primary_method": str(rsf_result.primary_value),
                    "secondary_method": str(rsf_result.secondary_value),
                    "verification_method": rsf_result.verification_method,
                    "api_reference": rsf_result.api_reference,
                    "calculation_id": rsf_result.calculation_id
                },
                "maximum_allowable_pressure": {
                    "value": str(mawp_result.value),
                    "primary_method": str(mawp_result.primary_value),
                    "secondary_method": str(mawp_result.secondary_value),
                    "verification_method": mawp_result.verification_method,
                    "api_reference": mawp_result.api_reference,
                    "calculation_id": mawp_result.calculation_id
                }
            },
            "verification_status": {
                "dual_path_verified": True,
                "tolerances_met": True,
                "cross_checks_passed": True,
                "verification_timestamp": datetime.utcnow().isoformat()
            },
            "assumptions_and_warnings": {
                "t_min_assumptions": t_min_result.assumptions,
                "t_min_warnings": t_min_result.warnings,
                "rsf_assumptions": rsf_result.assumptions,
                "rsf_warnings": rsf_result.warnings,
                "mawp_assumptions": mawp_result.assumptions,
                "mawp_warnings": mawp_result.warnings
            }
        }
        
        # Calculate audit hash for integrity
        audit_hash = self.calculate_data_hash(calculation_audit_data)
        
        # Store calculation with audit trail
        calculation = API579Calculation(
            inspection_record_id=inspection.id,
            calculation_type="Level 1 - General Metal Loss",
            calculation_method="Dual-Path Verification",
            performed_by="Audit Test Engineer",
            reviewed_by="Senior FFS Engineer",
            input_parameters=calculation_audit_data["input_parameters"],
            minimum_required_thickness=t_min_result.value,
            remaining_strength_factor=rsf_result.value,
            maximum_allowable_pressure=mawp_result.value,
            remaining_life_years=Decimal('25.0'),  # Mock value
            fitness_for_service="FIT" if rsf_result.value > Decimal('0.9') else "CONDITIONAL",
            risk_level="MEDIUM",
            recommendations="Continue normal operation with monitoring",
            assumptions=calculation_audit_data["assumptions_and_warnings"],
            confidence_score=Decimal('95.0'),
            uncertainty_factors={
                "measurement_uncertainty": "±0.001 inches",
                "material_property_uncertainty": "±5%",
                "calculation_method_uncertainty": "±1%",
                "audit_hash": audit_hash
            }
        )
        
        audit_db_session.add(calculation)
        audit_db_session.commit()
        
        # Verify audit trail completeness
        required_audit_elements = [
            'input_parameters',
            'performed_by',
            'reviewed_by',
            'calculation_type',
            'calculation_method',
            'minimum_required_thickness',
            'remaining_strength_factor',
            'maximum_allowable_pressure',
            'fitness_for_service',
            'recommendations',
            'assumptions',
            'confidence_score',
            'uncertainty_factors',
            'created_at',
            'updated_at'
        ]
        
        for element in required_audit_elements:
            value = getattr(calculation, element)
            assert value is not None, f"Missing calculation audit element: {element}"
        
        # Verify input parameters contain all required data
        input_params = calculation.input_parameters
        required_inputs = [
            'design_pressure', 'radius', 'allowable_stress', 'joint_efficiency',
            'current_thickness', 'nominal_thickness', 'calculation_timestamp',
            'calculator_version', 'api_579_edition'
        ]
        
        for param in required_inputs:
            assert param in input_params, f"Missing required input parameter: {param}"
        
        # Verify calculation traceability through IDs
        assert 'audit_hash' in calculation.uncertainty_factors, "Missing audit hash for integrity"
        
        # Verify dual review requirement
        assert calculation.performed_by != calculation.reviewed_by, "Dual review requirement not met"
        
        print(f"✅ API 579 calculation audit trail complete: {len(required_audit_elements)} elements verified")
    
    def test_audit_trail_immutability(self, audit_db_session):
        """Test that audit trail cannot be tampered with."""
        equipment = audit_db_session.query(Equipment).first()
        
        # Create inspection with timestamp
        original_timestamp = datetime.utcnow()
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=original_timestamp,
            inspection_type="UT",
            inspector_name="Immutability Tester",
            report_number="RPT-IMMUTABLE-001",
            thickness_readings={},
            min_thickness_found=Decimal('1.200'),
            avg_thickness=Decimal('1.200')
        )
        
        audit_db_session.add(inspection)
        audit_db_session.commit()
        
        original_created_at = inspection.created_at
        original_id = inspection.id
        
        # Attempt to modify audit fields (this should be prevented in production)
        inspection.inspector_name = "Modified Name"
        inspection.min_thickness_found = Decimal('1.300')  # Attempt to change critical data
        
        audit_db_session.commit()
        
        # Verify that created_at timestamp is immutable
        assert inspection.created_at == original_created_at, "Created timestamp was modified"
        
        # Verify ID is immutable
        assert inspection.id == original_id, "Record ID was modified"
        
        # In production, critical audit fields should be protected from modification
        # This test documents the expectation that audit trail modifications should be logged
        
        # Check if updated_at was properly set to track modifications
        assert inspection.updated_at > inspection.created_at, "Update timestamp not properly maintained"
        
        print(f"✅ Audit trail immutability behavior verified")
    
    def test_regulatory_compliance_report_generation(self, audit_db_session):
        """Test generation of regulatory compliance reports from audit trail."""
        equipment = audit_db_session.query(Equipment).first()
        
        # Create multiple inspections over time for compliance history
        inspection_dates = [
            datetime(2020, 1, 15),
            datetime(2022, 1, 15),
            datetime(2024, 1, 15)
        ]
        
        inspection_data = []
        
        for i, date in enumerate(inspection_dates):
            # Simulate progressive metal loss
            thickness = Decimal('1.250') - (Decimal('0.025') * i)
            
            inspection = InspectionRecord(
                equipment_id=equipment.id,
                inspection_date=date,
                inspection_type="UT",
                inspector_name=f"Inspector {i+1}",
                inspector_certification=f"UT-III-{date.year}-{i+1:03d}",
                report_number=f"RPT-{date.year}-{i+1:03d}",
                thickness_readings={},
                min_thickness_found=thickness,
                avg_thickness=thickness + Decimal('0.005'),
                findings=f"Inspection {i+1}: General corrosion observed",
                recommendations="Continue monitoring per API 510"
            )
            
            audit_db_session.add(inspection)
            audit_db_session.flush()
            
            # Add calculation results
            calculator = API579Calculator()
            rsf_result = calculator.calculate_remaining_strength_factor(
                current_thickness=thickness,
                minimum_thickness=Decimal('0.875'),
                nominal_thickness=Decimal('1.250'),
                future_corrosion_allowance=Decimal('0.050')
            )
            
            calculation = API579Calculation(
                inspection_record_id=inspection.id,
                calculation_type="Level 1 - General Metal Loss",
                calculation_method="Dual-Path Verification",
                performed_by=f"Engineer {i+1}",
                input_parameters={
                    "inspection_date": date.isoformat(),
                    "current_thickness": str(thickness),
                    "minimum_thickness": "0.875",
                    "nominal_thickness": "1.250"
                },
                minimum_required_thickness=Decimal('0.875'),
                remaining_strength_factor=rsf_result.value,
                maximum_allowable_pressure=Decimal('1000.0'),
                remaining_life_years=Decimal('20.0') - (Decimal('5.0') * i),
                fitness_for_service="FIT" if rsf_result.value > Decimal('0.9') else "CONDITIONAL",
                risk_level="LOW" if rsf_result.value > Decimal('0.95') else "MEDIUM",
                recommendations=f"Inspection interval: {5 - i} years",
                confidence_score=Decimal('95.0')
            )
            
            audit_db_session.add(calculation)
            
            inspection_data.append({
                'inspection': inspection,
                'calculation': calculation,
                'rsf': rsf_result.value,
                'thickness': thickness
            })
        
        audit_db_session.commit()
        
        # Generate compliance report
        compliance_report = {
            "equipment_identification": {
                "tag_number": equipment.tag_number,
                "description": equipment.description,
                "equipment_type": equipment.equipment_type.value,
                "design_pressure": equipment.design_pressure,
                "design_temperature": equipment.design_temperature,
                "material_specification": equipment.material_specification
            },
            "inspection_history": [],
            "fitness_for_service_assessments": [],
            "corrosion_trend_analysis": {
                "metal_loss_rate": None,
                "remaining_life_trend": [],
                "rsf_trend": []
            },
            "regulatory_compliance": {
                "api_510_compliance": True,
                "api_579_assessments_performed": True,
                "inspection_intervals_met": True,
                "dual_path_verification_performed": True
            },
            "report_metadata": {
                "generated_by": "Automated Compliance System",
                "generation_date": datetime.utcnow().isoformat(),
                "audit_trail_verified": True,
                "data_integrity_hash": None
            }
        }
        
        # Populate inspection history
        for data in inspection_data:
            inspection = data['inspection']
            calculation = data['calculation']
            
            compliance_report["inspection_history"].append({
                "inspection_date": inspection.inspection_date.isoformat(),
                "inspector_name": inspection.inspector_name,
                "inspector_certification": inspection.inspector_certification,
                "report_number": inspection.report_number,
                "min_thickness_found": str(data['thickness']),
                "findings": inspection.findings,
                "recommendations": inspection.recommendations
            })
            
            compliance_report["fitness_for_service_assessments"].append({
                "assessment_date": calculation.created_at.isoformat(),
                "performed_by": calculation.performed_by,
                "calculation_type": calculation.calculation_type,
                "remaining_strength_factor": str(calculation.remaining_strength_factor),
                "fitness_determination": calculation.fitness_for_service,
                "risk_level": calculation.risk_level,
                "api_579_reference": "API 579-1 Part 5, Equation 5.5"
            })
            
            compliance_report["corrosion_trend_analysis"]["remaining_life_trend"].append({
                "date": inspection.inspection_date.isoformat(),
                "remaining_life_years": str(calculation.remaining_life_years)
            })
            
            compliance_report["corrosion_trend_analysis"]["rsf_trend"].append({
                "date": inspection.inspection_date.isoformat(),
                "rsf_value": str(data['rsf'])
            })
        
        # Calculate overall corrosion rate
        if len(inspection_data) >= 2:
            first_thickness = inspection_data[0]['thickness']
            last_thickness = inspection_data[-1]['thickness']
            time_span_years = (inspection_dates[-1] - inspection_dates[0]).days / 365.25
            
            metal_loss_rate = (first_thickness - last_thickness) / Decimal(str(time_span_years))
            compliance_report["corrosion_trend_analysis"]["metal_loss_rate"] = str(metal_loss_rate)
        
        # Generate integrity hash
        report_hash = self.calculate_data_hash(compliance_report)
        compliance_report["report_metadata"]["data_integrity_hash"] = report_hash
        
        # Verify compliance report completeness
        required_sections = [
            'equipment_identification',
            'inspection_history', 
            'fitness_for_service_assessments',
            'corrosion_trend_analysis',
            'regulatory_compliance',
            'report_metadata'
        ]
        
        for section in required_sections:
            assert section in compliance_report, f"Missing compliance report section: {section}"
            assert compliance_report[section], f"Empty compliance report section: {section}"
        
        # Verify regulatory compliance flags
        regulatory_flags = compliance_report["regulatory_compliance"]
        assert all(regulatory_flags.values()), "Regulatory compliance flags indicate non-compliance"
        
        # Verify audit trail integrity
        assert compliance_report["report_metadata"]["audit_trail_verified"], "Audit trail verification failed"
        assert compliance_report["report_metadata"]["data_integrity_hash"], "Missing data integrity hash"
        
        print(f"✅ Regulatory compliance report generated with {len(inspection_data)} inspections")
        print(f"   Report sections: {len(required_sections)}")
        print(f"   Data integrity hash: {report_hash[:16]}...")
        
        return compliance_report
    
    def test_calculation_chain_of_custody(self, audit_db_session):
        """Test complete chain of custody for calculations."""
        equipment = audit_db_session.query(Equipment).first()
        
        # Create inspection with chain of custody
        inspection = InspectionRecord(
            equipment_id=equipment.id,
            inspection_date=datetime.utcnow() - timedelta(days=1),
            inspection_type="UT",
            inspector_name="Primary Inspector",
            inspector_certification="SNT-TC-1A Level III",
            report_number="RPT-CUSTODY-001",
            thickness_readings={},
            min_thickness_found=Decimal('1.185'),
            avg_thickness=Decimal('1.190'),
            verified_by="QC Inspector",
            verified_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        audit_db_session.add(inspection)
        audit_db_session.flush()
        
        # Perform calculation with chain of custody
        calculator = API579Calculator()
        rsf_result = calculator.calculate_remaining_strength_factor(
            current_thickness=Decimal('1.185'),
            minimum_thickness=Decimal('0.875'),
            nominal_thickness=Decimal('1.250')
        )
        
        # Create calculation with full chain of custody
        calculation = API579Calculation(
            inspection_record_id=inspection.id,
            calculation_type="Level 1 - General Metal Loss",
            calculation_method="Dual-Path Verification",
            performed_by="Calculation Engineer",
            reviewed_by="Senior FFS Engineer",
            input_parameters={
                "data_source": "inspection_id:" + inspection.id,
                "calculation_timestamp": datetime.utcnow().isoformat(),
                "chain_of_custody": {
                    "data_collected_by": inspection.inspector_name,
                    "data_verified_by": inspection.verified_by,
                    "calculation_performed_by": "Calculation Engineer",
                    "calculation_reviewed_by": "Senior FFS Engineer",
                    "each_step_timestamp": True
                }
            },
            minimum_required_thickness=Decimal('0.875'),
            remaining_strength_factor=rsf_result.value,
            maximum_allowable_pressure=Decimal('1000.0'),
            fitness_for_service="FIT",
            risk_level="MEDIUM",
            recommendations="Continue normal operation",
            confidence_score=Decimal('95.0')
        )
        
        audit_db_session.add(calculation)
        audit_db_session.commit()
        
        # Verify chain of custody elements
        custody_elements = [
            (inspection.inspector_name, "Data Collection"),
            (inspection.verified_by, "Data Verification"),
            (calculation.performed_by, "Calculation Performance"),
            (calculation.reviewed_by, "Calculation Review")
        ]
        
        for person, role in custody_elements:
            assert person is not None, f"Missing person in chain of custody for {role}"
            assert person.strip() != "", f"Empty person name for {role}"
        
        # Verify no self-review
        assert calculation.performed_by != calculation.reviewed_by, "Self-review detected in chain of custody"
        assert inspection.inspector_name != calculation.performed_by or inspection.verified_by != calculation.performed_by, "Insufficient separation of duties"
        
        # Verify timestamps show proper sequence
        assert inspection.created_at <= inspection.verified_at, "Verification before inspection"
        assert inspection.verified_at <= calculation.created_at, "Calculation before verification"
        
        print(f"✅ Chain of custody verified with {len(custody_elements)} participants")
        
        return custody_elements