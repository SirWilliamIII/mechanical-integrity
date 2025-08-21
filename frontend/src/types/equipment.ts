/**
 * Equipment Types for Mechanical Integrity Management System
 * TypeScript interfaces for equipment data structures
 */

export interface Equipment {
  id: string
  tag_number: string
  equipment_type: EquipmentType
  description: string
  design_pressure: number
  design_temperature: number
  design_thickness: number
  material_specification: string
  installation_date: string
  status: EquipmentStatus
  last_inspection_date?: string
  next_inspection_due?: string
  location: string
  service_fluid: string
  corrosion_allowance: number
  created_at: string
  updated_at: string
}

export enum EquipmentType {
  PRESSURE_VESSEL = 'pressure_vessel',
  STORAGE_TANK = 'storage_tank',
  HEAT_EXCHANGER = 'heat_exchanger',
  PIPING_SYSTEM = 'piping_system',
  REACTOR = 'reactor'
}

export enum EquipmentStatus {
  IN_SERVICE = 'in_service',
  OUT_OF_SERVICE = 'out_of_service',
  MAINTENANCE = 'maintenance',
  INSPECTION_DUE = 'inspection_due',
  DECOMMISSIONED = 'decommissioned'
}

export interface EquipmentSummary {
  total_count: number
  by_status: Record<EquipmentStatus, number>
  by_type: Record<EquipmentType, number>
  inspection_due_count: number
  overdue_count: number
}

export interface EquipmentCreateRequest {
  tag_number: string
  equipment_type: EquipmentType
  description: string
  design_pressure: number
  design_temperature: number
  design_thickness: number
  material_specification: string
  installation_date: string
  location: string
  service_fluid: string
  corrosion_allowance: number
}

export interface EquipmentUpdateRequest extends Partial<EquipmentCreateRequest> {
  status?: EquipmentStatus
}