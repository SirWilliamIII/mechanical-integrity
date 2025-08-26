-- API 579 COMPLIANCE: CRITICAL DATABASE MIGRATION
-- WARNING: This migration is REQUIRED for safety-critical compliance
-- DO NOT modify without API 579 engineer approval
-- 
-- Purpose: Fix precision loss in safety-critical calculations
-- Risk: Current Float types cause calculation errors that could lead to equipment failure
-- Solution: Migrate all measurement columns to DECIMAL with appropriate precision

-- ============================================================================
-- SAFETY NOTICE: 
-- This migration MUST be tested in a non-production environment first
-- Backup all data before execution
-- Verify no precision loss after migration
-- ============================================================================

BEGIN;

-- Step 1: Create backup tables for safety
CREATE TABLE equipment_backup AS SELECT * FROM equipment;
CREATE TABLE inspection_records_backup AS SELECT * FROM inspection_records;
CREATE TABLE thickness_readings_backup AS SELECT * FROM thickness_readings;
CREATE TABLE api579_calculations_backup AS SELECT * FROM api579_calculations;

-- ============================================================================
-- CRITICAL FIX #1: Equipment Table Float to DECIMAL Migration
-- API 579 Reference: Part 4, Section 4.3 - Precision Requirements
-- ============================================================================

-- Add new DECIMAL columns with proper precision
ALTER TABLE equipment 
  ADD COLUMN design_pressure_decimal DECIMAL(10,2),
  ADD COLUMN design_temperature_decimal DECIMAL(7,2),
  ADD COLUMN design_thickness_decimal DECIMAL(7,4),
  ADD COLUMN corrosion_allowance_decimal DECIMAL(7,4);

-- Copy data with explicit casting to preserve precision
UPDATE equipment 
SET 
  design_pressure_decimal = CAST(design_pressure AS DECIMAL(10,2)),
  design_temperature_decimal = CAST(design_temperature AS DECIMAL(7,2)),
  design_thickness_decimal = CAST(design_thickness AS DECIMAL(7,4)),
  corrosion_allowance_decimal = CAST(corrosion_allowance AS DECIMAL(7,4));

-- Verify no NULL values after conversion
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM equipment 
    WHERE design_pressure_decimal IS NULL 
       OR design_temperature_decimal IS NULL 
       OR design_thickness_decimal IS NULL
  ) THEN
    RAISE EXCEPTION 'NULL values detected after conversion - ROLLBACK REQUIRED';
  END IF;
END $$;

-- Drop old columns and rename new ones
ALTER TABLE equipment 
  DROP COLUMN design_pressure,
  DROP COLUMN design_temperature,
  DROP COLUMN design_thickness,
  DROP COLUMN corrosion_allowance;

ALTER TABLE equipment 
  RENAME COLUMN design_pressure_decimal TO design_pressure;
ALTER TABLE equipment 
  RENAME COLUMN design_temperature_decimal TO design_temperature;
ALTER TABLE equipment 
  RENAME COLUMN design_thickness_decimal TO design_thickness;
ALTER TABLE equipment 
  RENAME COLUMN corrosion_allowance_decimal TO corrosion_allowance;

-- Add NOT NULL constraints for safety-critical fields
ALTER TABLE equipment 
  ALTER COLUMN design_pressure SET NOT NULL,
  ALTER COLUMN design_temperature SET NOT NULL,
  ALTER COLUMN design_thickness SET NOT NULL;

-- Add CHECK constraints for valid ranges per API 579
ALTER TABLE equipment 
  ADD CONSTRAINT chk_design_pressure CHECK (design_pressure >= -14.7 AND design_pressure <= 10000),
  ADD CONSTRAINT chk_design_temperature CHECK (design_temperature >= -320 AND design_temperature <= 1500),
  ADD CONSTRAINT chk_design_thickness CHECK (design_thickness > 0 AND design_thickness <= 12),
  ADD CONSTRAINT chk_corrosion_allowance CHECK (corrosion_allowance >= 0 AND corrosion_allowance <= 1);

-- ============================================================================
-- CRITICAL FIX #2: Create Equipment Dimensions Table
-- API 579 Reference: Part 4, Section 4.3.2 - Geometry Requirements
-- ============================================================================

