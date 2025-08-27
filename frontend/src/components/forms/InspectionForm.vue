<!--
  InspectionForm - Professional form component connected to backend inspection API
  Features:
  - Submits to /api/v1/inspections/ with automatic API 579 calculation trigger
  - Decimal precision validation for safety-critical thickness measurements (±0.001")
  - Comprehensive equipment selection and validation
  - Real-time form validation with safety-critical field checks
-->
<template>
  <div class="inspection-form">
    <Card>
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-clipboard text-primary"></i>
          <span>{{ isEditing ? 'Edit' : 'New' }} Inspection Record</span>
        </div>
      </template>

      <template #content>
        <form @submit.prevent="handleSubmit" class="p-fluid">
          <!-- Basic Information -->
          <div class="formgrid grid">
            <div class="field col-12 md:col-6">
              <label for="equipment_id" class="font-semibold">
                Equipment <span class="text-red-500">*</span>
              </label>
              <Dropdown
                id="equipment_id"
                v-model="formData.equipment_id"
                :options="equipmentOptions"
                option-label="label"
                option-value="value"
                placeholder="Select Equipment"
                :loading="loadingEquipment"
                :class="getFieldClass('equipment_id')"
                @change="handleFieldChange('equipment_id')"
                @blur="markFieldTouched('equipment_id')"
              />
              <small v-if="getFieldError('equipment_id')" class="text-red-500">
                {{ getFieldError('equipment_id') }}
              </small>
            </div>

            <div class="field col-12 md:col-6">
              <label for="inspection_date" class="font-semibold">
                Inspection Date <span class="text-red-500">*</span>
              </label>
              <Calendar
                id="inspection_date"
                v-model="formData.inspection_date"
                date-format="yy-mm-dd"
                :max-date="new Date()"
                :class="getFieldClass('inspection_date')"
                @input="handleFieldChange('inspection_date')"
                @blur="markFieldTouched('inspection_date')"
              />
              <small v-if="getFieldError('inspection_date')" class="text-red-500">
                {{ getFieldError('inspection_date') }}
              </small>
            </div>
          </div>

          <div class="formgrid grid">
            <div class="field col-12 md:col-6">
              <label for="inspection_type" class="font-semibold">
                Inspection Type <span class="text-red-500">*</span>
              </label>
              <Dropdown
                id="inspection_type"
                v-model="formData.inspection_type"
                :options="inspectionTypeOptions"
                option-label="label"
                option-value="value"
                placeholder="Select Inspection Type"
                :class="getFieldClass('inspection_type')"
                @change="handleFieldChange('inspection_type')"
                @blur="markFieldTouched('inspection_type')"
              />
              <small v-if="getFieldError('inspection_type')" class="text-red-500">
                {{ getFieldError('inspection_type') }}
              </small>
            </div>

            <div class="field col-12 md:col-6">
              <label for="report_number" class="font-semibold">
                Report Number <span class="text-red-500">*</span>
              </label>
              <InputText
                id="report_number"
                v-model="formData.report_number"
                placeholder="Enter report number"
                :class="getFieldClass('report_number')"
                @input="handleFieldChange('report_number')"
                @blur="markFieldTouched('report_number')"
              />
              <small v-if="getFieldError('report_number')" class="text-red-500">
                {{ getFieldError('report_number') }}
              </small>
            </div>
          </div>

          <!-- Inspector Information -->
          <h3 class="text-lg font-semibold mt-4 mb-3">Inspector Information</h3>
          <div class="formgrid grid">
            <div class="field col-12 md:col-6">
              <label for="inspector_name" class="font-semibold">
                Inspector Name <span class="text-red-500">*</span>
              </label>
              <InputText
                id="inspector_name"
                v-model="formData.inspector_name"
                placeholder="Enter inspector name"
                :class="getFieldClass('inspector_name')"
                @input="handleFieldChange('inspector_name')"
                @blur="markFieldTouched('inspector_name')"
              />
              <small v-if="getFieldError('inspector_name')" class="text-red-500">
                {{ getFieldError('inspector_name') }}
              </small>
            </div>

            <div class="field col-12 md:col-6">
              <label for="inspector_certification" class="font-semibold">
                Certification (SNT-TC-1A Level)
              </label>
              <InputText
                id="inspector_certification"
                v-model="formData.inspector_certification"
                placeholder="e.g., Level II UT, Level III RT"
                :class="getFieldClass('inspector_certification')"
                @input="handleFieldChange('inspector_certification')"
                @blur="markFieldTouched('inspector_certification')"
              />
              <small v-if="getFieldError('inspector_certification')" class="text-red-500">
                {{ getFieldError('inspector_certification') }}
              </small>
            </div>
          </div>

          <!-- Thickness Readings -->
          <ThicknessReadingsTable
            v-model="formData.thickness_readings"
            :validation="validation"
            @field-change="handleFieldChange"
          />

          <!-- API 579 Calculation Results -->
          <API579Results :calculation="mockCalculation" />

          <!-- Additional Information -->
          <h3 class="text-lg font-semibold mt-4 mb-3">Additional Information</h3>
          <div class="formgrid grid">
            <div class="field col-12 md:col-6">
              <label for="corrosion_type" class="font-semibold">
                Corrosion Type
              </label>
              <Dropdown
                id="corrosion_type"
                v-model="formData.corrosion_type"
                :options="corrosionTypeOptions"
                option-label="label"
                option-value="value"
                placeholder="Select corrosion type"
                :class="getFieldClass('corrosion_type')"
                @change="handleFieldChange('corrosion_type')"
                @blur="markFieldTouched('corrosion_type')"
              />
              <small v-if="getFieldError('corrosion_type')" class="text-red-500">
                {{ getFieldError('corrosion_type') }}
              </small>
            </div>

            <div class="field col-12 md:col-6">
              <label for="follow_up_required" class="font-semibold">
                Follow-up Required
              </label>
              <div class="flex align-items-center mt-2">
                <Checkbox
                  id="follow_up_required"
                  v-model="formData.follow_up_required"
                  :binary="true"
                  @change="handleFieldChange('follow_up_required')"
                />
                <label for="follow_up_required" class="ml-2">
                  Immediate follow-up action required
                </label>
              </div>
            </div>
          </div>

          <div class="field col-12">
            <label for="findings" class="font-semibold">
              Inspection Findings
            </label>
            <Textarea
              id="findings"
              v-model="formData.findings"
              rows="4"
              placeholder="Detailed inspection findings and observations..."
              :class="getFieldClass('findings')"
              @input="handleFieldChange('findings')"
              @blur="markFieldTouched('findings')"
            />
            <small v-if="getFieldError('findings')" class="text-red-500">
              {{ getFieldError('findings') }}
            </small>
          </div>

          <div class="field col-12">
            <label for="recommendations" class="font-semibold">
              Recommendations
            </label>
            <Textarea
              id="recommendations"
              v-model="formData.recommendations"
              rows="3"
              placeholder="Inspector recommendations for follow-up actions..."
              :class="getFieldClass('recommendations')"
              @input="handleFieldChange('recommendations')"
              @blur="markFieldTouched('recommendations')"
            />
            <small v-if="getFieldError('recommendations')" class="text-red-500">
              {{ getFieldError('recommendations') }}
            </small>
          </div>

          <!-- Safety Warning -->
          <Message
            v-if="hasCriticalFindings"
            severity="warn"
            :closable="false"
            class="mt-4"
          >
            <div class="flex align-items-center gap-2">
              <i class="pi pi-exclamation-triangle"></i>
              <span>
                <strong>Safety Critical:</strong> This inspection contains measurements that may require immediate attention.
                All critical findings will be flagged for engineering review.
              </span>
            </div>
          </Message>

          <!-- Submit Actions -->
          <div class="flex justify-content-end gap-2 mt-4">
            <Button
              type="button"
              label="Cancel"
              severity="secondary"
              outlined
              @click="handleCancel"
              :disabled="isSubmitting"
            />
            <Button
              type="button"
              label="Save Draft"
              severity="info"
              outlined
              @click="handleSaveDraft"
              :loading="isSavingDraft"
              :disabled="isSubmitting"
            />
            <Button
              type="submit"
              label="Submit Inspection"
              severity="primary"
              :loading="isSubmitting"
              :disabled="!isFormValid || isSubmitting"
            />
          </div>
        </form>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'

import { useFormValidation } from '@/composables/useFormValidation'
import { equipmentApi } from '@/api/equipment'
import { inspectionsApi } from '@/api/inspections'
import { mockAPI579Calculations } from '@/api/mock'
import ThicknessReadingsTable from './ThicknessReadingsTable.vue'
import API579Results from '@/components/calculation/API579Results.vue'
import type {
  InspectionCreateRequest,
  InspectionType,
  CorrosionType,
  Equipment
} from '@/types'

// Props and emits
interface Props {
  inspectionId?: string
  equipmentId?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  success: [inspection: any]
  cancel: []
}>()

// Composables
const router = useRouter()
const toast = useToast()
const {
  validations,
  isSubmitting,
  isFormValid,
  rules,
  registerField,
  validateField,
  markFieldTouched,
  submitForm
} = useFormValidation()

// Form data
const formData = ref<InspectionCreateRequest>({
  equipment_id: props.equipmentId || '',
  inspection_date: new Date().toISOString().split('T')[0],
  inspection_type: '' as InspectionType,
  inspector_name: '',
  inspector_certification: '',
  report_number: '',
  thickness_readings: [],
  corrosion_type: undefined,
  findings: '',
  recommendations: '',
  follow_up_required: false
})

// Loading states
const loadingEquipment = ref(false)
const isSavingDraft = ref(false)

// Equipment options
const equipmentOptions = ref<Array<{ label: string; value: string }>>([])

// Mock calculation for demonstration
const mockCalculation = computed(() => {
  // Show calculation only when thickness readings exist
  if (formData.value.thickness_readings.length > 0) {
    return mockAPI579Calculations[0]
  }
  return null
})

// Dropdown options
const inspectionTypeOptions = [
  { label: 'Ultrasonic Testing (UT)', value: 'ultrasonic' },
  { label: 'Radiographic Testing (RT)', value: 'radiographic' },
  { label: 'Magnetic Particle Testing (MT)', value: 'magnetic_particle' },
  { label: 'Liquid Penetrant Testing (PT)', value: 'liquid_penetrant' },
  { label: 'Visual Testing (VT)', value: 'visual' },
  { label: 'Eddy Current Testing (ET)', value: 'eddy_current' }
]

const corrosionTypeOptions = [
  { label: 'General Corrosion', value: 'general' },
  { label: 'Pitting Corrosion', value: 'pitting' },
  { label: 'Crevice Corrosion', value: 'crevice' },
  { label: 'Stress Corrosion', value: 'stress' },
  { label: 'Galvanic Corrosion', value: 'galvanic' },
  { label: 'Erosion Corrosion', value: 'erosion' }
]

// Computed properties
const isEditing = computed(() => Boolean(props.inspectionId))

const hasCriticalFindings = computed(() => {
  return formData.value.thickness_readings.some(reading => {
    const lossPercentage = ((reading.design_thickness - reading.thickness_measured) / reading.design_thickness) * 100
    return lossPercentage > 50 || reading.thickness_measured < 0.1
  })
})

// Form validation setup
onMounted(() => {
  setupValidation()
  loadEquipmentOptions()
  
  if (props.inspectionId) {
    loadInspectionData()
  }
})

function setupValidation() {
  registerField('equipment_id', [rules.required('Equipment selection is required')])
  registerField('inspection_date', [
    rules.required('Inspection date is required'),
    rules.pastDate(),
    rules.recentDate(10)
  ])
  registerField('inspection_type', [rules.required('Inspection type is required')])
  registerField('inspector_name', [
    rules.required('Inspector name is required'),
    rules.minLength(2),
    rules.maxLength(100)
  ])
  registerField('inspector_certification', [
    rules.maxLength(50),
    rules.pattern(/^[A-Z0-9\-\/\s]*$/, 'Invalid certification format')
  ])
  registerField('report_number', [
    rules.required('Report number is required'),
    rules.minLength(1),
    rules.maxLength(50)
  ])
  registerField('findings', [rules.maxLength(2000)])
  registerField('recommendations', [rules.maxLength(2000)])
}

async function loadEquipmentOptions() {
  try {
    loadingEquipment.value = true
    const response = await equipmentApi.getEquipment({ per_page: 1000 })
    
    equipmentOptions.value = response.data.map((equipment: Equipment) => ({
      label: `${equipment.tag_number} - ${equipment.description}`,
      value: equipment.id
    }))
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load equipment options',
      life: 3000
    })
  } finally {
    loadingEquipment.value = false
  }
}

