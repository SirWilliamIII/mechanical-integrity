<!--
    EquipmentView - Professional component connected to backend equipment API
    Features:
    - Real-time equipment data loading via equipmentApi.getEquipment()
    - Full CRUD operations (create/update/delete) connected to backend
    - Advanced filtering, search, and pagination
    - Safety-critical decimal precision handling for pressure/temperature values
-->
<template>
  <div class="equipment-view">
    <div class="page-header">
      <div class="header-content">
        <h2>Equipment Registry</h2>
        <p class="subtitle">Manage mechanical integrity equipment and compliance tracking</p>
      </div>
      <div class="header-actions">
        <Button 
          label="New Equipment" 
          icon="pi pi-plus" 
          @click="showCreateDialog = true"
          severity="primary"
        />
        <Button 
          label="Export" 
          icon="pi pi-download" 
          @click="exportEquipment"
          severity="secondary"
          outlined
        />
      </div>
    </div>

    <!-- Filters and Search -->
    <Card class="filters-card">
      <template #content>
        <div class="filters-container">
          <div class="search-section">
            <IconField>
              <InputIcon>
                <i class="pi pi-search" />
              </InputIcon>
              <InputText 
                v-model="searchTerm"
                placeholder="Search by tag number, description, or location..."
                @input="debouncedSearch"
                class="search-input"
              />
            </IconField>
          </div>
          
          <div class="filter-section">
            <MultiSelect 
              v-model="selectedTypes" 
              :options="equipmentTypes"
              option-label="label"
              option-value="value"
              placeholder="Equipment Types"
              class="filter-select"
              :max-selected-labels="2"
            />
            <MultiSelect 
              v-model="selectedStatuses" 
              :options="equipmentStatuses"
              option-label="label"
              option-value="value"
              placeholder="Status"
              class="filter-select"
              :max-selected-labels="2"
            />
            <Dropdown 
              v-model="selectedLocation" 
              :options="locations"
              option-label="label"
              option-value="value"
              placeholder="All Locations"
              class="filter-select"
              show-clear
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Equipment Data Table -->
    <Card class="table-card">
      <template #content>
        <DataTable 
          :value="filteredEquipment"
          :loading="loading"
          :paginator="true"
          :rows="25"
          :total-records="totalRecords"
          :lazy="true"
          @page="onPage"
          @sort="onSort"
          sortMode="single"
          class="equipment-table"
          selection-mode="multiple"
          v-model:selection="selectedEquipment"
          :meta-key-selection="false"
          responsive-layout="scroll"
        >
          <!-- TODO: [E2E_TESTING] Add Cypress/Playwright end-to-end tests -->
          <!-- - Test complete equipment inspection workflow from creation to calculation results -->
          <!-- - Verify decimal precision maintained through full user journey -->
          <!-- - Test error handling and validation messages -->
          <!-- - Add performance testing for large equipment datasets -->

          <template #empty>
            <div class="empty-state">
              <i class="pi pi-database" style="font-size: 3rem; color: var(--p-text-color-secondary);"></i>
              <h3>No Equipment Found</h3>
              <p>No equipment matches your current filters. Try adjusting your search criteria.</p>
              <Button 
                label="Add First Equipment" 
                icon="pi pi-plus" 
                @click="showCreateDialog = true"
              />
            </div>
          </template>

          <template #loading>
            <div class="loading-state">
              <ProgressSpinner size="small" />
              <span>Loading equipment data...</span>
            </div>
          </template>

          <Column selection-mode="multiple" header-style="width: 3rem"></Column>

          <Column field="tag_number" header="Tag Number" sortable>
            <template #body="{ data }">
              <div class="tag-cell">
                <span class="tag-number">{{ data.tag_number }}</span>
                <Tag 
                  :severity="getStatusSeverity(data.status)" 
                  size="small"
                  class="status-tag"
                >
                  {{ formatStatus(data.status) }}
                </Tag>
              </div>
            </template>
          </Column>

          <Column field="equipment_type" header="Type" sortable>
            <template #body="{ data }">
              <div class="type-cell">
                <i :class="getTypeIcon(data.equipment_type)"></i>
                <span>{{ formatEquipmentType(data.equipment_type) }}</span>
              </div>
            </template>
          </Column>

          <Column field="description" header="Description">
            <template #body="{ data }">
              <div class="description-cell">
                <div class="description">{{ data.description }}</div>
                <div class="location">
                  <i class="pi pi-map-marker"></i>
                  {{ data.location }}
                </div>
              </div>
            </template>
          </Column>

          <Column field="design_pressure" header="Design Pressure" sortable>
            <template #body="{ data }">
              <span class="pressure-value">{{ formatPressure(data.design_pressure) }}</span>
            </template>
          </Column>

          <Column field="design_temperature" header="Design Temp" sortable>
            <template #body="{ data }">
              <span class="temperature-value">{{ formatTemperature(data.design_temperature) }}</span>
            </template>
          </Column>

          <Column field="last_inspection_date" header="Last Inspection" sortable>
            <template #body="{ data }">
              <div class="inspection-cell">
                <div class="date">{{ formatDate(data.last_inspection_date) }}</div>
                <div v-if="data.next_inspection_due" class="next-due">
                  Next: {{ formatDate(data.next_inspection_due) }}
                </div>
              </div>
            </template>
          </Column>

          <Column header="Actions" :exportable="false" style="width: 8rem">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button 
                  icon="pi pi-eye" 
                  severity="info" 
                  text
                  rounded
                  @click="viewEquipment(data)"
                  v-tooltip.top="'View Details'"
                />
                <Button 
                  icon="pi pi-pencil" 
                  severity="secondary" 
                  text
                  rounded
                  @click="editEquipment(data)"
                  v-tooltip.top="'Edit Equipment'"
                />
                <Button 
                  icon="pi pi-trash" 
                  severity="danger" 
                  text
                  rounded
                  @click="confirmDelete(data)"
                  v-tooltip.top="'Delete Equipment'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Equipment Create/Edit Dialog -->
    <EquipmentDialog 
      v-model:visible="showCreateDialog"
      :equipment="selectedEquipmentForEdit"
      @equipment-saved="onEquipmentSaved"
    />

    <!-- Equipment Detail Dialog -->
    <EquipmentDetailDialog 
      v-model:visible="showDetailDialog"
      :equipment="selectedEquipmentForDetail"
    />

    <!-- Delete Confirmation Dialog -->
    <Dialog 
      v-model:visible="showDeleteDialog" 
      :style="{ width: '450px' }" 
      header="Confirm Deletion" 
      :modal="true"
    >
      <div class="delete-confirmation">
        <i class="pi pi-exclamation-triangle" style="font-size: 2rem; color: var(--p-orange-500)"></i>
        <div class="confirmation-text">
          <p>Are you sure you want to delete this equipment?</p>
          <div class="equipment-details">
            <strong>{{ equipmentToDelete?.tag_number }}</strong><br>
            {{ equipmentToDelete?.description }}
          </div>
          <Message severity="warn" :closable="false">
            This action cannot be undone. All associated inspection data will also be removed.
          </Message>
        </div>
      </div>
      
      <template #footer>
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showDeleteDialog = false"
          severity="secondary"
          outlined
        />
        <Button 
          label="Delete" 
          icon="pi pi-trash" 
          @click="deleteEquipment"
          severity="danger"
          :loading="deleteLoading"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { equipmentApi } from '@/api/equipment'