CREATE TABLE equipment_dimensions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
  internal_diameter DECIMAL(10,4) NOT NULL,
  external_diameter DECIMAL(10,4) NOT NULL,
  straight_length DECIMAL(10,2),
  volume DECIMAL(12,2),
  surface_area DECIMAL(12,2),
  nominal_pipe_size VARCHAR(10),
  schedule VARCHAR(10),
  class_rating VARCHAR(10),
  orientation VARCHAR(20) CHECK (orientation IN ('horizontal', 'vertical', 'inclined')),
  elevation_bottom DECIMAL(8,2),
  elevation_top DECIMAL(8,2),
  insulation_thickness DECIMAL(5,3),
  cladding_thickness DECIMAL(5,3),
  design_code VARCHAR(50),
  design_year INTEGER,
  validated_by VARCHAR(100) NOT NULL,
  validated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  validation_method VARCHAR(100),
  drawing_reference VARCHAR(100),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  
  -- Critical safety constraints
  CONSTRAINT chk_diameter_relationship CHECK (internal_diameter < external_diameter),
  CONSTRAINT chk_positive_dimensions CHECK (
    internal_diameter > 0 AND 
    external_diameter > 0 AND 
    (straight_length IS NULL OR straight_length > 0) AND
    (volume IS NULL OR volume > 0)
  ),
  CONSTRAINT chk_wall_thickness CHECK ((external_diameter - internal_diameter) / 2 >= 0.0625), -- Min 1/16"
  CONSTRAINT chk_diameter_ratio CHECK (internal_diameter / external_diameter >= 0.5), -- Prevent impossible geometries
  UNIQUE(equipment_id) -- One dimension record per equipment
);

-- Create index for performance
CREATE INDEX idx_equipment_dimensions_equipment_id ON equipment_dimensions(equipment_id);

-- Add comments for documentation
COMMENT ON TABLE equipment_dimensions IS 'Critical equipment geometry data per API 579 Part 4 requirements';
COMMENT ON COLUMN equipment_dimensions.internal_diameter IS 'Internal diameter in inches - critical for stress calculations';
COMMENT ON COLUMN equipment_dimensions.external_diameter IS 'External diameter in inches - used for thickness calculations';
COMMENT ON COLUMN equipment_dimensions.validated_by IS 'PE or API 510/570/653 inspector who validated dimensions';

-- ============================================================================
-- CRITICAL FIX #3: Create Material Properties Table
-- API 579 Reference: Annex F - Material Properties
-- ASME Section II Part D - Allowable Stress Values
-- ============================================================================

CREATE TABLE material_properties (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  material_spec VARCHAR(50) NOT NULL,
  material_grade VARCHAR(20),
  product_form VARCHAR(30),
  temperature DECIMAL(7,2) NOT NULL,
  allowable_stress DECIMAL(10,2) NOT NULL,
  yield_strength DECIMAL(10,2),
  tensile_strength DECIMAL(10,2),
  elastic_modulus DECIMAL(12,2),
  poisson_ratio DECIMAL(4,3),
  thermal_expansion DECIMAL(8,6),
  thermal_conductivity DECIMAL(8,3),
  specific_heat DECIMAL(8,3),
  density DECIMAL(8,3),
  creep_rupture_strength DECIMAL(10,2),
  fatigue_curve VARCHAR(10),
  source_document VARCHAR(100) NOT NULL,
  source_table VARCHAR(50),
  source_year INTEGER,
  notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  
  -- Ensure unique material-temperature combinations
  UNIQUE(material_spec, material_grade, temperature),
  
  -- Data validation constraints
  CONSTRAINT chk_positive_properties CHECK (
    allowable_stress > 0 AND
    (yield_strength IS NULL OR yield_strength > 0) AND
    (tensile_strength IS NULL OR tensile_strength > 0) AND
    (elastic_modulus IS NULL OR elastic_modulus > 0)
  ),
  CONSTRAINT chk_temperature_range CHECK (temperature >= -320 AND temperature <= 1500),
  CONSTRAINT chk_strength_relationship CHECK (
    yield_strength IS NULL OR 
    tensile_strength IS NULL OR 
    yield_strength <= tensile_strength
  )
);

-- Create indexes for performance
CREATE INDEX idx_material_properties_lookup ON material_properties(material_spec, temperature);
CREATE INDEX idx_material_properties_spec ON material_properties(material_spec);

-- Insert critical carbon steel data (SA-516-70) per ASME Section II-D
INSERT INTO material_properties (
  material_spec, material_grade, temperature, allowable_stress, 
  yield_strength, tensile_strength, elastic_modulus, source_document
) VALUES 
  ('SA-516', '70', -20, 20000, 38000, 70000, 29500000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 100, 20000, 38000, 70000, 29300000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 200, 20000, 36600, 70000, 28800000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 300, 20000, 35500, 70000, 28300000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 400, 20000, 35100, 70000, 27700000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 500, 20000, 34300, 70000, 27100000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 600, 20000, 32500, 70000, 26500000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 650, 20000, 30900, 68600, 26100000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 700, 18900, 28200, 65400, 25700000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 750, 17300, 24900, 60700, 25300000, 'ASME Section II-D Table 1A'),
  ('SA-516', '70', 800, 15500, 21500, 54500, 24800000, 'ASME Section II-D Table 1A');

-- ============================================================================
-- CRITICAL FIX #4: Add Audit Trail Immutability
-- API 579 Reference: Part 2, Section 2.5.4 - Documentation Requirements
-- ============================================================================

