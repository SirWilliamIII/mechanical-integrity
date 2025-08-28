/**
 * Inspections API Service - Real backend integration
 * Handles inspection data and API 579 calculations
 */

import { apiClient } from './client'
import type {
  InspectionRecord,
  InspectionCreateRequest,
  InspectionUpdateRequest,
  API579Calculation,
  ThicknessReading,
  PaginatedResponse
} from '@/types'

export class InspectionsService {
  private basePath = '/api/v1/inspections'

  /**
   * Get paginated list of inspections
   */
  async getInspections(params?: {
    skip?: number
    limit?: number
    equipment_id?: string
    inspection_type?: string
    date_from?: string
    date_to?: string
  }): Promise<PaginatedResponse<InspectionRecord>> {
    const response = await apiClient.get<PaginatedResponse<InspectionRecord>>(
      this.basePath,
      params
    )
    return response
  }

  /**
   * Get inspection by ID
   */
  async getInspectionById(id: string): Promise<InspectionRecord> {
    const response = await apiClient.get<InspectionRecord>(`${this.basePath}/${id}`)
    return response
  }

  /**
   * Create new inspection
   */
  async createInspection(inspection: InspectionCreateRequest): Promise<InspectionRecord> {
    const response = await apiClient.post<InspectionRecord>(this.basePath, inspection)
    return response
  }

  /**
   * Update existing inspection
   */
  async updateInspection(id: string, inspection: InspectionUpdateRequest): Promise<InspectionRecord> {
    const response = await apiClient.put<InspectionRecord>(`${this.basePath}/${id}`, inspection)
    return response
  }

  /**
   * Delete inspection
   */
  async deleteInspection(id: string): Promise<void> {
    await apiClient.delete(`${this.basePath}/${id}`)
  }

  /**
   * Get inspections for specific equipment
   */
  async getInspectionsForEquipment(equipmentId: string): Promise<InspectionRecord[]> {
    const response = await apiClient.get<InspectionRecord[]>(`${this.basePath}/equipment/${equipmentId}`)
    return response
  }

  /**
   * Get thickness readings for inspection
   */
  async getThicknessReadings(inspectionId: string): Promise<ThicknessReading[]> {
    const response = await apiClient.get<ThicknessReading[]>(`${this.basePath}/${inspectionId}/thickness`)
    return response
  }

  /**
   * Add thickness reading to inspection
   */
  async addThicknessReading(inspectionId: string, reading: Omit<ThicknessReading, 'id' | 'created_at' | 'updated_at'>): Promise<ThicknessReading> {
    const response = await apiClient.post<ThicknessReading>(`${this.basePath}/${inspectionId}/thickness`, reading)
    return response
  }

  /**
   * Process inspection document with AI
   */
  async processInspectionDocument(inspectionId: string, file: File): Promise<{
    success: boolean
    extracted_data?: any
    confidence_score?: number
    warnings?: string[]
  }> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post<{
      success: boolean
      extracted_data?: any
      confidence_score?: number
      warnings?: string[]
    }>(`${this.basePath}/${inspectionId}/process-document`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response
  }
}

// Export singleton instance
export const inspectionsService = new InspectionsService()