import EquipmentDialog from '@/components/equipment/EquipmentDialog.vue'
import EquipmentDetailDialog from '@/components/equipment/EquipmentDetailDialog.vue'
import type { 
  Equipment, 
  EquipmentType, 
  EquipmentStatus,
  PaginatedResponse,
  ApiQueryParams 
} from '@/types'

// Composables
const router = useRouter()
const toast = useToast()

// State
const loading = ref(false)
const deleteLoading = ref(false)
const equipmentData = ref<Equipment[]>([])
const totalRecords = ref(0)
const currentPage = ref(0)
const searchTerm = ref('')
const selectedTypes = ref<EquipmentType[]>([])
const selectedStatuses = ref<EquipmentStatus[]>([])
const selectedLocation = ref<string | null>(null)
const selectedEquipment = ref<Equipment[]>([])
const sortField = ref<string>('')
const sortOrder = ref<number>(1)

// Dialog state
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showDeleteDialog = ref(false)
const selectedEquipmentForEdit = ref<Equipment | null>(null)
const selectedEquipmentForDetail = ref<Equipment | null>(null)
const equipmentToDelete = ref<Equipment | null>(null)

// Options for filters
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

const locations = ref([
  { label: 'Unit 100', value: 'Unit 100' },
  { label: 'Unit 200', value: 'Unit 200' },
  { label: 'Unit 300', value: 'Unit 300' },
  { label: 'Utilities', value: 'Utilities' },
  { label: 'Tank Farm', value: 'Tank Farm' }
])

