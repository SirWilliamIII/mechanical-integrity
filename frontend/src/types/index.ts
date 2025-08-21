/**
 * Main Types Export for Mechanical Integrity Management System
 */

export * from './equipment'
export * from './inspection'
export * from './api'

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