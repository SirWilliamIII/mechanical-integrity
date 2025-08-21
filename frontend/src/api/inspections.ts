/**
 * Inspections API Service for Mechanical Integrity Management System
 * API endpoints for inspection and calculation management
 */

import apiClient from './client'
import { mockApiResponses, useMockData } from './mock'
import type {
  InspectionRecord,
  InspectionCreateRequest,
  API579Calculation,
  ThicknessReading,
  InspectionSummary,
  PaginatedResponse,
  ApiQueryParams
} from '@/types'

export class InspectionsApi {
  private readonly basePath = '/inspections'

  /**
   * Get all inspections with optional filtering and pagination
   */
  async getInspections(params?: ApiQueryParams): Promise<PaginatedResponse<InspectionRecord>> {
    if (useMockData) {
      return mockApiResponses.getInspections()
    }
    return apiClient.get(`${this.basePath}/`, params)
  }

  /**
   * Get inspection by ID
   */
  async getInspectionById(id: string): Promise<InspectionRecord> {
    return apiClient.get(`${this.basePath}/${id}`)
  }

  /**
   * Create new inspection
   */
  async createInspection(data: InspectionCreateRequest): Promise<InspectionRecord> {
    if (useMockData) {
      return mockApiResponses.createInspection(data)
    }
    return apiClient.post(`${this.basePath}/`, data)
  }

  /**
   * Add thickness readings to existing inspection
   */
  async addThicknessReadings(
    inspectionId: string, 
    readings: ThicknessReading[], 
    operatorNotes?: string
  ): Promise<{ message: string; new_readings_count: number }> {
    return apiClient.post(`${this.basePath}/${inspectionId}/thickness-readings`, {
      readings,
      operator_notes: operatorNotes
    })
  }

  /**
   * Get API 579 calculations for inspection
   */
  async getInspectionCalculations(inspectionId: string): Promise<API579Calculation[]> {
    return apiClient.get(`${this.basePath}/${inspectionId}/calculations`)
  }

  /**
   * Get inspection summary statistics
   */
  async getInspectionSummary(): Promise<InspectionSummary> {
    return apiClient.get(`${this.basePath}/summary`)
  }

  /**
   * Get recent inspections
   */
  async getRecentInspections(limit: number = 10): Promise<InspectionRecord[]> {
    return apiClient.get(`${this.basePath}/recent`, { limit })
  }

  /**
   * Get inspections pending review
   */
  async getInspectionsPendingReview(params?: ApiQueryParams): Promise<PaginatedResponse<InspectionRecord>> {
    return apiClient.get(`${this.basePath}/pending-review`, params)
  }

  /**
   * Verify inspection (mark as reviewed)
   */
  async verifyInspection(inspectionId: string, verifiedBy: string): Promise<InspectionRecord> {
    return apiClient.patch(`${this.basePath}/${inspectionId}/verify`, {
      verified_by: verifiedBy
    })
  }

  /**
   * Upload inspection document
   */
  async uploadInspectionDocument(
    inspectionId: string, 
    file: File, 
    onProgress?: (progress: number) => void
  ): Promise<{ message: string; document_id: string }> {
    return apiClient.upload(`${this.basePath}/${inspectionId}/documents`, file, onProgress)
  }

  /**
   * Get critical findings across all inspections
   */
  async getCriticalFindings(params?: ApiQueryParams): Promise<PaginatedResponse<InspectionRecord>> {
    return apiClient.get(`${this.basePath}/critical-findings`, params)
  }

  /**
   * Export inspection data
   */
  async exportInspections(
    format: 'csv' | 'xlsx' | 'pdf' = 'csv',
    equipmentId?: string,
    dateFrom?: string,
    dateTo?: string
  ): Promise<Blob> {
    const response = await apiClient.get(`${this.basePath}/export`, {
      format,
      equipment_id: equipmentId,
      date_from: dateFrom,
      date_to: dateTo
    }, {
      responseType: 'blob'
    } as any)
    return response
  }

  /**
   * Search inspections
   */
  async searchInspections(query: string, params?: ApiQueryParams): Promise<PaginatedResponse<InspectionRecord>> {
    return apiClient.get(`${this.basePath}/search`, { ...params, q: query })
  }
}

// Export singleton instance
export const inspectionsApi = new InspectionsApi()
export default inspectionsApi