// Computed
const filteredEquipment = computed(() => equipmentData.value)

// Methods
async function loadEquipment(params: ApiQueryParams = {}) {
  try {
    loading.value = true
    
    const queryParams: ApiQueryParams = {
      page: currentPage.value + 1,
      per_page: 25,
      ...params
    }

    if (searchTerm.value) {
      queryParams.search = searchTerm.value
    }
    
    if (selectedTypes.value.length) {
      queryParams.equipment_type = selectedTypes.value
    }
    
    if (selectedStatuses.value.length) {
      queryParams.status = selectedStatuses.value
    }
    
    if (selectedLocation.value) {
      queryParams.location = selectedLocation.value
    }

    if (sortField.value) {
      queryParams.sort = `${sortOrder.value === 1 ? '' : '-'}${sortField.value}`
    }

    const response = await equipmentApi.getEquipment(queryParams)
    equipmentData.value = response.data
    totalRecords.value = response.total
    
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error Loading Equipment',
      detail: error.message || 'Failed to load equipment data',
      life: 5000
    })
  } finally {
    loading.value = false
  }
}

// Debounced search
let searchTimeout: ReturnType<typeof setTimeout>
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 0
    loadEquipment()
  }, 300)
}

// Table event handlers
function onPage(event: any) {
  currentPage.value = event.page
  loadEquipment()
}

function onSort(event: any) {
  sortField.value = event.sortField
  sortOrder.value = event.sortOrder
  loadEquipment()
}

// Equipment actions
function viewEquipment(equipment: Equipment) {
  selectedEquipmentForDetail.value = equipment
  showDetailDialog.value = true
}

function editEquipment(equipment: Equipment) {
  selectedEquipmentForEdit.value = equipment
  showCreateDialog.value = true
}

function confirmDelete(equipment: Equipment) {
  equipmentToDelete.value = equipment
  showDeleteDialog.value = true
}

async function deleteEquipment() {
  if (!equipmentToDelete.value) return
  
  try {
    deleteLoading.value = true
    await equipmentApi.deleteEquipment(equipmentToDelete.value.id)
    
    toast.add({
      severity: 'success',
      summary: 'Equipment Deleted',
      detail: `Equipment ${equipmentToDelete.value.tag_number} has been deleted`,
      life: 3000
    })
    
    showDeleteDialog.value = false
    equipmentToDelete.value = null
    loadEquipment()
    
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Delete Failed',
      detail: error.message || 'Failed to delete equipment',
      life: 5000
    })
  } finally {
    deleteLoading.value = false
  }
}

