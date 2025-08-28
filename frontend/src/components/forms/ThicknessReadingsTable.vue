<template>
  <div class="thickness-readings-table">
    <div class="flex justify-content-between align-items-center mb-3">
      <h3 class="text-lg font-semibold m-0">
        Thickness Readings <span class="text-red-500">*</span>
      </h3>
      <Button
        icon="pi pi-plus"
        label="Add Reading"
        size="small"
        @click="addReading"
        :disabled="readings.length >= maxReadings"
      />
    </div>

    <Message
      v-if="readings.length === 0"
      severity="info"
      :closable="false"
      class="mb-3"
    >
      At least one thickness reading is required for API 579 compliance.
      Add readings using the "Add Reading" button above.
    </Message>

    <Message
      v-if="readings.length > 0 && readings.length < 3"
      severity="warn"
      :closable="false"
      class="mb-3"
    >
      <strong>Statistical Confidence Warning:</strong> 
      Only {{ readings.length }} reading(s) provided. Minimum 3 readings recommended for statistical confidence.
    </Message>

    <DataTable
      v-if="readings.length > 0"
      v-model:selection="selectedReadings"
      :value="readings"
      dataKey="tempId"
      :scrollable="true"
      scrollHeight="400px"
      :reorderableColumns="true"
      class="p-datatable-sm"
    >
      <Column selectionMode="multiple" style="width: 3rem" :exportable="false"></Column>
      
      <Column field="cml_number" header="CML Number" style="min-width: 120px">
        <template #body="slotProps">
          <InputText
            v-model="slotProps.data.cml_number"
            placeholder="e.g., CML-01"
            :class="getReadingFieldClass(slotProps.index, 'cml_number')"
            @input="handleReadingChange(slotProps.index, 'cml_number')"
            @blur="validateReading(slotProps.index, 'cml_number')"
          />
          <small 
            v-if="getReadingFieldError(slotProps.index, 'cml_number')" 
            class="text-red-500 block"
          >
            {{ getReadingFieldError(slotProps.index, 'cml_number') }}
          </small>
        </template>
      </Column>

      <Column field="location_description" header="Location" style="min-width: 200px">
        <template #body="slotProps">
          <InputText
            v-model="slotProps.data.location_description"
            placeholder="Detailed location description"
            :class="getReadingFieldClass(slotProps.index, 'location_description')"
            @input="handleReadingChange(slotProps.index, 'location_description')"
            @blur="validateReading(slotProps.index, 'location_description')"
          />
          <small 
            v-if="getReadingFieldError(slotProps.index, 'location_description')" 
            class="text-red-500 block"
          >
            {{ getReadingFieldError(slotProps.index, 'location_description') }}
          </small>
        </template>
      </Column>

      <Column field="thickness_measured" header="Current Thickness (in)" style="min-width: 150px">
        <template #body="slotProps">
          <InputNumber
            v-model="slotProps.data.thickness_measured"
            :min-fraction-digits="3"
            :max-fraction-digits="3"
            :min="0.001"
            :max="10.000"
            :step="0.001"
            placeholder="0.000"
            :class="getReadingFieldClass(slotProps.index, 'thickness_measured')"
            @input="handleReadingChange(slotProps.index, 'thickness_measured')"
            @blur="validateReading(slotProps.index, 'thickness_measured')"
          />
          <small 
            v-if="getReadingFieldError(slotProps.index, 'thickness_measured')" 
            class="text-red-500 block"
          >
            {{ getReadingFieldError(slotProps.index, 'thickness_measured') }}
          </small>
        </template>
      </Column>

      <Column field="design_thickness" header="Design Thickness (in)" style="min-width: 150px">
        <template #body="slotProps">
          <InputNumber
            v-model="slotProps.data.design_thickness"
            :min-fraction-digits="3"
            :max-fraction-digits="3"
            :min="0.001"
            :max="10.000"
            :step="0.001"
            placeholder="0.000"
            :class="getReadingFieldClass(slotProps.index, 'design_thickness')"
            @input="handleReadingChange(slotProps.index, 'design_thickness')"
            @blur="validateReading(slotProps.index, 'design_thickness')"
          />
          <small 
            v-if="getReadingFieldError(slotProps.index, 'design_thickness')" 
            class="text-red-500 block"
          >
            {{ getReadingFieldError(slotProps.index, 'design_thickness') }}
          </small>
        </template>
      </Column>

      <Column field="previous_thickness" header="Previous Thickness (in)" style="min-width: 150px">
        <template #body="slotProps">
          <InputNumber
            v-model="slotProps.data.previous_thickness"
            :min-fraction-digits="3"
            :max-fraction-digits="3"
            :min="0.001"
            :max="10.000"
            :step="0.001"
            placeholder="0.000 (optional)"
            :class="getReadingFieldClass(slotProps.index, 'previous_thickness')"
            @input="handleReadingChange(slotProps.index, 'previous_thickness')"
            @blur="validateReading(slotProps.index, 'previous_thickness')"
          />
        </template>
      </Column>

      <Column field="grid_reference" header="Grid Ref" style="min-width: 100px">
        <template #body="slotProps">
          <InputText
            v-model="slotProps.data.grid_reference"
            placeholder="e.g., A-1"
            :class="getReadingFieldClass(slotProps.index, 'grid_reference')"
            @input="handleReadingChange(slotProps.index, 'grid_reference')"
            @blur="validateReading(slotProps.index, 'grid_reference')"
          />
        </template>
      </Column>

      <Column field="surface_condition" header="Surface Condition" style="min-width: 150px">
        <template #body="slotProps">
          <Dropdown
            v-model="slotProps.data.surface_condition"
            :options="surfaceConditionOptions"
            option-label="label"
            option-value="value"
            placeholder="Select condition"
            :class="getReadingFieldClass(slotProps.index, 'surface_condition')"
            @change="handleReadingChange(slotProps.index, 'surface_condition')"
          />
        </template>
      </Column>

      <Column field="metal_loss" header="Metal Loss %" style="min-width: 100px">
        <template #body="slotProps">
          <div class="text-center">
            <Tag
              v-if="slotProps.data.design_thickness && slotProps.data.thickness_measured"
              :value="calculateMetalLossPercentage(slotProps.data)"
              :severity="getMetalLossSeverity(slotProps.data)"
            />
          </div>
        </template>
      </Column>

      <Column header="Actions" style="width: 80px" :exportable="false">
        <template #body="slotProps">
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            size="small"
            @click="removeReading(slotProps.index)"
            :disabled="readings.length <= 1"
          />
        </template>
      </Column>
    </DataTable>

    <!-- Bulk Actions -->
    <div v-if="selectedReadings.length > 0" class="flex gap-2 mt-3">
      <Button
        icon="pi pi-trash"
        label="Delete Selected"
        severity="danger"
        outlined
        size="small"
        @click="removeSelectedReadings"
        :disabled="readings.length - selectedReadings.length < 1"
      />
      <Button
        icon="pi pi-copy"
        label="Duplicate Selected"
        severity="secondary"
        outlined
        size="small"
        @click="duplicateSelectedReadings"
      />
    </div>

    <!-- Summary Statistics -->
    <Card v-if="readings.length > 0" class="mt-4">
      <template #title>
        <span class="text-sm font-medium">Thickness Statistics</span>
      </template>
      <template #content>
        <div class="grid">
          <div class="col-12 md:col-3">
            <div class="text-center">
              <div class="text-2xl font-bold text-primary">{{ statisticalSummary.minThickness }}</div>
              <div class="text-sm text-600">Minimum (in)</div>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="text-center">
              <div class="text-2xl font-bold text-primary">{{ statisticalSummary.avgThickness }}</div>
              <div class="text-sm text-600">Average (in)</div>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="text-center">
              <div class="text-2xl font-bold text-primary">{{ statisticalSummary.maxThickness }}</div>
              <div class="text-sm text-600">Maximum (in)</div>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="text-center">
              <div class="text-2xl font-bold" :class="getConfidenceClass()">{{ statisticalSummary.confidenceLevel }}%</div>
              <div class="text-sm text-600">Confidence Level</div>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

