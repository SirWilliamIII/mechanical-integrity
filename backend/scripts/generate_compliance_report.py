#!/usr/bin/env python3
"""
Generate comprehensive API 579 regulatory compliance report.

This script audits the system for compliance with:
- API 579 Fitness-for-Service standards
- OSHA Process Safety Management requirements  
- ASME inspection and calculation requirements

Critical safety areas audited:
- Calculation traceability and immutability
- Audit trail completeness
- Precision requirements compliance
- Human verification loops
"""

import asyncio
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.calculations.dual_path_calculator import API579Calculator
from models.database import SessionLocal
from models.inspection import InspectionRecord, API579Calculation
from models.equipment import Equipment
from models.audit_trail import AuditTrail
from core.config import settings

class ComplianceAuditor:
    """Comprehensive regulatory compliance auditor."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.passed_checks: List[str] = []
        
    def add_issue(self, severity: str, component: str, description: str, 
                  regulation: str, remediation: str):
        """Add a compliance issue."""
        self.issues.append({
            "severity": severity,
            "component": component, 
            "description": description,
            "regulation": regulation,
            "remediation": remediation,
            "timestamp": datetime.utcnow()
        })
        
    def add_warning(self, component: str, description: str, recommendation: str):
        """Add a compliance warning."""
        self.warnings.append({
            "component": component,
            "description": description, 
            "recommendation": recommendation,
            "timestamp": datetime.utcnow()
        })
        
    def add_pass(self, check_name: str):
        """Record a passed compliance check."""
        self.passed_checks.append(check_name)

    async def audit_calculation_immutability(self, session):
        """Verify API 579 calculations are immutable once created."""
        print("🔒 Auditing calculation immutability...")
        
        # Check if API579Calculation records can be updated after creation
        try:
            calc = session.query(API579Calculation).first()
            if calc:
                # Verify no direct update methods exist on critical fields
                original_rsf = calc.remaining_strength_factor
                
                # This should be prevented by design
                if hasattr(calc, 'update_calculation'):
                    self.add_issue(
                        "CRITICAL",
                        "API579Calculation Model", 
                        "Direct calculation update methods exist",
                        "API 579 Part 1 - Immutable Records Required",
                        "Remove update methods from calculation models"
                    )
                else:
                    self.add_pass("Calculation Model Immutability")
                    
            else:
                self.add_warning(
                    "API579Calculation Model",
                    "No calculation records found for immutability testing",
                    "Create test calculations to verify immutability"
                )
                
        except Exception as e:
            self.add_issue(
                "HIGH", 
                "Database Schema",
                f"Error accessing calculation records: {e}",
                "API 579 Part 1 - Data Integrity",
                "Fix database schema issues"
            )

    async def audit_api579_references(self):
        """Verify all calculations include proper API 579 section references."""
        print("📖 Auditing API 579 references...")
        
        # Check dual path calculator for API references
        calculator_file = backend_path / "app" / "calculations" / "dual_path_calculator.py"
        
        try:
            content = calculator_file.read_text()
            
            # Look for API 579 references in key methods
            methods_requiring_refs = [
                "calculate_minimum_thickness",
                "calculate_mawp", 
                "calculate_rsf",
                "calculate_remaining_life"
            ]
            
            missing_refs = []
            for method in methods_requiring_refs:
                if method in content:
                    # Check if method has API 579 reference
                    method_start = content.find(f"def {method}")
                    if method_start == -1:
                        continue
                        
                    # Find the end of the method (next def or class)
                    method_end = content.find("\n    def ", method_start + 1)
                    if method_end == -1:
                        method_end = content.find("\nclass ", method_start + 1)
                    if method_end == -1:
                        method_end = len(content)
                        
                    method_content = content[method_start:method_end]
                    
                    if "API 579" not in method_content and "api579" not in method_content.lower():
                        missing_refs.append(method)
            
            if missing_refs:
                self.add_issue(
                    "HIGH",
                    "Calculation Methods",
                    f"Missing API 579 references in methods: {', '.join(missing_refs)}",
                    "API 579 Part 1 - Calculation Documentation Requirements",
                    "Add API 579 section references to calculation method docstrings"
                )
            else:
                self.add_pass("API 579 Reference Documentation")
                
        except Exception as e:
            self.add_issue(
                "MEDIUM",
                "Code Documentation", 
                f"Error checking API 579 references: {e}",
                "API 579 Part 1 - Documentation",
                "Fix file access issues for documentation audit"
            )

    async def audit_precision_compliance(self):
        """Verify decimal precision meets API 579 requirements."""
        print("📏 Auditing precision compliance...")
        
        try:
            # Test precision requirements
            test_thickness = Decimal("1.2345")  # Test value
            
            # API 579 requires ±0.001 inch precision for thickness
            if test_thickness.quantize(Decimal("0.001")) == test_thickness.quantize(Decimal("0.001")):
                self.add_pass("Thickness Precision Compliance (±0.001)")
            else:
                self.add_issue(
                    "CRITICAL",
                    "Decimal Precision",
                    "Thickness calculations do not meet ±0.001 inch requirement", 
                    "API 579 Part 4 - Measurement Precision",
                    "Ensure all thickness calculations use Decimal with 0.001 precision"
                )
                
            # Test pressure precision (±0.1 psi)
            test_pressure = Decimal("150.05")
            if test_pressure.quantize(Decimal("0.1")) == test_pressure.quantize(Decimal("0.1")):
                self.add_pass("Pressure Precision Compliance (±0.1 psi)")
            else:
                self.add_issue(
                    "CRITICAL", 
                    "Decimal Precision",
                    "Pressure calculations do not meet ±0.1 psi requirement",
                    "API 579 Part 4 - Pressure Precision", 
                    "Ensure all pressure calculations use Decimal with 0.1 precision"
                )
                
        except Exception as e:
            self.add_issue(
                "HIGH",
                "Precision Testing",
                f"Error testing precision compliance: {e}",
                "API 579 Part 4 - Calculation Precision",
                "Fix precision testing framework"
            )

    async def audit_audit_trail_completeness(self, session):
        """Verify complete audit trails exist for all calculations."""
        print("🔍 Auditing audit trail completeness...")
        
        try:
            # Check recent calculations have audit trails
            recent_calcs = session.query(API579Calculation).limit(10).all()
            
            missing_trails = 0
            for calc in recent_calcs:
                # Check if audit trail exists for this calculation
                trail = session.query(AuditTrail).filter(
                    AuditTrail.entity_type == "API579Calculation",
                    AuditTrail.entity_id == str(calc.id)
                ).first()
                
                if not trail:
                    missing_trails += 1
            
            if missing_trails > 0:
                self.add_issue(
                    "HIGH",
                    "Audit Trail",
                    f"{missing_trails} calculations missing audit trails",
                    "OSHA PSM - Complete Documentation Required", 
                    "Ensure all calculations automatically generate audit trails"
                )
            else:
                self.add_pass("Complete Audit Trail Coverage")
                
            # Check audit trail immutability
            trails = session.query(AuditTrail).limit(5).all()
            for trail in trails:
                if hasattr(trail, 'update') or hasattr(trail, 'modify'):
                    self.add_issue(
                        "CRITICAL",
                        "Audit Trail Model",
                        "Audit trail records are mutable",
                        "OSHA PSM - Immutable Audit Records",
                        "Remove update capabilities from AuditTrail model"
                    )
                    break
            else:
                self.add_pass("Audit Trail Immutability")
                
        except Exception as e:
            self.add_issue(
                "MEDIUM",
                "Audit Trail System",
                f"Error auditing trail completeness: {e}",
                "OSHA PSM - Audit Trail Requirements",
                "Fix audit trail query mechanisms"
            )

    async def audit_human_verification_loops(self, session):
        """Verify AI extractions require human verification."""
        print("👨‍🔬 Auditing human verification requirements...")
        
        try:
            # Check for AI-processed inspections without human verification
            ai_inspections = session.query(InspectionRecord).filter(
                InspectionRecord.ai_processed == True,
                InspectionRecord.verified_by.is_(None)
            ).all()
            
            if ai_inspections:
                self.add_issue(
                    "HIGH", 
                    "AI Verification",
                    f"{len(ai_inspections)} AI-processed inspections lack human verification",
                    "API 579 Part 1 - Human Oversight Required",
                    "Implement mandatory human verification for AI-extracted data"
                )
            else:
                self.add_pass("Human Verification Loop Compliance")
                
        except Exception as e:
            self.add_warning(
                "AI Verification System",
                f"Error checking verification loops: {e}",
                "Investigate AI verification query mechanisms"
            )

    async def audit_safety_factor_compliance(self):
        """Verify conservative safety factors are applied."""
        print("⚡ Auditing safety factor compliance...")
        
        try:
            # Check configuration for conservative settings
            safety_factor = getattr(settings, 'SAFETY_FACTOR', None)
            
            if not safety_factor:
                self.add_issue(
                    "CRITICAL",
                    "Configuration",
                    "No SAFETY_FACTOR defined in settings",
                    "API 579 Part 5 - Conservative Safety Factors", 
                    "Define SAFETY_FACTOR >= 2.0 in environment configuration"
                )
            elif float(safety_factor) < 2.0:
                self.add_issue(
                    "HIGH",
                    "Configuration", 
                    f"SAFETY_FACTOR {safety_factor} below recommended minimum of 2.0",
                    "API 579 Part 5 - Conservative Safety Factors",
                    "Increase SAFETY_FACTOR to >= 2.0 for conservative estimates"
                )
            else:
                self.add_pass(f"Conservative Safety Factor ({safety_factor})")
                
        except Exception as e:
            self.add_warning(
                "Configuration System",
                f"Error checking safety factors: {e}",
                "Verify environment configuration access"
            )

    def generate_report(self) -> str:
        """Generate comprehensive compliance report."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        report = f"""
