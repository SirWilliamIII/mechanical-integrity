<template>
  <Dialog v-model:visible="visible" modal header="Equipment Design Validation" :style="{ width: '50rem' }">
    <div class="flex flex-column gap-4">
      <!-- Equipment Parameters Form -->
      <div class="grid">
        <div class="col-6">
          <label for="design_pressure" class="font-semibold">Design Pressure (PSI)*</label>
          <InputNumber
            id="design_pressure"
            v-model="validationRequest.design_pressure"
            :min="0.1"
            :max="10000"
            :maxFractionDigits="2"
            placeholder="150.0"
            class="w-full"
          />
        </div>
        
        <div class="col-6">
          <label for="design_temperature" class="font-semibold">Design Temperature (°F)*</label>
          <InputNumber
            id="design_temperature"
            v-model="validationRequest.design_temperature"
            :min="-320"
            :max="1500"
            :maxFractionDigits="1"
            placeholder="400.0"
            class="w-full"
          />
        </div>
        
        <div class="col-6">
          <label for="design_thickness" class="font-semibold">Design Thickness (inches)*</label>
          <InputNumber
            id="design_thickness"
            v-model="validationRequest.design_thickness"
            :min="0.001"
            :max="10"
            :maxFractionDigits="3"
            placeholder="0.500"
            class="w-full"
          />
        </div>
        
        <div class="col-6">
          <label for="corrosion_allowance" class="font-semibold">Corrosion Allowance (inches)</label>
          <InputNumber
            id="corrosion_allowance"
            v-model="validationRequest.corrosion_allowance"
            :min="0"
            :max="1"
            :maxFractionDigits="3"
            placeholder="0.125"
            class="w-full"
          />
        </div>
        
        <div class="col-6">
          <label for="material_specification" class="font-semibold">Material Specification*</label>
          <Dropdown
            id="material_specification"
            v-model="validationRequest.material_specification"
            :options="supportedMaterials"
            placeholder="Select Material"
            class="w-full"
            :loading="loadingMaterials"
          />
        </div>
        
        <div class="col-6">
          <label for="equipment_type" class="font-semibold">Equipment Type*</label>
          <Dropdown
            id="equipment_type"
            v-model="validationRequest.equipment_type"
            :options="equipmentTypes"
            optionLabel="label"
            optionValue="value"
            placeholder="Select Type"
            class="w-full"
          />
        </div>
        
        <div class="col-12">
          <label for="service_description" class="font-semibold">Service Description</label>
          <InputText
            id="service_description"
            v-model="validationRequest.service_description"
            placeholder="e.g., Crude Oil, Steam, Cooling Water"
            class="w-full"
          />
        </div>
      </div>

      <!-- Validation Button -->
      <div class="flex justify-content-center">
        <Button 
          label="Validate Design" 
          icon="pi pi-check" 
          @click="validateDesign"
          :loading="validating"
          :disabled="!isFormValid"
          class="p-button-primary"
        />
      </div>

      <!-- Validation Results -->
      <div v-if="validationResults.length > 0" class="mt-4">
        <h3>Validation Results</h3>
        <div class="flex flex-column gap-3">
          <Card 
            v-for="result in validationResults" 
            :key="result.field"
            class="p-2"
            :class="getResultCardClass(result)"
          >
            <template #content>
              <div class="flex align-items-center gap-2 mb-2">
                <i :class="getResultIcon(result)"></i>
                <strong>{{ formatFieldName(result.field) }}</strong>
                <Badge 
                  :value="result.valid ? 'PASS' : 'FAIL'" 
                  :severity="result.valid ? 'success' : 'danger'"
                />
              </div>
              
              <div v-if="!result.valid" class="text-red-600 mb-2">
                <strong>Issue:</strong> {{ result.reason }}
                <div v-if="result.action_required" class="mt-1">
                  <strong>Action Required:</strong> {{ result.action_required }}
                </div>
                <div v-if="result.api_reference" class="text-sm text-gray-500 mt-1">
                  Reference: {{ result.api_reference }}
                </div>
              </div>
              
              <div v-if="result.warnings && result.warnings.length > 0" class="text-orange-600">
                <strong>Warnings:</strong>
                <ul class="mt-1">
                  <li v-for="warning in result.warnings" :key="warning">{{ warning }}</li>
                </ul>
              </div>
              
              <div class="text-sm text-gray-500 mt-2">
                Value: {{ result.value }}
              </div>
            </template>
          </Card>
        </div>

        <!-- Overall Summary -->
        <Card class="mt-4" :class="overallValid ? 'border-green-500' : 'border-red-500'">
          <template #content>
            <div class="flex align-items-center gap-2">
              <i :class="overallValid ? 'pi pi-check-circle text-green-600' : 'pi pi-exclamation-triangle text-red-600'"></i>
              <strong>Overall Validation: </strong>
              <Badge 
                :value="overallValid ? 'DESIGN ACCEPTABLE' : 'DESIGN REQUIRES ATTENTION'" 
                :severity="overallValid ? 'success' : 'danger'"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>

    <template #footer>
      <Button label="Close" @click="closeDialog" class="p-button-text" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Card from 'primevue/card'
