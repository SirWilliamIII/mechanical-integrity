# API 579 COMPLIANCE REMEDIATION CHECKLIST
## Critical Safety System Fixes Required

**System**: Mechanical Integrity Management System  
**Compliance Target**: API 579-1/ASME FFS-1 Full Compliance  
**Risk Level**: EXTREME - Do not deploy until all CRITICAL items resolved

---

## IMMEDIATE CRITICAL FIXES (24-48 Hours)
**These must be completed before ANY production use**

### 🔴 DATABASE PRECISION FIXES

- [ ] **CRITICAL-001**: Migrate Equipment model Float columns to DECIMAL
  ```python
  # File: /models/equipment.py:63-74
  # Change from:
  design_pressure: Mapped[float]
  # To:
  design_pressure: Mapped[Decimal] = mapped_column(DECIMAL(10, 2))
  ```
  - [ ] Create Alembic migration script
  - [ ] Test data migration with sample data
  - [ ] Verify no precision loss during migration
  - [ ] Update all related queries and calculations

- [ ] **CRITICAL-002**: Fix JSON encoder precision loss in ALL API endpoints
  ```python
  # Files: /app/api/equipment.py, /app/api/inspections.py, /app/api/calculations.py
  # Change from:
  json_encoders = {Decimal: lambda v: float(v)}
  # To:
  json_encoders = {Decimal: lambda v: str(v)}
  ```
  - [ ] Update all Pydantic model configs
  - [ ] Test API responses preserve full precision
  - [ ] Update frontend to handle string decimals
  - [ ] Validate with API 579 test cases

### 🔴 CALCULATION SAFETY FIXES

- [ ] **CRITICAL-003**: Remove ALL hardcoded equipment dimensions
  ```python
  # File: /app/services/api579_service.py:346-356
  # Remove hardcoded radius values
  # Add equipment_dimensions table with actual values
  ```
  - [ ] Create equipment_dimensions table
  - [ ] Add dimension validation against equipment type
  - [ ] Implement dimension lookup in calculations
  - [ ] Add validation for physically impossible dimensions

- [ ] **CRITICAL-004**: Replace hardcoded material properties with ASME database
  ```python
  # File: /app/services/api579_service.py:362-388
  # Remove hardcoded allowable stress values
  # Implement ASME Section II-D Part D lookup
  ```
  - [ ] Create material_properties table
  - [ ] Import ASME Section II-D data
  - [ ] Implement temperature interpolation per B31.3
  - [ ] Add material-service compatibility validation

---

## HIGH PRIORITY FIXES (Within 1 Week)

### 🟠 AUDIT TRAIL COMPLIANCE

- [ ] **HIGH-001**: Implement audit trail immutability
  - [ ] Add database triggers to prevent UPDATE on audit tables
  - [ ] Implement append-only audit log table
  - [ ] Add cryptographic checksums to all calculations
  - [ ] Create chain-of-custody verification system

- [ ] **HIGH-002**: Fix failing dual-path verification tests
  ```python
  # File: /app/calculations/dual_path_calculator.py
  # Fix test: test_minimum_thickness_regression
  ```
  - [ ] Identify calculation discrepancy source
  - [ ] Align tolerance specifications
  - [ ] Validate against API 579 example problems
  - [ ] Document verification methodology

- [ ] **HIGH-003**: Add comprehensive input validation
  - [ ] Implement physical bounds checking (thickness < diameter)
  - [ ] Add temperature-pressure relationship validation
  - [ ] Validate corrosion rates against material/service
  - [ ] Add equipment-specific validation rules

### 🟠 DATA INTEGRITY

- [ ] **HIGH-004**: Implement calculation version control
  - [ ] Add calculation_version field to API579Calculation table
  - [ ] Track formula changes with version numbers
  - [ ] Enable reproduction of historical calculations
  - [ ] Add regression testing against previous versions

- [ ] **HIGH-005**: Add transaction isolation for safety calculations
  - [ ] Implement pessimistic locking for equipment updates
  - [ ] Add SERIALIZABLE isolation for calculation sequences
  - [ ] Prevent concurrent modification of inspection data
  - [ ] Add retry logic for lock conflicts

---

## MEDIUM PRIORITY FIXES (Within 1 Month)

### 🟡 REGULATORY COMPLIANCE FEATURES

- [ ] **MEDIUM-001**: Implement Level 2 and Level 3 API 579 assessments
  - [ ] Add Level 2 assessment methods per Part 5
  - [ ] Implement finite element analysis interface
  - [ ] Add stress concentration factor calculations
  - [ ] Create assessment level escalation logic

- [ ] **MEDIUM-002**: Add brittle fracture assessment (API 579 Part 3)
  - [ ] Implement minimum allowable temperature calculations
  - [ ] Add Charpy impact test data management
  - [ ] Create fracture toughness assessment
  - [ ] Add temperature exemption curves

- [ ] **MEDIUM-003**: Implement creep damage assessment (API 579 Part 10)
  - [ ] Add time-dependent material properties
  - [ ] Implement Larson-Miller parameter calculations
  - [ ] Add remaining creep life assessment
  - [ ] Create creep rate monitoring

### 🟡 SAFETY SYSTEMS

- [ ] **MEDIUM-004**: Add automatic safety actions
  - [ ] Auto-generate work orders for RSF < 0.9
  - [ ] Send alerts for remaining life < 2 years
  - [ ] Implement escalation workflow for critical findings
  - [ ] Add integration with emergency shutdown systems

