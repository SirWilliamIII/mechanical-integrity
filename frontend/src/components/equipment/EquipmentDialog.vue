<template>
  <Dialog 
    v-model:visible="dialogVisible" 
    :style="{ width: '800px' }" 
    :header="dialogTitle"
    :modal="true"
    class="equipment-dialog"
    @hide="onDialogHide"
  >
    <form @submit.prevent="saveEquipment" class="equipment-form">
      <div class="form-grid">
        <!-- Basic Information -->
        <div class="form-section">
          <h3 class="section-title">
            <i class="pi pi-info-circle"></i>
            Basic Information
          </h3>
          
          <div class="form-row">
            <div class="form-field">
              <label for="tag-number">Tag Number *</label>
              <InputText 
                id="tag-number"
                v-model="formData.tag_number"
                :class="{ 'p-invalid': errors.tag_number }"
                placeholder="e.g., V-101, T-201"
                required
              />
              <small v-if="errors.tag_number" class="p-error">{{ errors.tag_number }}</small>
            </div>
            
            <div class="form-field">
              <label for="equipment-type">Equipment Type *</label>
              <Dropdown 
                id="equipment-type"
                v-model="formData.equipment_type"
                :options="equipmentTypes"
                option-label="label"
                option-value="value"
                :class="{ 'p-invalid': errors.equipment_type }"
                placeholder="Select equipment type"
                required
              />
              <small v-if="errors.equipment_type" class="p-error">{{ errors.equipment_type }}</small>
            </div>
          </div>

          <div class="form-field">
            <label for="description">Description *</label>
            <Textarea 
              id="description"
              v-model="formData.description"
              :class="{ 'p-invalid': errors.description }"
              placeholder="Detailed equipment description"
              rows="3"
              required
            />
            <small v-if="errors.description" class="p-error">{{ errors.description }}</small>
          </div>

          <div class="form-row">
            <div class="form-field">
              <label for="location">Location *</label>
              <AutoComplete 
                id="location"
                v-model="formData.location"
                :suggestions="locationSuggestions"
                @complete="searchLocations"
                :class="{ 'p-invalid': errors.location }"
                placeholder="e.g., Unit 100, Tank Farm"
                force-selection
                required
              />
              <small v-if="errors.location" class="p-error">{{ errors.location }}</small>
            </div>
            
            <div class="form-field">
              <label for="service-fluid">Service Fluid</label>
              <InputText 
                id="service-fluid"
                v-model="formData.service_fluid"
                placeholder="e.g., Crude Oil, Natural Gas"
              />
            </div>
          </div>
        </div>

        <!-- Design Parameters -->
        <div class="form-section">
          <h3 class="section-title">
            <i class="pi pi-cog"></i>
            Design Parameters
          </h3>
          
          <div class="form-row">
            <div class="form-field">
              <label for="design-pressure">Design Pressure (psig) *</label>
              <InputNumber 
                id="design-pressure"
                v-model="formData.design_pressure"
                :class="{ 'p-invalid': errors.design_pressure }"
                mode="decimal"
                :min="0"
                :max="10000"
                :fraction-digits="1"
                suffix=" psig"
                placeholder="0.0"
                required
              />
              <small v-if="errors.design_pressure" class="p-error">{{ errors.design_pressure }}</small>
            </div>
            
            <div class="form-field">
              <label for="design-temperature">Design Temperature (°F) *</label>
              <InputNumber 
                id="design-temperature"
                v-model="formData.design_temperature"
                :class="{ 'p-invalid': errors.design_temperature }"
                mode="decimal"
                :min="-100"
                :max="2000"
                :fraction-digits="1"
                suffix="°F"
                placeholder="0.0"
                required
              />
              <small v-if="errors.design_temperature" class="p-error">{{ errors.design_temperature }}</small>
            </div>
          </div>

          <div class="form-row">
            <div class="form-field">
              <label for="design-thickness">Design Thickness (inches) *</label>
              <InputNumber 
                id="design-thickness"
                v-model="formData.design_thickness"
                :class="{ 'p-invalid': errors.design_thickness }"
                mode="decimal"
                :min="0.001"
                :max="10"
                :fraction-digits="3"
                suffix=" in"
                placeholder="0.000"
                required
              />
              <small v-if="errors.design_thickness" class="p-error">{{ errors.design_thickness }}</small>
            </div>
            
            <div class="form-field">
              <label for="corrosion-allowance">Corrosion Allowance (inches) *</label>
              <InputNumber 
                id="corrosion-allowance"
                v-model="formData.corrosion_allowance"
                :class="{ 'p-invalid': errors.corrosion_allowance }"
                mode="decimal"
                :min="0"
                :max="1"
                :fraction-digits="3"
                suffix=" in"
                placeholder="0.000"
                required
              />
              <small v-if="errors.corrosion_allowance" class="p-error">{{ errors.corrosion_allowance }}</small>
            </div>
          </div>

          <div class="form-field">
            <label for="material-specification">Material Specification *</label>
            <AutoComplete 
              id="material-specification"
              v-model="formData.material_specification"
              :suggestions="materialSuggestions"
              @complete="searchMaterials"
              :class="{ 'p-invalid': errors.material_specification }"
              placeholder="e.g., SA-516 Grade 70, SA-240 Type 316L"
              required
            />
            <small v-if="errors.material_specification" class="p-error">{{ errors.material_specification }}</small>
          </div>
        </div>

        <!-- Installation & Status -->
        <div class="form-section">
          <h3 class="section-title">
            <i class="pi pi-calendar"></i>
            Installation & Status
          </h3>
          
          <div class="form-row">
            <div class="form-field">
              <label for="installation-date">Installation Date *</label>
              <Calendar 
                id="installation-date"
                v-model="installationDateModel"
                :class="{ 'p-invalid': errors.installation_date }"
                date-format="mm/dd/yy"
                :show-icon="true"
                :max-date="new Date()"
                placeholder="Select installation date"
                required
              />
              <small v-if="errors.installation_date" class="p-error">{{ errors.installation_date }}</small>
            </div>
            
            <div class="form-field" v-if="isEditMode">
              <label for="status">Equipment Status</label>
              <Dropdown 
                id="status"
                v-model="formData.status"
                :options="equipmentStatuses"
                option-label="label"
                option-value="value"
                placeholder="Select status"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Form Actions -->
      <div class="form-actions">
        <Button 
          type="button"
          label="Cancel" 
          icon="pi pi-times" 
          @click="cancelForm"
          severity="secondary"
          outlined
        />
        <Button 
          type="submit"
          :label="isEditMode ? 'Update Equipment' : 'Create Equipment'"
          :icon="isEditMode ? 'pi pi-check' : 'pi pi-plus'"
          :loading="saving"
          severity="primary"
        />
      </div>
    </form>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { equipmentApi } from '@/api/equipment'