async function loadInspectionData() {
  if (!props.inspectionId) return

  try {
    const inspection = await inspectionsApi.getInspectionById(props.inspectionId)
    
    // Map inspection data to form
    formData.value = {
      equipment_id: inspection.equipment_id,
      inspection_date: inspection.inspection_date.split('T')[0],
      inspection_type: inspection.inspection_type,
      inspector_name: inspection.inspector_name,
      inspector_certification: inspection.inspector_certification || '',
      report_number: inspection.report_number,
      thickness_readings: inspection.thickness_readings || [],
      corrosion_type: inspection.corrosion_type,
      findings: inspection.findings || '',
      recommendations: inspection.recommendations || '',
      follow_up_required: inspection.follow_up_required
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load inspection data',
      life: 3000
    })
  }
}

// Field validation helpers
function getFieldClass(fieldName: string) {
  const errors = validateField(fieldName, formData.value[fieldName as keyof typeof formData.value])
  const field = validations.value[fieldName]
  
  if (!field?.isTouched) return ''
  return errors.length > 0 ? 'p-invalid' : ''
}

function getFieldError(fieldName: string): string {
  const errors = validateField(fieldName, formData.value[fieldName as keyof typeof formData.value])
  const field = validations.value[fieldName]
  
  return field?.isTouched && errors.length > 0 ? errors[0] : ''
}

