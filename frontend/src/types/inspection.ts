/**
 * Inspection Types for Mechanical Integrity Management System
 * TypeScript interfaces for inspection and measurement data
 */

export interface InspectionRecord {
  id: string
  equipment_id: string
  inspection_date: string
  inspection_type: InspectionType
  inspector_name: string
  inspector_certification?: string
  report_number: string
  
  // Calculated thickness fields
  min_thickness_found: number
  avg_thickness: number
  
  // Corrosion analysis
  corrosion_type?: CorrosionType
  corrosion_rate_calculated?: number
  confidence_level: number
  
  // Content
  findings?: string
  recommendations?: string
  follow_up_required: boolean
  
  // AI processing
  ai_processed: boolean
  ai_confidence_score?: number
  verified_by?: string
  verified_at?: string
  
  // Metadata
  created_at: string
  updated_at: string
  
  // Related data
  thickness_readings?: ThicknessReading[]
  calculations?: API579Calculation[]
}

export interface ThicknessReading {
  id: string
  inspection_record_id: string
  cml_number: string
  location_description: string
  thickness_measured: number
  design_thickness: number
  previous_thickness?: number
  grid_reference?: string
  surface_condition?: string
  metal_loss_total?: number
  metal_loss_period?: number
  created_at: string
}

export interface API579Calculation {
  id: string
  inspection_record_id: string
  calculation_type: string
  calculation_method: string
  performed_by: string
  
  // Input parameters
  input_parameters: Record<string, any>
  
  // Results
  minimum_required_thickness: number
  remaining_strength_factor: number
  maximum_allowable_pressure: number
  remaining_life_years?: number
  next_inspection_date?: string
  
  // Safety assessments
  fitness_for_service: FitnessForService
  risk_level: RiskLevel
  
  // Recommendations
  recommendations: string
  warnings?: string
  assumptions: Record<string, any>
  
  // Confidence
  confidence_score: number
  uncertainty_factors?: Record<string, any>
  
  created_at: string
}

export enum InspectionType {
  ULTRASONIC = 'ultrasonic',
  RADIOGRAPHIC = 'radiographic',
  MAGNETIC_PARTICLE = 'magnetic_particle',
  LIQUID_PENETRANT = 'liquid_penetrant',
  VISUAL = 'visual',
  EDDY_CURRENT = 'eddy_current'
}

export enum CorrosionType {
  GENERAL = 'general',
  PITTING = 'pitting',
  CREVICE = 'crevice',
  STRESS = 'stress',
  GALVANIC = 'galvanic',
  EROSION = 'erosion'
}

export enum FitnessForService {
  ACCEPTABLE = 'acceptable',
  CONDITIONAL = 'conditional',
  UNACCEPTABLE = 'unacceptable'
}

export enum RiskLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface InspectionCreateRequest {
  equipment_id: string
  inspection_date: string
  inspection_type: InspectionType
  inspector_name: string
  inspector_certification?: string
  report_number: string
  thickness_readings: ThicknessReadingCreateRequest[]
  corrosion_type?: CorrosionType
  findings?: string
  recommendations?: string
  follow_up_required?: boolean
}

export interface ThicknessReadingCreateRequest {
  cml_number: string
  location_description: string
  thickness_measured: number
  design_thickness: number
  previous_thickness?: number
  grid_reference?: string
  surface_condition?: string
}

export interface InspectionSummary {
  total_inspections: number
  recent_inspections: number
  pending_review: number
  critical_findings: number
  avg_confidence_level: number
}