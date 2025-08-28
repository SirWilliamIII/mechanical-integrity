/**
 * Equipment API Service - Real backend integration
 * Replaces mock data with actual FastAPI endpoints
 */

import { apiClient } from './client'
import type {
  Equipment,
  EquipmentCreateRequest,
  EquipmentUpdateRequest,
  PaginatedResponse,
  ApiResponse
} from '@/types'

export class EquipmentService {
  private basePath = '/api/v1/equipment'

  /**
   * Get paginated list of equipment
   */
  async getEquipment(params?: {
    skip?: number
    limit?: number
    search?: string
    equipment_type?: string
    criticality?: string
  }): Promise<PaginatedResponse<Equipment>> {
    const response = await apiClient.get<PaginatedResponse<Equipment>>(
      this.basePath,
      params
    )
    return response
  }

  /**
   * Get equipment by ID
   */
  async getEquipmentById(id: string): Promise<Equipment> {
    const response = await apiClient.get<Equipment>(`${this.basePath}/${id}`)
    return response
  }

  /**
   * Create new equipment
   */
  async createEquipment(equipment: EquipmentCreateRequest): Promise<Equipment> {
    const response = await apiClient.post<Equipment>(this.basePath, equipment)
    return response
  }

  /**
   * Update existing equipment
   */
  async updateEquipment(id: string, equipment: EquipmentUpdateRequest): Promise<Equipment> {
    const response = await apiClient.put<Equipment>(`${this.basePath}/${id}`, equipment)
    return response
  }

  /**
   * Delete equipment
   */
  async deleteEquipment(id: string): Promise<void> {
    await apiClient.delete(`${this.basePath}/${id}`)
  }

  /**
   * Get equipment by tag number
   */
  async getEquipmentByTag(tagNumber: string): Promise<Equipment> {
    const response = await apiClient.get<Equipment>(`${this.basePath}/by-tag/${tagNumber}`)
    return response
  }

  /**
   * Get equipment statistics
   */
  async getEquipmentStats(): Promise<{
    total: number
    by_type: Record<string, number>
    by_criticality: Record<string, number>
    overdue_inspections: number
  }> {
    const response = await apiClient.get<{
      total: number
      by_type: Record<string, number>
      by_criticality: Record<string, number>
      overdue_inspections: number
    }>(`${this.basePath}/stats`)
    return response
  }

  /**
   * Get equipment due for inspection
   */
  async getEquipmentDueForInspection(daysAhead: number = 30): Promise<Equipment[]> {
    const response = await apiClient.get<Equipment[]>(`${this.basePath}/due-for-inspection`, {
      days_ahead: daysAhead
    })
    return response
  }

  /**
   * Bulk create equipment
   */
  async bulkCreateEquipment(equipment: EquipmentCreateRequest[]): Promise<{
    created: Equipment[]
    failed: Array<{ index: number; tag_number: string; error: string }>
  }> {
    const response = await apiClient.post<{
      created: Equipment[]
      failed: Array<{ index: number; tag_number: string; error: string }>
    }>(`${this.basePath}/bulk`, { equipment })
    return response
  }
}

// Export singleton instance
export const equipmentService = new EquipmentService()