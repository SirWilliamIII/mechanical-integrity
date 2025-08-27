/**
 * Calculations API Service for Mechanical Integrity Management System
 * API endpoints for API 579 calculation management
 */

import apiClient from './client'
import type {
  API579Calculation,
  API579CalculationRequest,
  AuditTrail,
  ApiQueryParams
} from '@/types'

export class CalculationsApi {
  private readonly basePath = '/calculations'

  /**
   * Perform API 579 fitness-for-service calculation
   * POST /api/v1/calculations/api579
   */
  async calculateAPI579(request: API579CalculationRequest): Promise<API579Calculation> {
    return apiClient.post(`${this.basePath}/api579`, request)
  }

  /**
   * Get calculation audit trail
   * GET /api/v1/calculations/{calculation_id}/audit
   */
  async getCalculationAudit(calculationId: string): Promise<AuditTrail> {
    return apiClient.get(`${this.basePath}/${calculationId}/audit`)
  }

  /**
   * Get calculation by ID
   * This would connect to a future calculation retrieval endpoint
   */
  async getCalculationById(calculationId: string): Promise<API579Calculation> {
    // For now, this endpoint is not implemented in backend
    // TODO: Connect to /api/v1/calculations/{calculation_id} when available
    throw new Error('Get calculation by ID not yet implemented in backend')
  }

  /**
   * Get calculations for inspection
   * This uses the inspections API to get calculation results
   */
  async getCalculationsForInspection(inspectionId: string): Promise<API579Calculation[]> {
    // This uses the existing inspections endpoint for calculations
    return apiClient.get(`/inspections/${inspectionId}/calculations`)
  }
}

export const calculationsApi = new CalculationsApi()
export default calculationsApi