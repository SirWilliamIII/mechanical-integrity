/**
 * Form Validation Composable for Safety-Critical Data Entry
 * Provides comprehensive validation for mechanical integrity forms
 */

import { ref, computed, type Ref } from 'vue'

export interface ValidationRule {
  test: (value: any) => boolean
  message: string
}

export interface FieldValidation {
  rules: ValidationRule[]
  isDirty: boolean
  isTouched: boolean
}

export interface FormValidation {
  [key: string]: FieldValidation
}

export function useFormValidation() {
  const validations: Ref<FormValidation> = ref({})
  const isSubmitting = ref(false)

  // Common validation rules for safety-critical data
  const rules = {
    required: (message = 'This field is required'): ValidationRule => ({
      test: (value: any) => value !== null && value !== undefined && value !== '',
      message
    }),

    minLength: (min: number, message?: string): ValidationRule => ({
      test: (value: string) => !value || value.length >= min,
      message: message || `Minimum ${min} characters required`
    }),

    maxLength: (max: number, message?: string): ValidationRule => ({
      test: (value: string) => !value || value.length <= max,
      message: message || `Maximum ${max} characters allowed`
    }),

    pattern: (regex: RegExp, message: string): ValidationRule => ({
      test: (value: string) => !value || regex.test(value),
      message
    }),

    email: (): ValidationRule => ({
      test: (value: string) => !value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
      message: 'Invalid email format'
    }),

    // Safety-critical numeric validations
    positiveNumber: (message = 'Value must be positive'): ValidationRule => ({
      test: (value: number) => value === null || value === undefined || value > 0,
      message
    }),

    numberRange: (min: number, max: number, message?: string): ValidationRule => ({
      test: (value: number) => value === null || value === undefined || (value >= min && value <= max),
      message: message || `Value must be between ${min} and ${max}`
    }),

    // Thickness measurement validation (±0.001 precision)
    thicknessPrecision: (): ValidationRule => ({
      test: (value: number) => {
        if (value === null || value === undefined) return true
        const str = value.toString()
        const decimalIndex = str.indexOf('.')
        if (decimalIndex === -1) return true
        return str.length - decimalIndex - 1 <= 3
      },
      message: 'Thickness precision cannot exceed ±0.001 inches'
    }),

    thicknessRange: (): ValidationRule => ({
      test: (value: number) => value === null || value === undefined || (value >= 0.001 && value <= 10.000),
      message: 'Thickness must be between 0.001 and 10.000 inches'
    }),

    // Pressure validation for safety
    pressureRange: (): ValidationRule => ({
      test: (value: number) => value === null || value === undefined || (value >= 0 && value <= 10000),
      message: 'Pressure must be between 0 and 10,000 psi'
    }),

    // Temperature validation
    temperatureRange: (): ValidationRule => ({
      test: (value: number) => value === null || value === undefined || (value >= -459 && value <= 2000),
      message: 'Temperature must be between -459°F and 2000°F'
    }),

    // Equipment tag validation
    equipmentTag: (): ValidationRule => ({
      test: (value: string) => !value || /^[A-Z0-9\-]{3,20}$/.test(value),
      message: 'Equipment tag must be 3-20 characters, uppercase letters, numbers, and hyphens only'
    }),

    // CML number validation
    cmlNumber: (): ValidationRule => ({
      test: (value: string) => !value || /^[A-Z0-9\-]{1,20}$/.test(value),
      message: 'CML number must be 1-20 characters, uppercase letters, numbers, and hyphens only'
    }),

    // Date validation
    pastDate: (message = 'Date cannot be in the future'): ValidationRule => ({
      test: (value: string) => !value || new Date(value) <= new Date(),
      message
    }),

    recentDate: (maxYearsAgo = 10): ValidationRule => ({
      test: (value: string) => {
        if (!value) return true
        const date = new Date(value)
        const maxPastDate = new Date()
        maxPastDate.setFullYear(maxPastDate.getFullYear() - maxYearsAgo)
        return date >= maxPastDate
      },
      message: `Date cannot be more than ${maxYearsAgo} years ago`
    })
  }

  // Register field validation
  function registerField(fieldName: string, fieldRules: ValidationRule[]) {
    validations.value[fieldName] = {
      rules: fieldRules,
      isDirty: false,
      isTouched: false
    }
  }

  // Validate single field
  function validateField(fieldName: string, value: any): string[] {
    const field = validations.value[fieldName]
    if (!field) return []

    const errors: string[] = []
    field.rules.forEach(rule => {
      if (!rule.test(value)) {
        errors.push(rule.message)
      }
    })

    return errors
  }

  // Mark field as dirty (value changed)
  function markFieldDirty(fieldName: string) {
    if (validations.value[fieldName]) {
      validations.value[fieldName].isDirty = true
    }
  }

  // Mark field as touched (focused/blurred)
  function markFieldTouched(fieldName: string) {
    if (validations.value[fieldName]) {
      validations.value[fieldName].isTouched = true
    }
  }

  // Validate all fields
  function validateForm(formData: Record<string, any>): Record<string, string[]> {
    const allErrors: Record<string, string[]> = {}

    Object.keys(validations.value).forEach(fieldName => {
      const errors = validateField(fieldName, formData[fieldName])
      if (errors.length > 0) {
        allErrors[fieldName] = errors
      }
      markFieldTouched(fieldName)
    })

    return allErrors
  }

  // Check if form is valid
  const isFormValid = computed(() => {
    return Object.keys(validations.value).every(fieldName => {
      const field = validations.value[fieldName]
      return !field.isTouched || validateField(fieldName, null).length === 0
    })
  })

  // Check if field is valid
  function isFieldValid(fieldName: string, value: any): boolean {
    return validateField(fieldName, value).length === 0
  }

  // Reset validation state
  function resetValidation() {
    Object.keys(validations.value).forEach(fieldName => {
      validations.value[fieldName].isDirty = false
      validations.value[fieldName].isTouched = false
    })
    isSubmitting.value = false
  }

  // Submit handler with validation
  async function submitForm<T>(
    formData: Record<string, any>,
    submitFn: (data: Record<string, any>) => Promise<T>
  ): Promise<T | null> {
    isSubmitting.value = true

    try {
      const errors = validateForm(formData)
      
      if (Object.keys(errors).length > 0) {
        throw new Error('Form validation failed')
      }

      const result = await submitFn(formData)
      resetValidation()
      return result

    } catch (error) {
      console.error('Form submission error:', error)
      throw error
    } finally {
      isSubmitting.value = false
    }
  }

  return {
    validations,
    isSubmitting,
    isFormValid,
    rules,
    registerField,
    validateField,
    markFieldDirty,
    markFieldTouched,
    validateForm,
    isFieldValid,
    resetValidation,
    submitForm
  }
}