import type { 
  Equipment, 
  EquipmentCreateRequest, 
  EquipmentUpdateRequest,
  EquipmentType,
  EquipmentStatus
} from '@/types'

// Props & Emits
interface Props {
  visible: boolean
  equipment?: Equipment | null
}

const props = withDefaults(defineProps<Props>(), {
  equipment: null
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'equipment-saved': [equipment: Equipment]
}>()

// State
const saving = ref(false)
const errors = ref<Record<string, string>>({})
const locationSuggestions = ref<string[]>([])
const materialSuggestions = ref<string[]>([])

// Form data
const defaultFormData = (): EquipmentCreateRequest => ({
  tag_number: '',
  equipment_type: '' as EquipmentType,
  description: '',
  design_pressure: 0,
  design_temperature: 0,
  design_thickness: 0,
  material_specification: '',
  installation_date: '',
  location: '',
  service_fluid: '',
  corrosion_allowance: 0
})

const formData = ref<EquipmentCreateRequest & { status?: EquipmentStatus }>(defaultFormData())

// Options
const equipmentTypes = [
  { label: 'Pressure Vessel', value: 'pressure_vessel' },
  { label: 'Storage Tank', value: 'storage_tank' },
  { label: 'Heat Exchanger', value: 'heat_exchanger' },
  { label: 'Piping System', value: 'piping_system' },
  { label: 'Reactor', value: 'reactor' }
]

const equipmentStatuses = [
  { label: 'In Service', value: 'in_service' },
  { label: 'Out of Service', value: 'out_of_service' },
  { label: 'Maintenance', value: 'maintenance' },
  { label: 'Inspection Due', value: 'inspection_due' },
  { label: 'Decommissioned', value: 'decommissioned' }
]

// Predefined options
const commonLocations = [
  'Unit 100', 'Unit 200', 'Unit 300', 'Unit 400',
  'Tank Farm', 'Utilities', 'Warehouse', 'Loading Dock',
  'Process Area A', 'Process Area B', 'Cooling Tower',
  'Boiler House', 'Compressor House'
]

const commonMaterials = [
  'SA-516 Grade 70',
  'SA-240 Type 316L',
  'SA-240 Type 304L',
  'SA-106 Grade B',
  'SA-333 Grade 6',
  'SA-312 Type 316L',
  'SA-789 UNS S31803',
  'SA-790 UNS S32750',
  'Inconel 625',
  'Hastelloy C-276'
]

// Computed
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const isEditMode = computed(() => !!props.equipment)
const dialogTitle = computed(() => isEditMode.value ? 'Edit Equipment' : 'Create New Equipment')

// Installation date model for Calendar component
const installationDateModel = computed({
  get: () => {
    if (typeof formData.value.installation_date === 'string' && formData.value.installation_date) {
      return new Date(formData.value.installation_date)
    }
    return formData.value.installation_date as Date | null
  },
  set: (value: Date | null) => {
    formData.value.installation_date = value ? value.toISOString().split('T')[0] : ''
  }
})

// Methods
function resetForm() {
  formData.value = defaultFormData()
  errors.value = {}
}

function loadEquipmentData() {
  if (props.equipment) {
    formData.value = {
      tag_number: props.equipment.tag_number,
      equipment_type: props.equipment.equipment_type,
      description: props.equipment.description,
      design_pressure: props.equipment.design_pressure,
      design_temperature: props.equipment.design_temperature,
      design_thickness: props.equipment.design_thickness,
      material_specification: props.equipment.material_specification,
      installation_date: props.equipment.installation_date,
      location: props.equipment.location,
      service_fluid: props.equipment.service_fluid,
      corrosion_allowance: props.equipment.corrosion_allowance,
      status: props.equipment.status
    }
  } else {
    resetForm()
  }
}

function validateForm(): boolean {
  errors.value = {}
  let isValid = true

  // Required field validation
  if (!formData.value.tag_number.trim()) {
    errors.value.tag_number = 'Tag number is required'
    isValid = false
  }

  if (!formData.value.equipment_type) {
    errors.value.equipment_type = 'Equipment type is required'
    isValid = false
  }

  if (!formData.value.description.trim()) {
    errors.value.description = 'Description is required'
    isValid = false
  }

  if (!formData.value.location.trim()) {
    errors.value.location = 'Location is required'
    isValid = false
  }

  if (!formData.value.material_specification.trim()) {
    errors.value.material_specification = 'Material specification is required'
    isValid = false
  }

  if (!formData.value.installation_date) {
    errors.value.installation_date = 'Installation date is required'
    isValid = false
  }

  // Numeric validations
  if (formData.value.design_pressure <= 0) {
    errors.value.design_pressure = 'Design pressure must be greater than 0'
    isValid = false
  }

  if (formData.value.design_thickness <= 0) {
    errors.value.design_thickness = 'Design thickness must be greater than 0'
    isValid = false
  }

  if (formData.value.corrosion_allowance < 0) {
    errors.value.corrosion_allowance = 'Corrosion allowance cannot be negative'
    isValid = false
  }

  return isValid
}

async function saveEquipment() {
  if (!validateForm()) return

  try {
    saving.value = true

    // Installation date is already formatted by the computed property
    const installationDate = formData.value.installation_date

    const equipmentData: EquipmentCreateRequest | EquipmentUpdateRequest = {
      ...formData.value,
      installation_date: installationDate
    }

    let result: Equipment
    if (isEditMode.value && props.equipment) {
      result = await equipmentApi.updateEquipment(props.equipment.id, equipmentData as EquipmentUpdateRequest)
    } else {
      result = await equipmentApi.createEquipment(equipmentData as EquipmentCreateRequest)
    }

    emit('equipment-saved', result)
    
  } catch (error: any) {
    console.error('Error saving equipment:', error)
    
    // Handle validation errors from API
    if (error.response?.status === 422 && error.response.data?.detail) {
      const apiErrors = error.response.data.detail
      if (Array.isArray(apiErrors)) {
        apiErrors.forEach((err: any) => {
          if (err.loc && err.msg) {
            const field = err.loc[err.loc.length - 1]
            errors.value[field] = err.msg
          }
        })
      }
    } else {
      errors.value.general = error.message || 'Failed to save equipment'
    }
  } finally {
    saving.value = false
  }
}

function cancelForm() {
  dialogVisible.value = false
}

function onDialogHide() {
  // Reset form when dialog closes
  nextTick(() => {
    resetForm()
  })
}

// AutoComplete search methods
function searchLocations(event: any) {
  const query = event.query.toLowerCase()
  locationSuggestions.value = commonLocations.filter(location => 
    location.toLowerCase().includes(query)
  )
}

function searchMaterials(event: any) {
  const query = event.query.toLowerCase()
  materialSuggestions.value = commonMaterials.filter(material => 
    material.toLowerCase().includes(query)
  )
}

// Watchers
watch(() => props.visible, (visible) => {
  if (visible) {
    loadEquipmentData()
  }
}, { immediate: true })

watch(() => props.equipment, () => {
  if (props.visible) {
    loadEquipmentData()
  }
}, { deep: true })
</script>

<style scoped>
.equipment-dialog {
  font-size: 0.9rem;
}

.equipment-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.form-section {
  border: 1px solid var(--p-surface-border);
  border-radius: var(--p-border-radius);
  padding: 1.5rem;
  background: var(--p-surface-card);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1.5rem 0;
  color: var(--p-text-color);
  font-size: 1.1rem;
  font-weight: 600;
  border-bottom: 1px solid var(--p-surface-border);
  padding-bottom: 0.75rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-row:last-child {
  margin-bottom: 0;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 500;
  color: var(--p-text-color);
  font-size: 0.9rem;
}

.form-field small.p-error {
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-surface-border);
}

/* Input styling adjustments */
:deep(.p-inputtext),
:deep(.p-dropdown),
:deep(.p-inputnumber-input),
:deep(.p-calendar input),
:deep(.p-autocomplete input) {
  font-size: 0.9rem;
}

:deep(.p-inputnumber) {
  width: 100%;
}

:deep(.p-calendar) {
  width: 100%;
}

:deep(.p-autocomplete) {
  width: 100%;
}

:deep(.p-dropdown) {
  width: 100%;
}

/* Error state styling */
:deep(.p-invalid) {
  border-color: var(--p-red-500);
}

:deep(.p-invalid:enabled:focus) {
  outline: 0 none;
  outline-offset: 0;
  box-shadow: 0 0 0 0.2rem var(--p-red-200);
  border-color: var(--p-red-500);
}

@media (max-width: 768px) {
  .equipment-dialog {
    width: 95vw !important;
    margin: 0.5rem;
  }
  
  .form-row {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .form-section {
    padding: 1rem;
  }
  
  .form-actions {
    flex-direction: column;
  }
}
</style>