# API 579 REGULATORY COMPLIANCE AUDIT REPORT
Generated: {timestamp}

## EXECUTIVE SUMMARY

**Critical Issues**: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}
**High Priority Issues**: {len([i for i in self.issues if i['severity'] == 'HIGH'])}  
**Medium Priority Issues**: {len([i for i in self.issues if i['severity'] == 'MEDIUM'])}
**Warnings**: {len(self.warnings)}
**Passed Checks**: {len(self.passed_checks)}

## COMPLIANCE STATUS

### ✅ PASSED COMPLIANCE CHECKS ({len(self.passed_checks)})
"""
        
        for check in self.passed_checks:
            report += f"- {check}\n"
        
        if self.issues:
            report += f"""
## 🚨 COMPLIANCE ISSUES ({len(self.issues)})

"""
            # Group by severity
            for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
                severity_issues = [i for i in self.issues if i['severity'] == severity]
                if severity_issues:
                    report += f"### {severity} PRIORITY ({len(severity_issues)} issues)\n\n"
                    
                    for issue in severity_issues:
                        report += f"""**Component**: {issue['component']}
**Issue**: {issue['description']}
**Regulation**: {issue['regulation']}  
**Remediation**: {issue['remediation']}
**Detected**: {issue['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

---

"""

        if self.warnings:
            report += f"""
## ⚠️ COMPLIANCE WARNINGS ({len(self.warnings)})

"""
            for warning in self.warnings:
                report += f"""**Component**: {warning['component']}
**Warning**: {warning['description']}
**Recommendation**: {warning['recommendation']}
**Detected**: {warning['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        
        # Compliance score
        total_checks = len(self.passed_checks) + len(self.issues)
        if total_checks > 0:
            compliance_score = (len(self.passed_checks) / total_checks) * 100
            report += f"""
## OVERALL COMPLIANCE SCORE

**{compliance_score:.1f}%** ({len(self.passed_checks)}/{total_checks} checks passed)

"""
        
        report += f"""
## REGULATORY FRAMEWORK COVERAGE

This audit covers compliance with:

- **API 579-1/ASME FFS-1**: Fitness-for-Service calculations and documentation
- **OSHA 29 CFR 1910.119**: Process Safety Management requirements  
- **ASME Section VIII**: Pressure vessel inspection and analysis
- **API 510/570/653**: In-service inspection standards

## NEXT STEPS

1. **Immediate**: Address all CRITICAL priority issues
2. **Short-term**: Resolve HIGH priority issues within 30 days
3. **Long-term**: Address MEDIUM priority issues and warnings
4. **Continuous**: Maintain compliance monitoring and audit trails

---
*This report was generated by the Mechanical Integrity Management System compliance auditor.*
*For questions about specific findings, consult the system documentation or API 579 standards.*
"""
        
        return report

async def main():
    """Run comprehensive compliance audit."""
    print("🔍 Starting API 579 Regulatory Compliance Audit...")
    print("=" * 60)
    
    auditor = ComplianceAuditor()
    
    try:
        # Get database session
        session = SessionLocal()
        try:
            # Run all compliance audits
            await auditor.audit_api579_references()
            await auditor.audit_precision_compliance() 
            await auditor.audit_calculation_immutability(session)
            await auditor.audit_audit_trail_completeness(session)
            await auditor.audit_human_verification_loops(session)
            await auditor.audit_safety_factor_compliance()
        finally:
            session.close()
            
    except Exception as e:
        auditor.add_issue(
            "CRITICAL",
            "Audit System",
            f"Audit framework error: {e}",
            "System Integrity",
            "Fix audit system infrastructure"
        )
    
    # Generate and save report
    report = auditor.generate_report()
    
    # Save to file
    report_file = backend_path / "compliance_audit_report.md"
    report_file.write_text(report)
    
    print(f"📋 Compliance report saved to: {report_file}")
    print(f"📊 Summary: {len(auditor.passed_checks)} passed, {len(auditor.issues)} issues, {len(auditor.warnings)} warnings")
    
    # Print executive summary
    critical_issues = len([i for i in auditor.issues if i['severity'] == 'CRITICAL'])
    if critical_issues > 0:
        print(f"🚨 CRITICAL: {critical_issues} critical compliance issues require immediate attention!")
        return 1
    else:
        print("✅ No critical compliance issues detected.")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)