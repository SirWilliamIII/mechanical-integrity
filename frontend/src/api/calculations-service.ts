/**
 * API 579 Calculations Service - Real backend integration
 * Handles safety-critical fitness-for-service calculations
 */

import { apiClient } from './client'
import type {
  API579Calculation,
  API579CalculationRequest,
  API579Results,
  RemainingLifeRequest,
  RSFCalculationRequest,
  MAWPCalculationRequest
} from '@/types'

export class CalculationsService {
  private basePath = '/api/v1/calculations'

  /**
   * Perform complete API 579 assessment
   */
  async performAPI579Assessment(inspectionId: string): Promise<API579Calculation> {
    const response = await apiClient.post<API579Calculation>(
      `${this.basePath}/api579/${inspectionId}`,
      {}
    )
    return response
  }

  /**
   * Get calculation results by inspection ID
   */
  async getCalculationsByInspection(inspectionId: string): Promise<API579Calculation[]> {
    const response = await apiClient.get<API579Calculation[]>(
      `${this.basePath}/inspection/${inspectionId}`
    )
    return response
  }

  /**
   * Get calculation by ID
   */
  async getCalculationById(calculationId: string): Promise<API579Calculation> {
    const response = await apiClient.get<API579Calculation>(
      `${this.basePath}/${calculationId}`
    )
    return response
  }

  /**
   * Calculate Remaining Strength Factor (RSF)
   */
  async calculateRSF(request: RSFCalculationRequest): Promise<{
    rsf: number
    status: 'FIT' | 'CONDITIONAL' | 'UNFIT'
    warnings?: string[]
    recommendations?: string
  }> {
    const response = await apiClient.post<{
      rsf: number
      status: 'FIT' | 'CONDITIONAL' | 'UNFIT'
      warnings?: string[]
      recommendations?: string
    }>(`${this.basePath}/rsf`, request)
    return response
  }

  /**
   * Calculate Maximum Allowable Working Pressure (MAWP)
   */
  async calculateMAWP(request: MAWPCalculationRequest): Promise<{
    mawp: number
    margin_psi: number
    warnings?: string[]
  }> {
    const response = await apiClient.post<{
      mawp: number
      margin_psi: number
      warnings?: string[]
    }>(`${this.basePath}/mawp`, request)
    return response
  }

  /**
   * Calculate remaining life
   */
  async calculateRemainingLife(request: RemainingLifeRequest): Promise<{
    remaining_life_years: number | null
    corrosion_rate: number
    confidence_level: number
    warnings?: string[]
  }> {
    const response = await apiClient.post<{
      remaining_life_years: number | null
      corrosion_rate: number
      confidence_level: number
      warnings?: string[]
    }>(`${this.basePath}/remaining-life`, request)
    return response
  }

  /**
   * Get calculation history for equipment
   */
  async getCalculationHistory(equipmentId: string): Promise<API579Calculation[]> {
    const response = await apiClient.get<API579Calculation[]>(
      `${this.basePath}/equipment/${equipmentId}/history`
    )
    return response
  }

  /**
   * Verify calculation using dual-path method
   */
  async verifyCalculation(calculationId: string): Promise<{
    primary_result: number
    secondary_result: number
    difference: number
    verification_passed: boolean
    tolerance: number
  }> {
    const response = await apiClient.post<{
      primary_result: number
      secondary_result: number
      difference: number
      verification_passed: boolean
      tolerance: number
    }>(`${this.basePath}/${calculationId}/verify`, {})
    return response
  }

  /**
   * Get calculation statistics
   */
  async getCalculationStats(): Promise<{
    total_calculations: number
    calculations_by_type: Record<string, number>
    avg_processing_time_ms: number
    rsf_distribution: {
      fit: number
      conditional: number
      unfit: number
    }
  }> {
    const response = await apiClient.get<{
      total_calculations: number
      calculations_by_type: Record<string, number>
      avg_processing_time_ms: number
      rsf_distribution: {
        fit: number
        conditional: number
        unfit: number
      }
    }>(`${this.basePath}/stats`)
    return response
  }

  /**
   * Export calculation report
   */
  async exportCalculationReport(calculationId: string, format: 'pdf' | 'excel'): Promise<Blob> {
    const response = await apiClient.get(
      `${this.basePath}/${calculationId}/export`,
      { format },
      { responseType: 'blob' }
    )
    return response
  }
}

// Export singleton instance
export const calculationsService = new CalculationsService()