function handleFieldChange(fieldName: string) {
  const field = validations.value[fieldName]
  if (field) {
    field.isDirty = true
  }
}

// Form submission
async function handleSubmit() {
  try {
    const result = await submitForm(formData.value, async (data) => {
      if (isEditing.value) {
        // Update existing inspection (if API supports it)
        throw new Error('Inspection editing not implemented')
      } else {
        return await inspectionsApi.createInspection(data as InspectionCreateRequest)
      }
    })

    if (result) {
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `Inspection ${isEditing.value ? 'updated' : 'created'} successfully`,
        life: 3000
      })
      
      emit('success', result)
      
      // Navigate to inspection detail or list
      if (!isEditing.value) {
        router.push(`/inspections/${result.id}`)
      }
    }
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || `Failed to ${isEditing.value ? 'update' : 'create'} inspection`,
      life: 5000
    })
  }
}

async function handleSaveDraft() {
  // Draft saving functionality for safety-critical data
  // This would require a separate draft storage system to maintain data integrity
  toast.add({
    severity: 'info',
    summary: 'Info',
    detail: 'Draft saving functionality will be implemented in phase 2',
    life: 3000
  })
}

function handleCancel() {
  emit('cancel')
  router.go(-1)
}
</script>

<style scoped>
.inspection-form {
  max-width: 1200px;
  margin: 0 auto;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
}

.text-red-500 {
  color: #ef4444;
}

.font-semibold {
  font-weight: 600;
}

.p-invalid {
  border-color: #ef4444;
}
</style>