- [ ] **MEDIUM-005**: Implement inspector qualification tracking
  - [ ] Add inspector_certifications table
  - [ ] Track SNT-TC-1A Level II/III certifications
  - [ ] Implement certification expiry alerts
  - [ ] Add qualification validation per inspection type

---

## DATABASE MIGRATION CHECKLIST

### 📊 Schema Changes Required

```sql
-- Equipment table modifications
ALTER TABLE equipment 
  ALTER COLUMN design_pressure TYPE DECIMAL(10,2),
  ALTER COLUMN design_temperature TYPE DECIMAL(7,2),
  ALTER COLUMN design_thickness TYPE DECIMAL(7,4),
  ALTER COLUMN corrosion_allowance TYPE DECIMAL(7,4);

-- Add equipment dimensions table
CREATE TABLE equipment_dimensions (
  id UUID PRIMARY KEY,
  equipment_id UUID REFERENCES equipment(id),
  internal_diameter DECIMAL(10,4) NOT NULL,
  external_diameter DECIMAL(10,4) NOT NULL,
  length DECIMAL(10,2),
  volume DECIMAL(12,2),
  validated_by VARCHAR(100),
  validated_at TIMESTAMP,
  CHECK (internal_diameter < external_diameter),
  CHECK (internal_diameter > 0)
);

-- Add material properties table
CREATE TABLE material_properties (
  id UUID PRIMARY KEY,
  material_spec VARCHAR(50) NOT NULL,
  temperature DECIMAL(7,2) NOT NULL,
  allowable_stress DECIMAL(10,2) NOT NULL,
  yield_strength DECIMAL(10,2),
  tensile_strength DECIMAL(10,2),
  elastic_modulus DECIMAL(12,2),
  source_document VARCHAR(100),
  UNIQUE(material_spec, temperature)
);

-- Add audit immutability trigger
CREATE OR REPLACE FUNCTION prevent_audit_update()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Audit records cannot be modified';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_immutability
BEFORE UPDATE ON api579_calculations
FOR EACH ROW EXECUTE FUNCTION prevent_audit_update();
```

---

## TESTING REQUIREMENTS

### 🧪 Required Test Coverage

- [ ] **TEST-001**: Decimal precision validation
  - [ ] Test all calculations maintain 6+ significant figures
  - [ ] Verify no float conversions in calculation path
  - [ ] Test JSON serialization preserves precision
  - [ ] Validate database storage and retrieval

- [ ] **TEST-002**: API 579 formula validation
  - [ ] Test against all Part 4 example problems
  - [ ] Validate Part 5 RSF calculations
  - [ ] Test MAWP calculations per ASME VIII
  - [ ] Verify remaining life calculations

- [ ] **TEST-003**: Safety boundary testing
  - [ ] Test RSF < 0.9 triggers alerts
  - [ ] Verify remaining life < 2 years flagging
  - [ ] Test pressure > MAWP prevention
  - [ ] Validate thickness < t_min handling

- [ ] **TEST-004**: Audit trail completeness
  - [ ] Test all calculations create audit records
  - [ ] Verify immutability enforcement
  - [ ] Test cryptographic hash verification
  - [ ] Validate chain of custody

---

## VALIDATION AGAINST API 579 STANDARDS

### 📋 Required Validations

- [ ] **VALIDATE-001**: Part 4 General Metal Loss
  - [ ] Equation 4.7 minimum thickness
  - [ ] Equation 4.8 MAWP calculation
  - [ ] Section 4.4.5 remaining life
  - [ ] Table 4.1 thickness limits

- [ ] **VALIDATE-002**: Part 5 Local Metal Loss  
  - [ ] Equation 5.5 RSF calculation
  - [ ] Section 5.4.3 assessment criteria
  - [ ] Figure 5.2 screening curves
  - [ ] Table 5.1 acceptance criteria

- [ ] **VALIDATE-003**: Inspection Intervals
  - [ ] API 510 pressure vessel intervals
  - [ ] API 570 piping intervals
  - [ ] API 653 tank intervals
  - [ ] Half-life rule implementation

---

## DEPLOYMENT READINESS CHECKLIST

### 🚀 Pre-Production Requirements

- [ ] All CRITICAL fixes completed and tested
- [ ] All HIGH priority fixes implemented
- [ ] 100% test coverage for safety-critical code
- [ ] Third-party safety audit completed
- [ ] Regulatory compliance documentation prepared
- [ ] Emergency response procedures defined
- [ ] Operator training completed
- [ ] Backup and recovery procedures tested
- [ ] Performance testing under load completed
- [ ] Security penetration testing passed

### 📝 Required Documentation

- [ ] API 579 compliance certification
- [ ] Safety case documentation
- [ ] Calculation methodology document
- [ ] Audit trail procedures
- [ ] Emergency response plan
- [ ] Operator training materials
- [ ] System architecture document
- [ ] Database schema documentation
- [ ] API documentation
- [ ] Testing evidence package

---

## SIGN-OFF REQUIREMENTS

**DO NOT DEPLOY** until all following parties have signed off:

- [ ] API 579 Certified Inspector
- [ ] Professional Engineer (PE)
- [ ] Safety Manager
- [ ] IT Security Officer
- [ ] Quality Assurance Lead
- [ ] Regulatory Compliance Officer
- [ ] Operations Manager
- [ ] Project Sponsor

---

**Last Updated**: 2025-08-26  
**Next Review**: Before any production deployment  
**Status**: **NOT READY FOR PRODUCTION** - Critical fixes required