import { useFormValidation } from '@/composables/useFormValidation'
import type { ThicknessReadingCreateRequest } from '@/types'

// Props and emits
interface Props {
  modelValue: ThicknessReadingCreateRequest[]
  validation?: any
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: ThicknessReadingCreateRequest[]]
  'field-change': [fieldName: string]
}>()

// Composables
const { rules, validateField } = useFormValidation()

// Local state
const readings = ref<(ThicknessReadingCreateRequest & { tempId: string })[]>([])
const selectedReadings = ref([])
const readingValidations = ref<Record<string, Record<string, { errors: string[], touched: boolean }>>>({})

const maxReadings = 100

// Surface condition options
const surfaceConditionOptions = [
  { label: 'Good', value: 'good' },
  { label: 'Fair', value: 'fair' },
  { label: 'Poor', value: 'poor' },
  { label: 'Corroded', value: 'corroded' },
  { label: 'Pitted', value: 'pitted' },
  { label: 'Scaled', value: 'scaled' }
]

// Initialize readings from modelValue
watch(() => props.modelValue, (newValue) => {
  readings.value = newValue.map((reading, index) => ({
    ...reading,
    tempId: `reading-${index}-${Date.now()}`
  }))
}, { immediate: true })

// Emit changes
watch(readings, (newReadings) => {
  const cleanReadings = newReadings.map(reading => {
    const { tempId, ...cleanReading } = reading
    return cleanReading
  })
  emit('update:modelValue', cleanReadings)
}, { deep: true })

