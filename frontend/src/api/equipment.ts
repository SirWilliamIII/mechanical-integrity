/**
 * Equipment API Service for Mechanical Integrity Management System
 * API endpoints for equipment management
 */

import apiClient from './client'
import { mockApiResponses, useMockData, mockEquipment } from './mock'
import type {
  Equipment,
  EquipmentCreateRequest,
  EquipmentUpdateRequest,
  EquipmentSummary,
  PaginatedResponse,
  ApiQueryParams
} from '@/types'

export class EquipmentApi {
  private readonly basePath = '/equipment'

  /**
   * Get all equipment with optional filtering and pagination
   */
  async getEquipment(params?: ApiQueryParams): Promise<PaginatedResponse<Equipment>> {
    if (useMockData) {
      return mockApiResponses.getEquipment()
    }
    return apiClient.get(`${this.basePath}/`, params)
  }

  /**
   * Get equipment by ID
   */
  async getEquipmentById(id: string): Promise<Equipment> {
    if (useMockData) {
      return mockApiResponses.getEquipmentById(id)
    }
    return apiClient.get(`${this.basePath}/${id}`)
  }

  /**
   * Create new equipment
   */
  async createEquipment(data: EquipmentCreateRequest): Promise<Equipment> {
    return apiClient.post(`${this.basePath}/`, data)
  }

  /**
   * Update existing equipment
   */
  async updateEquipment(id: string, data: EquipmentUpdateRequest): Promise<Equipment> {
    return apiClient.put(`${this.basePath}/${id}`, data)
  }

  /**
   * Delete equipment
   */
  async deleteEquipment(id: string): Promise<void> {
    return apiClient.delete(`${this.basePath}/${id}`)
  }

  /**
   * Get equipment summary statistics
   */
  async getEquipmentSummary(): Promise<EquipmentSummary> {
    return apiClient.get(`${this.basePath}/summary`)
  }

  /**
   * Get equipment inspection history
   */
  async getEquipmentInspections(equipmentId: string, params?: ApiQueryParams) {
    return apiClient.get(`${this.basePath}/${equipmentId}/inspections`, params)
  }

  /**
   * Get equipment due for inspection
   */
  async getEquipmentDueForInspection(params?: ApiQueryParams): Promise<PaginatedResponse<Equipment>> {
    return apiClient.get(`${this.basePath}/due-for-inspection`, params)
  }

  /**
   * Get equipment by location
   */
  async getEquipmentByLocation(location: string, params?: ApiQueryParams): Promise<PaginatedResponse<Equipment>> {
    return apiClient.get(`${this.basePath}/by-location`, { ...params, location })
  }

  /**
   * Search equipment by tag number or description
   */
  async searchEquipment(query: string, params?: ApiQueryParams): Promise<PaginatedResponse<Equipment>> {
    return apiClient.get(`${this.basePath}/search`, { ...params, q: query })
  }

  /**
   * Export equipment data
   */
  async exportEquipment(format: 'csv' | 'xlsx' = 'csv'): Promise<Blob> {
    // Note: File download requires custom handling - this may need to be implemented differently
    const response = await apiClient.get(`${this.basePath}/export`, { format })
    return response as any
  }
}

// Export singleton instance
export const equipmentApi = new EquipmentApi()
export default equipmentApi