-- Create audit log table for immutable records
CREATE TABLE calculation_audit_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  calculation_id UUID NOT NULL,
  calculation_type VARCHAR(50) NOT NULL,
  performed_at TIMESTAMP WITH TIME ZONE NOT NULL,
  performed_by VARCHAR(100) NOT NULL,
  input_parameters JSONB NOT NULL,
  calculation_results JSONB NOT NULL,
  api_reference VARCHAR(100) NOT NULL,
  calculation_version VARCHAR(20) NOT NULL,
  software_version VARCHAR(20) NOT NULL,
  data_hash VARCHAR(64) NOT NULL, -- SHA-256 hash
  previous_hash VARCHAR(64), -- For blockchain-style chaining
  verified BOOLEAN DEFAULT FALSE,
  verified_by VARCHAR(100),
  verified_at TIMESTAMP WITH TIME ZONE,
  
  -- Prevent any modifications
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create immutability trigger function
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    -- Allow only verification updates
    IF OLD.verified = TRUE OR 
       (NEW.calculation_id != OLD.calculation_id OR
        NEW.calculation_type != OLD.calculation_type OR
        NEW.performed_at != OLD.performed_at OR
        NEW.performed_by != OLD.performed_by OR
        NEW.input_parameters != OLD.input_parameters OR
        NEW.calculation_results != OLD.calculation_results OR
        NEW.data_hash != OLD.data_hash) THEN
      RAISE EXCEPTION 'Audit records cannot be modified per API 579 compliance';
    END IF;
  ELSIF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'Audit records cannot be deleted per API 579 compliance';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply immutability trigger
CREATE TRIGGER audit_log_immutability
BEFORE UPDATE OR DELETE ON calculation_audit_log
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- Also protect main calculation table
CREATE TRIGGER api579_calculation_immutability
BEFORE DELETE ON api579_calculations
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- ============================================================================
-- CRITICAL FIX #5: Add Data Integrity Verification
-- ============================================================================

-- Function to calculate SHA-256 hash for data integrity
CREATE OR REPLACE FUNCTION calculate_data_hash(data JSONB)
RETURNS VARCHAR AS $$
DECLARE
  data_string TEXT;
BEGIN
  -- Convert JSONB to deterministic string
  data_string := jsonb_pretty(data);
  -- Return SHA-256 hash
  RETURN encode(digest(data_string, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Add hash verification function
CREATE OR REPLACE FUNCTION verify_calculation_integrity(calc_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
  stored_hash VARCHAR;
  calculated_hash VARCHAR;
  audit_record RECORD;
BEGIN
  SELECT * INTO audit_record 
  FROM calculation_audit_log 
  WHERE calculation_id = calc_id;
  
  IF NOT FOUND THEN
    RETURN FALSE;
  END IF;
  
  -- Combine input and output for hash
  calculated_hash := calculate_data_hash(
    jsonb_build_object(
      'input', audit_record.input_parameters,
      'output', audit_record.calculation_results
    )
  );
  
  RETURN calculated_hash = audit_record.data_hash;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VALIDATION QUERIES - Run these to verify migration success
-- ============================================================================

-- Check for precision issues
SELECT 
  'Equipment' as table_name,
  COUNT(*) as total_records,
  COUNT(CASE WHEN design_pressure::TEXT LIKE '%.%' THEN 1 END) as decimal_values,
  MAX(LENGTH(SPLIT_PART(design_pressure::TEXT, '.', 2))) as max_decimal_places
FROM equipment;

-- Verify constraints are working
-- This should fail (negative thickness)
-- INSERT INTO equipment_dimensions (equipment_id, internal_diameter, external_diameter, validated_by)
-- VALUES (gen_random_uuid(), 24, 23, 'Test'); -- Should fail

-- Verify material properties loaded correctly
SELECT 
  material_spec, 
  temperature, 
  allowable_stress,
  yield_strength
FROM material_properties 
WHERE material_spec = 'SA-516'
ORDER BY temperature;

-- ============================================================================
-- ROLLBACK PLAN (if needed)
-- ============================================================================
-- If any issues are encountered, run:
-- ROLLBACK;
-- Then restore from backups:
-- DROP TABLE IF EXISTS equipment CASCADE;
-- ALTER TABLE equipment_backup RENAME TO equipment;
-- Repeat for other tables

-- ============================================================================
-- COMMIT TRANSACTION
-- ============================================================================

-- Final safety check
DO $$
DECLARE
  equipment_count INTEGER;
  backup_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO equipment_count FROM equipment;
  SELECT COUNT(*) INTO backup_count FROM equipment_backup;
  
  IF equipment_count != backup_count THEN
    RAISE EXCEPTION 'Record count mismatch - ROLLBACK REQUIRED';
  END IF;
  
  RAISE NOTICE 'Migration completed successfully. % records migrated.', equipment_count;
END $$;

COMMIT;

-- ============================================================================
-- POST-MIGRATION VALIDATION
-- ============================================================================

-- Generate migration report
SELECT 
  'MIGRATION COMPLETE' as status,
  NOW() as completed_at,
  (SELECT COUNT(*) FROM equipment) as equipment_records,
  (SELECT COUNT(*) FROM material_properties) as material_records,
  (SELECT COUNT(*) FROM equipment_dimensions) as dimension_records,
  'Run post-migration tests immediately' as next_action;