// Statistical summary
const statisticalSummary = computed(() => {
  const validReadings = readings.value.filter(r => 
    r.thickness_measured !== null && 
    r.thickness_measured !== undefined && 
    r.thickness_measured > 0
  )

  if (validReadings.length === 0) {
    return {
      minThickness: '—',
      avgThickness: '—',
      maxThickness: '—',
      confidenceLevel: 0
    }
  }

  const thicknesses = validReadings.map(r => r.thickness_measured)
  const min = Math.min(...thicknesses)
  const max = Math.max(...thicknesses)
  const avg = thicknesses.reduce((sum, val) => sum + val, 0) / thicknesses.length

  // Calculate confidence level based on number of readings
  let confidenceLevel = 75 // Default
  if (validReadings.length >= 10) confidenceLevel = 95
  else if (validReadings.length >= 5) confidenceLevel = 85
  else if (validReadings.length >= 3) confidenceLevel = 80

  return {
    minThickness: min.toFixed(3),
    avgThickness: avg.toFixed(3),
    maxThickness: max.toFixed(3),
    confidenceLevel
  }
})

// Add new reading
function addReading() {
  const newReading: ThicknessReadingCreateRequest & { tempId: string } = {
    tempId: `reading-${readings.value.length}-${Date.now()}`,
    cml_number: `CML-${String(readings.value.length + 1).padStart(2, '0')}`,
    location_description: '',
    thickness_measured: null,
    design_thickness: null,
    previous_thickness: undefined,
    grid_reference: '',
    surface_condition: ''
  }
  
  readings.value.push(newReading)
  emit('field-change', 'thickness_readings')
}

// Remove reading
function removeReading(index: number) {
  if (readings.value.length > 1) {
    const readingId = readings.value[index].tempId
    delete readingValidations.value[readingId]
    readings.value.splice(index, 1)
    emit('field-change', 'thickness_readings')
  }
}

// Remove selected readings
function removeSelectedReadings() {
  const selectedIds = selectedReadings.value.map((r: any) => r.tempId)
  const remainingCount = readings.value.length - selectedIds.length
  
  if (remainingCount >= 1) {
    readings.value = readings.value.filter(r => !selectedIds.includes(r.tempId))
    selectedIds.forEach(id => delete readingValidations.value[id])
    selectedReadings.value = []
    emit('field-change', 'thickness_readings')
  }
}

// Duplicate selected readings
function duplicateSelectedReadings() {
  const selectedIds = selectedReadings.value.map((r: any) => r.tempId)
  const toDuplicate = readings.value.filter(r => selectedIds.includes(r.tempId))
  
  toDuplicate.forEach(reading => {
    const duplicated = {
      ...reading,
      tempId: `reading-dup-${Date.now()}-${Math.random()}`,
      cml_number: `${reading.cml_number}-COPY`
    }
    readings.value.push(duplicated)
  })
  
  selectedReadings.value = []
  emit('field-change', 'thickness_readings')
}

// Handle reading field changes
function handleReadingChange(index: number, fieldName: string) {
  emit('field-change', 'thickness_readings')
  
  // Clear validation state for this field
  const readingId = readings.value[index].tempId
  if (readingValidations.value[readingId]?.[fieldName]) {
    readingValidations.value[readingId][fieldName].touched = false
  }
}