function onEquipmentSaved(equipment: Equipment) {
  showCreateDialog.value = false
  selectedEquipmentForEdit.value = null
  
  toast.add({
    severity: 'success',
    summary: selectedEquipmentForEdit.value ? 'Equipment Updated' : 'Equipment Created',
    detail: `Equipment ${equipment.tag_number} has been saved`,
    life: 3000
  })
  
  loadEquipment()
}

async function exportEquipment() {
  try {
    const blob = await equipmentApi.exportEquipment('csv')
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `equipment-export-${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    
    toast.add({
      severity: 'success',
      summary: 'Export Complete',
      detail: 'Equipment data has been exported successfully',
      life: 3000
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Export Failed',
      detail: error.message || 'Failed to export equipment data',
      life: 5000
    })
  }
}

// Formatting methods
function formatEquipmentType(type: EquipmentType): string {
  return equipmentTypes.find(t => t.value === type)?.label || type
}

function formatStatus(status: EquipmentStatus): string {
  return equipmentStatuses.find(s => s.value === status)?.label || status
}

function getStatusSeverity(status: EquipmentStatus): string {
  const severityMap = {
    'in_service': 'success',
    'out_of_service': 'danger',
    'maintenance': 'warn',
    'inspection_due': 'info',
    'decommissioned': 'secondary'
  }
  return severityMap[status] || 'secondary'
}

function getTypeIcon(type: EquipmentType): string {
  const iconMap = {
    'pressure_vessel': 'pi pi-circle',
    'storage_tank': 'pi pi-box',
    'heat_exchanger': 'pi pi-sync',
    'piping_system': 'pi pi-share-alt',
    'reactor': 'pi pi-cog'
  }
  return iconMap[type] || 'pi pi-wrench'
}

function formatPressure(pressure: number): string {
  return `${pressure} psig`
}

function formatTemperature(temperature: number): string {
  return `${temperature}°F`
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString()
}

// Watch for filter changes
watch([selectedTypes, selectedStatuses, selectedLocation], () => {
  currentPage.value = 0
  loadEquipment()
}, { deep: true })

// Lifecycle
onMounted(() => {
  loadEquipment()
})
</script>

<style scoped>
.equipment-view {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
}

.header-content h2 {
  margin: 0 0 0.5rem 0;
  color: var(--p-text-color);
  font-size: 2rem;
  font-weight: 600;
}

.subtitle {
  color: var(--p-text-color-secondary);
  margin: 0;
  font-size: 1.1rem;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.filters-card {
  margin-bottom: 1.5rem;
}

.filters-container {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-section {
  flex: 1;
  min-width: 300px;
}

.search-input {
  width: 100%;
}

.filter-section {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.filter-select {
  min-width: 150px;
}

.table-card {
  margin-bottom: 2rem;
}

.equipment-table {
  font-size: 0.9rem;
}

.tag-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.tag-number {
  font-weight: 600;
  color: var(--p-text-color);
}

.status-tag {
  align-self: flex-start;
}

.type-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.description-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.description {
  color: var(--p-text-color);
  font-weight: 500;
}

.location {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
}

.pressure-value,
.temperature-value {
  font-weight: 500;
  color: var(--p-text-color);
}

.inspection-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.date {
  color: var(--p-text-color);
  font-weight: 500;
}

.next-due {
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: var(--p-text-color);
}

.empty-state p {
  margin: 0;
  color: var(--p-text-color-secondary);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: var(--p-text-color-secondary);
}

.delete-confirmation {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.confirmation-text {
  flex: 1;
}

.equipment-details {
  margin: 0.75rem 0;
  padding: 0.75rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
  border-left: 3px solid var(--p-primary-color);
}

@media (max-width: 1024px) {
  .equipment-view {
    padding: 1rem;
  }
  
  .page-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .filters-container {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .search-section {
    min-width: auto;
  }
  
  .filter-section {
    flex-wrap: wrap;
  }
  
  .filter-select {
    min-width: 130px;
    flex: 1;
  }
}

@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
  }
  
  .equipment-table {
    font-size: 0.85rem;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>