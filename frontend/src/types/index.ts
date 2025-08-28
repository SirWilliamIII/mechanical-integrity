/**
 * Main Types Export for Mechanical Integrity Management System
 */

export * from './equipment'
export * from './inspection' 
export * from './api'

// Analysis types
export interface CorrosionAnalysisRequest {
  equipment_id: string
  inspection_data: any[]
  analysis_period?: string
}

export interface CorrosionAnalysisResponse {
  analysis_id: string
  corrosion_rate: string
  trend_direction: 'increasing' | 'decreasing' | 'stable'
  confidence_level: number
  recommendations: string[]
  created_at: string
}

export interface RemainingLifeProjection {
  equipmentId: string
  remainingLife: string
  confidenceLevel: number
  projectionDate: string
  assumptions: string[]
}

// RBI types  
export interface RBIIntervalRequest {
  equipment_id: string
  current_condition: string
  operating_context: string
  risk_factors: Record<string, any>
}

export interface RBIIntervalResponse {
  interval_years: number
  risk_level: string
  justification: string
  next_inspection_date: string
  recommendations: string[]
}

export interface RiskMatrix {
  matrix: any[]
  riskCategories: string[]
  equipmentCount: number
}

export interface RiskAssessment {
  equipmentId: string
  riskLevel: string
  probability: number
  consequence: number
  inspectionInterval: number
  lastAssessmentDate: string
}

// Calculation types
export interface API579CalculationRequest {
  inspection_id: string
  calculation_type: string
  input_parameters: Record<string, any>
}

export interface AuditTrail {
  calculation_id: string
  actions: AuditAction[]
  created_by: string
  created_at: string
}

export interface AuditAction {
  action: string
  timestamp: string
  user: string
  details: Record<string, any>
}

// Inspection status enum
export enum InspectionStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  VERIFIED = 'verified',
  REQUIRES_REVIEW = 'requires_review'
}

// Dashboard specific types
export interface DashboardStats {
  total_equipment: number
  inspections_due: number
  critical_findings: number
  compliance_rate: number
}

export interface AlertItem {
  id: string
  type: 'warning' | 'error' | 'info'
  title: string
  message: string
  equipment_id?: string
  created_at: string
  acknowledged: boolean
}

export interface ComplianceMetric {
  metric_name: string
  current_value: number
  target_value: number
  unit: string
  status: 'good' | 'warning' | 'critical'
  trend: 'up' | 'down' | 'stable'
}

// Equipment validation types
export interface EquipmentValidationRequest {
  design_pressure: string
  design_temperature: string  
  design_thickness: string
  material_specification: string
  equipment_type: 'pressure_vessel' | 'storage_tank' | 'piping' | 'heat_exchanger'
  service_description?: string
  corrosion_allowance?: string
}

export interface ValidationResult {
  valid: boolean
  field: string
  value: string
  reason?: string
  api_reference?: string
  action_required?: string
  warnings: string[]
}