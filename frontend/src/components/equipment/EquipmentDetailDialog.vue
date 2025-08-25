<template>
  <Dialog 
    v-model:visible="dialogVisible" 
    :style="{ width: '900px', maxWidth: '95vw' }" 
    :header="dialogTitle"
    :modal="true"
    class="equipment-detail-dialog"
  >
    <div v-if="equipment" class="equipment-details">
      <!-- Header Section -->
      <div class="detail-header">
        <div class="equipment-title">
          <h3>{{ equipment.tag_number }}</h3>
          <Tag 
            :severity="getStatusSeverity(equipment.status)" 
            size="large"
            class="status-badge"
          >
            {{ formatStatus(equipment.status) }}
          </Tag>
        </div>
        <div class="equipment-type">
          <i :class="getTypeIcon(equipment.equipment_type)"></i>
          <span>{{ formatEquipmentType(equipment.equipment_type) }}</span>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="quick-stats">
        <div class="stat-item">
          <div class="stat-label">Design Pressure</div>
          <div class="stat-value">{{ formatPressure(equipment.design_pressure) }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Design Temperature</div>
          <div class="stat-value">{{ formatTemperature(equipment.design_temperature) }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Design Thickness</div>
          <div class="stat-value">{{ formatThickness(equipment.design_thickness) }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Corr. Allowance</div>
          <div class="stat-value">{{ formatThickness(equipment.corrosion_allowance) }}</div>
        </div>
      </div>

      <!-- Detail Tabs -->
      <TabView class="detail-tabs">
        <!-- General Information Tab -->
        <TabPanel value="0" header="General Information">
          <div class="tab-content">
            <div class="info-grid">
              <div class="info-section">
                <h4>Equipment Details</h4>
                <div class="info-list">
                  <div class="info-item">
                    <span class="info-label">Tag Number:</span>
                    <span class="info-value">{{ equipment.tag_number }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Description:</span>
                    <span class="info-value">{{ equipment.description }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Equipment Type:</span>
                    <span class="info-value">{{ formatEquipmentType(equipment.equipment_type) }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Location:</span>
                    <span class="info-value">
                      <i class="pi pi-map-marker"></i>
                      {{ equipment.location }}
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Service Fluid:</span>
                    <span class="info-value">{{ equipment.service_fluid || 'Not specified' }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Material Specification:</span>
                    <span class="info-value">{{ equipment.material_specification }}</span>
                  </div>
                </div>
              </div>

              <div class="info-section">
                <h4>Installation & Status</h4>
                <div class="info-list">
                  <div class="info-item">
                    <span class="info-label">Installation Date:</span>
                    <span class="info-value">{{ formatDate(equipment.installation_date) }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Age:</span>
                    <span class="info-value">{{ calculateAge(equipment.installation_date) }} years</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Current Status:</span>
                    <span class="info-value">
                      <Tag :severity="getStatusSeverity(equipment.status)" size="small">
                        {{ formatStatus(equipment.status) }}
                      </Tag>
                    </span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Last Updated:</span>
                    <span class="info-value">{{ formatDateTime(equipment.updated_at) }}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Created:</span>
                    <span class="info-value">{{ formatDateTime(equipment.created_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabPanel>

        <!-- Design Parameters Tab -->
        <TabPanel value="1" header="Design Parameters">
          <div class="tab-content">
            <div class="parameters-grid">
              <Card class="parameter-card">
                <template #title>
                  <div class="card-header">
                    <i class="pi pi-cog"></i>
                    <span>Pressure & Temperature</span>
                  </div>
                </template>
                <template #content>
                  <div class="parameter-list">
                    <div class="parameter-item">
                      <span class="param-label">Design Pressure</span>
                      <span class="param-value highlight">{{ formatPressure(equipment.design_pressure) }}</span>
                    </div>
                    <div class="parameter-item">
                      <span class="param-label">Design Temperature</span>
                      <span class="param-value highlight">{{ formatTemperature(equipment.design_temperature) }}</span>
                    </div>
                  </div>
                </template>
              </Card>

              <Card class="parameter-card">
                <template #title>
                  <div class="card-header">
                    <i class="pi pi-circle"></i>
                    <span>Thickness Parameters</span>
                  </div>
                </template>
                <template #content>
                  <div class="parameter-list">
                    <div class="parameter-item">
                      <span class="param-label">Design Thickness</span>
                      <span class="param-value highlight">{{ formatThickness(equipment.design_thickness) }}</span>
                    </div>
                    <div class="parameter-item">
                      <span class="param-label">Corrosion Allowance</span>
                      <span class="param-value highlight">{{ formatThickness(equipment.corrosion_allowance) }}</span>
                    </div>
                    <div class="parameter-item">
                      <span class="param-label">Minimum Thickness</span>
                      <span class="param-value warning">
                        {{ formatThickness(equipment.design_thickness - equipment.corrosion_allowance) }}
                      </span>
                    </div>
                  </div>
                </template>
              </Card>

              <Card class="parameter-card material-card">
                <template #title>
                  <div class="card-header">
                    <i class="pi pi-wrench"></i>
                    <span>Material Properties</span>
                  </div>
                </template>
                <template #content>
                  <div class="parameter-list">
                    <div class="parameter-item">
                      <span class="param-label">Material Specification</span>
                      <span class="param-value">{{ equipment.material_specification }}</span>
                    </div>
                    <div class="parameter-item">
                      <span class="param-label">Material Class</span>
                      <span class="param-value">{{ getMaterialClass(equipment.material_specification) }}</span>
                    </div>
                  </div>
                </template>
              </Card>
            </div>
          </div>
        </TabPanel>

        <!-- Inspection History Tab -->
        <TabPanel value="2" header="Inspection History">
          <div class="tab-content">
            <div class="inspection-summary">
              <div class="summary-cards">
                <div class="summary-card">
                  <div class="summary-icon">
                    <i class="pi pi-calendar-check"></i>
                  </div>
                  <div class="summary-content">
                    <div class="summary-value">{{ formatDate(equipment.last_inspection_date || null) }}</div>
                    <div class="summary-label">Last Inspection</div>
                  </div>
                </div>
                <div class="summary-card">
                  <div class="summary-icon next-due">
                    <i class="pi pi-calendar-clock"></i>
                  </div>
                  <div class="summary-content">
                    <div class="summary-value">{{ formatDate(equipment.next_inspection_due || null) }}</div>
                    <div class="summary-label">Next Due</div>
                  </div>
                </div>
                <div class="summary-card">
                  <div class="summary-icon" :class="getInspectionStatusClass(equipment)">
                    <i class="pi pi-info-circle"></i>
                  </div>
                  <div class="summary-content">
                    <div class="summary-value">{{ getInspectionStatus(equipment) }}</div>
                    <div class="summary-label">Status</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Inspection Actions -->
            <div class="inspection-actions">
              <Button 
                label="View Inspection History" 
                icon="pi pi-history" 
                @click="navigateToInspections"
                severity="secondary"
                outlined
              />
              <Button 
                label="Schedule New Inspection" 
                icon="pi pi-plus" 
                @click="scheduleInspection"
                severity="primary"
              />
            </div>

            <!-- Placeholder for inspection history -->
            <div class="inspection-placeholder">
              <Message severity="info" :closable="false">
                <template #messageicon>
                  <i class="pi pi-info-circle"></i>
                </template>
                Detailed inspection history will be available once the inspection management module is implemented.
              </Message>
            </div>
          </div>
        </TabPanel>
      </TabView>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <Button 
          label="Edit Equipment" 
          icon="pi pi-pencil" 
          @click="editEquipment"
          severity="secondary"
        />
        <Button 
          label="Close" 
          icon="pi pi-times" 
          @click="dialogVisible = false"
          severity="primary"
          outlined
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Equipment, EquipmentType, EquipmentStatus } from '@/types'

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
  'edit-equipment': [equipment: Equipment]
}>()

// Composables
const router = useRouter()

// Computed
const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const dialogTitle = computed(() => 
  props.equipment ? `Equipment Details - ${props.equipment.tag_number}` : 'Equipment Details'
)

// Methods
function formatEquipmentType(type: EquipmentType): string {
  const typeMap = {
    'pressure_vessel': 'Pressure Vessel',
    'storage_tank': 'Storage Tank',
    'heat_exchanger': 'Heat Exchanger',
    'piping_system': 'Piping System',
    'reactor': 'Reactor'
  }
  return typeMap[type] || type
}

function formatStatus(status: EquipmentStatus): string {
  const statusMap = {
    'in_service': 'In Service',
    'out_of_service': 'Out of Service',
    'maintenance': 'Maintenance',
    'inspection_due': 'Inspection Due',
    'decommissioned': 'Decommissioned'
  }
  return statusMap[status] || status
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
  return `${pressure.toLocaleString()} psig`
}

function formatTemperature(temperature: number): string {
  return `${temperature.toLocaleString()}°F`
}

function formatThickness(thickness: number): string {
  return `${thickness.toFixed(3)}" `
}

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Not specified'
  return new Date(dateString).toLocaleDateString()
}

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString()
}

function calculateAge(installationDate: string): string {
  const installed = new Date(installationDate)
  const now = new Date()
  const ageInYears = (now.getTime() - installed.getTime()) / (1000 * 60 * 60 * 24 * 365.25)
  return ageInYears.toFixed(1)
}

function getMaterialClass(materialSpec: string): string {
  if (materialSpec.includes('SA-516')) return 'Carbon Steel'
  if (materialSpec.includes('SA-240')) return 'Stainless Steel'
  if (materialSpec.includes('SA-106')) return 'Carbon Steel Pipe'
  if (materialSpec.includes('SA-312')) return 'Stainless Steel Pipe'
  if (materialSpec.includes('Inconel')) return 'Nickel Alloy'
  if (materialSpec.includes('Hastelloy')) return 'Nickel Alloy'
  return 'See Specification'
}

function getInspectionStatus(equipment: Equipment): string {
  if (!equipment.next_inspection_due) return 'Not Scheduled'
  
  const today = new Date()
  const dueDate = new Date(equipment.next_inspection_due)
  
  if (dueDate < today) {
    const daysOverdue = Math.floor((today.getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24))
    return `${daysOverdue} days overdue`
  }
  
  const daysUntilDue = Math.floor((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  if (daysUntilDue <= 30) return `Due in ${daysUntilDue} days`
  
  return 'Current'
}

function getInspectionStatusClass(equipment: Equipment): string {
  if (!equipment.next_inspection_due) return 'info'
  
  const today = new Date()
  const dueDate = new Date(equipment.next_inspection_due)
  
  if (dueDate < today) return 'overdue'
  
  const daysUntilDue = Math.floor((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  if (daysUntilDue <= 30) return 'warning'
  
  return 'success'
}

function editEquipment() {
  if (props.equipment) {
    emit('edit-equipment', props.equipment)
  }
}

function navigateToInspections() {
  if (props.equipment) {
    router.push(`/inspections?equipment=${props.equipment.id}`)
  }
}

function scheduleInspection() {
  if (props.equipment) {
    router.push(`/inspections/new?equipment=${props.equipment.id}`)
  }
}
</script>

<style scoped>
.equipment-detail-dialog {
  font-size: 0.9rem;
}

.equipment-details {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
  border-left: 4px solid var(--p-primary-color);
}

.equipment-title {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.equipment-title h3 {
  margin: 0;
  color: var(--p-text-color);
  font-size: 1.5rem;
  font-weight: 700;
}

.status-badge {
  font-size: 0.9rem;
}

.equipment-type {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color-secondary);
  font-weight: 500;
}

.quick-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: var(--p-surface-card);
  border: 1px solid var(--p-surface-border);
  border-radius: var(--p-border-radius);
  text-align: center;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.detail-tabs {
  margin-top: 1rem;
}

.tab-content {
  padding: 1rem 0;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.info-section h4 {
  margin: 0 0 1rem 0;
  color: var(--p-text-color);
  font-size: 1.1rem;
  font-weight: 600;
  border-bottom: 1px solid var(--p-surface-border);
  padding-bottom: 0.5rem;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.info-label {
  font-weight: 500;
  color: var(--p-text-color-secondary);
  flex-shrink: 0;
  min-width: 120px;
}

.info-value {
  color: var(--p-text-color);
  text-align: right;
  word-break: break-word;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  justify-content: flex-end;
}

.parameters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.parameter-card {
  border: 1px solid var(--p-surface-border);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color);
}

.parameter-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.parameter-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  color: var(--p-text-color-secondary);
  font-weight: 500;
}

.param-value {
  color: var(--p-text-color);
  font-weight: 600;
}

.param-value.highlight {
  color: var(--p-primary-color);
  font-size: 1.1rem;
}

.param-value.warning {
  color: var(--p-orange-500);
  font-weight: 700;
}

.material-card {
  grid-column: 1 / -1;
}

.inspection-summary {
  margin-bottom: 2rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--p-surface-card);
  border: 1px solid var(--p-surface-border);
  border-radius: var(--p-border-radius);
}

.summary-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--p-primary-50);
  color: var(--p-primary-500);
  font-size: 1.25rem;
}

.summary-icon.next-due {
  background: var(--p-blue-50);
  color: var(--p-blue-500);
}

.summary-icon.success {
  background: var(--p-green-50);
  color: var(--p-green-500);
}

.summary-icon.warning {
  background: var(--p-orange-50);
  color: var(--p-orange-500);
}

.summary-icon.overdue {
  background: var(--p-red-50);
  color: var(--p-red-500);
}

.summary-content {
  flex: 1;
}

.summary-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin-bottom: 0.25rem;
}

.summary-label {
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
}

.inspection-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  margin: 2rem 0;
}

.inspection-placeholder {
  margin-top: 2rem;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

@media (max-width: 768px) {
  .equipment-detail-dialog {
    width: 95vw !important;
    margin: 0.5rem;
  }
  
  .detail-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .equipment-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .quick-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .info-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .parameters-grid {
    grid-template-columns: 1fr;
  }
  
  .summary-cards {
    grid-template-columns: 1fr;
  }
  
  .inspection-actions {
    flex-direction: column;
  }
  
  .dialog-footer {
    flex-direction: column;
  }
}
</style>