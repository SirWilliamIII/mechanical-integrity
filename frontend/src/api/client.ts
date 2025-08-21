/**
 * HTTP Client Configuration for Mechanical Integrity Management System
 * Axios-based API client with interceptors and error handling
 */

import axios, { type AxiosInstance, type AxiosResponse, type AxiosError } from 'axios'
import type { ApiResponse, ApiError } from '@/types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        
        // Add request timestamp for debugging
        config.metadata = { startTime: Date.now() }
        
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        // Calculate request duration
        const duration = Date.now() - (response.config.metadata?.startTime || 0)
        
        // Log slow requests
        if (duration > 2000) {
          console.warn(`Slow API request: ${response.config.url} took ${duration}ms`)
        }
        
        return response
      },
      (error: AxiosError<ApiError>) => {
        return this.handleError(error)
      }
    )
  }

  private handleError(error: AxiosError<ApiError>): Promise<never> {
    const apiError: ApiError = {
      message: 'An unexpected error occurred',
      status: error.response?.status || 500,
      code: error.code,
    }

    if (error.response) {
      // Server responded with error status
      apiError.message = error.response.data?.message || `HTTP ${error.response.status}`
      apiError.status = error.response.status
      apiError.details = error.response.data?.details
    } else if (error.request) {
      // Request made but no response received
      apiError.message = 'Network error - please check your connection'
      apiError.status = 0
    }

    // Handle specific error cases
    if (apiError.status === 401) {
      // Unauthorized - clear auth and redirect to login
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    } else if (apiError.status === 403) {
      apiError.message = 'Access denied - insufficient permissions'
    } else if (apiError.status >= 500) {
      apiError.message = 'Server error - please try again later'
    }

    console.error('API Error:', apiError)
    return Promise.reject(apiError)
  }

  // HTTP Methods
  async get<T = any>(url: string, params?: Record<string, any>): Promise<T> {
    const response = await this.client.get<ApiResponse<T>>(url, { params })
    return response.data.data
  }

  async post<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<ApiResponse<T>>(url, data)
    return response.data.data
  }

  async put<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<ApiResponse<T>>(url, data)
    return response.data.data
  }

  async patch<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.patch<ApiResponse<T>>(url, data)
    return response.data.data
  }

  async delete<T = any>(url: string): Promise<T> {
    const response = await this.client.delete<ApiResponse<T>>(url)
    return response.data.data
  }

  // Upload file method
  async upload<T = any>(url: string, file: File, onProgress?: (progress: number) => void): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<ApiResponse<T>>(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })

    return response.data.data
  }
}

// Export singleton instance
export const apiClient = new ApiClient()
export default apiClient