import Badge from 'primevue/badge'
import { equipmentApi } from '@/api/equipment'
import type { EquipmentValidationRequest, ValidationResult } from '@/types'

// Props and emits
const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// Reactive data
const validationRequest = ref<EquipmentValidationRequest>({
  design_pressure: '',
  design_temperature: '',
  design_thickness: '',
  material_specification: '',
  equipment_type: 'pressure_vessel',
  service_description: '',
  corrosion_allowance: '0.125'
})

const validationResults = ref<ValidationResult[]>([])
const supportedMaterials = ref<string[]>([])
const validating = ref(false)
const loadingMaterials = ref(false)

// Equipment type options
const equipmentTypes = [
  { label: 'Pressure Vessel', value: 'pressure_vessel' },
  { label: 'Storage Tank', value: 'storage_tank' },
  { label: 'Piping', value: 'piping' },
  { label: 'Heat Exchanger', value: 'heat_exchanger' }
]

// Computed properties
const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const isFormValid = computed(() => {
  return validationRequest.value.design_pressure &&
         validationRequest.value.design_temperature &&
         validationRequest.value.design_thickness &&
         validationRequest.value.material_specification &&
         validationRequest.value.equipment_type
})

const overallValid = computed(() => {
  return validationResults.value.length > 0 && 
         validationResults.value.every(result => result.valid)
})

// Methods
const loadSupportedMaterials = async () => {
  try {
    loadingMaterials.value = true
    supportedMaterials.value = await equipmentApi.getSupportedMaterials()
  } catch (error) {
    console.error('Failed to load materials:', error)
    // Fallback to common materials if API fails
    supportedMaterials.value = [
      'SA-516-70', 'SA-516-60', 'SA-106-B', 'SA-240-304', 'SA-240-316'
    ]
  } finally {
    loadingMaterials.value = false
  }
}

const validateDesign = async () => {
  try {
    validating.value = true
    
    // Prepare request data with proper string formatting for decimal precision
    const requestData = {
      ...validationRequest.value,
      design_pressure: validationRequest.value.design_pressure.toString(),
      design_temperature: validationRequest.value.design_temperature.toString(),
      design_thickness: validationRequest.value.design_thickness.toString(),
      corrosion_allowance: validationRequest.value.corrosion_allowance?.toString() || '0.125'
    }
    
    validationResults.value = await equipmentApi.validateEquipmentDesign(requestData)
  } catch (error) {
    console.error('Validation failed:', error)
    // Show error message to user
  } finally {
    validating.value = false
  }
}

const closeDialog = () => {
  visible.value = false
  // Reset form
  validationResults.value = []
}

const getResultCardClass = (result: ValidationResult) => {
  if (!result.valid) return 'border-red-500 bg-red-50'
  if (result.warnings && result.warnings.length > 0) return 'border-orange-500 bg-orange-50'
  return 'border-green-500 bg-green-50'
}

const getResultIcon = (result: ValidationResult) => {
  if (!result.valid) return 'pi pi-times-circle text-red-600'
  if (result.warnings && result.warnings.length > 0) return 'pi pi-exclamation-triangle text-orange-600'
  return 'pi pi-check-circle text-green-600'
}

const formatFieldName = (field: string) => {
  const fieldMap: Record<string, string> = {
    'pressure': 'Design Pressure',
    'temperature': 'Design Temperature', 
    'thickness': 'Design Thickness',
    'material_specification': 'Material Specification',
    'thickness_adequacy': 'Thickness Adequacy',
    'material_pressure_compatibility': 'Material-Pressure Compatibility',
    'material_temperature_compatibility': 'Material-Temperature Compatibility'
  }
  return fieldMap[field] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Lifecycle
onMounted(() => {
  loadSupportedMaterials()
})
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
}

.col-6 {
  grid-column: span 6;
}

.col-12 {
  grid-column: span 12;
}

@media (max-width: 768px) {
  .col-6 {
    grid-column: span 12;
  }
}
</style>