// Validate individual reading field
function validateReading(index: number, fieldName: string) {
  const reading = readings.value[index]
  const readingId = reading.tempId
  const value = reading[fieldName as keyof typeof reading]

  // Initialize validation state
  if (!readingValidations.value[readingId]) {
    readingValidations.value[readingId] = {}
  }
  if (!readingValidations.value[readingId][fieldName]) {
    readingValidations.value[readingId][fieldName] = { errors: [], touched: false }
  }

  let fieldRules: any[] = []

  switch (fieldName) {
    case 'cml_number':
      fieldRules = [
        rules.required('CML number is required'),
        rules.pattern(/^[A-Z0-9\-]+$/, 'CML number must be uppercase letters, numbers, and hyphens only'),
        rules.maxLength(20)
      ]
      break
    case 'location_description':
      fieldRules = [
        rules.required('Location description is required'),
        rules.minLength(1),
        rules.maxLength(200)
      ]
      break
    case 'thickness_measured':
      fieldRules = [
        rules.required('Current thickness is required'),
        rules.thicknessRange(),
        rules.thicknessPrecision()
      ]
      break
    case 'design_thickness':
      fieldRules = [
        rules.required('Design thickness is required'),
        rules.thicknessRange(),
        rules.thicknessPrecision()
      ]
      break
    case 'previous_thickness':
      fieldRules = [
        rules.thicknessRange(),
        rules.thicknessPrecision()
      ]
      break
    case 'grid_reference':
      fieldRules = [
        rules.pattern(/^[A-Z]\-[0-9]+$/, 'Grid reference format: A-1, B-3, etc.'),
        rules.maxLength(10)
      ]
      break
  }

  // Validate field
  const errors: string[] = []
  fieldRules.forEach(rule => {
    if (!rule.test(value)) {
      errors.push(rule.message)
    }
  })

  // Check for duplicate CML numbers
  if (fieldName === 'cml_number' && value) {
    const duplicates = readings.value.filter((r, i) => 
      i !== index && r.cml_number === value
    )
    if (duplicates.length > 0) {
      errors.push('CML number must be unique')
    }
  }

  // Store validation result
  readingValidations.value[readingId][fieldName] = {
    errors,
    touched: true
  }
}

// Get field validation class
function getReadingFieldClass(index: number, fieldName: string): string {
  const readingId = readings.value[index].tempId
  const validation = readingValidations.value[readingId]?.[fieldName]
  
  if (!validation?.touched) return ''
  return validation.errors.length > 0 ? 'p-invalid' : ''
}

// Get field validation error
function getReadingFieldError(index: number, fieldName: string): string {
  const readingId = readings.value[index].tempId
  const validation = readingValidations.value[readingId]?.[fieldName]
  
  return validation?.touched && validation.errors.length > 0 ? validation.errors[0] : ''
}

// Calculate metal loss percentage
function calculateMetalLossPercentage(reading: any): string {
  if (!reading.design_thickness || !reading.thickness_measured) return '—'
  
  const lossPercentage = ((reading.design_thickness - reading.thickness_measured) / reading.design_thickness) * 100
  return `${lossPercentage.toFixed(1)}%`
}

// Get metal loss severity
function getMetalLossSeverity(reading: any): string {
  if (!reading.design_thickness || !reading.thickness_measured) return 'info'
  
  const lossPercentage = ((reading.design_thickness - reading.thickness_measured) / reading.design_thickness) * 100
  
  if (lossPercentage > 50) return 'danger'
  if (lossPercentage > 25) return 'warning'
  return 'success'
}

// Get confidence level class
function getConfidenceClass(): string {
  const confidence = statisticalSummary.value.confidenceLevel
  if (confidence >= 85) return 'text-green-500'
  if (confidence >= 75) return 'text-yellow-500'
  return 'text-red-500'
}
</script>

<style scoped>
.thickness-readings-table {
  margin: 1rem 0;
}

.text-red-500 {
  color: #ef4444;
}

.text-green-500 {
  color: #10b981;
}

.text-yellow-500 {
  color: #f59e0b;
}

.p-invalid {
  border-color: #ef4444;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  padding: 0.5rem;
}

:deep(.p-inputtext), 
:deep(.p-inputnumber-input),
:deep(.p-dropdown) {
  width: 100%;
}
</style>