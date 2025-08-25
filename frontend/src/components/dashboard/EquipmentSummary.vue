<template>
  <div class="equipment-summary">
    <Card>
      <template #title>
        <div class="summary-header">
          <div class="title-section">
            <i class="pi pi-database"></i>
            <span>Equipment Registry</span>
          </div>
          <Button 
            label="View All" 
            icon="pi pi-external-link" 
            severity="secondary" 
            size="small"
            outlined
            @click="$emit('view-all')"
          />
        </div>
      </template>
      
      <template #content>
        <div v-if="loading" class="loading-state">
          <ProgressSpinner size="small" />
          <span>Loading equipment data...</span>
        </div>
        
        <div v-else-if="error" class="error-state">
          <Message severity="error" :closable="false">
            <template #messageicon>
              <i class="pi pi-times-circle"></i>
            </template>
            {{ error }}
          </Message>
        </div>
        
        <div v-else class="summary-content">
          <!-- Equipment Statistics -->
          <div class="stats-grid">
            <div class="stat-card total">
              <div class="stat-icon">
                <i class="pi pi-database"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ totalEquipment }}</div>
                <div class="stat-label">Total Equipment</div>
              </div>
            </div>
            
            <div class="stat-card active">
              <div class="stat-icon">
                <i class="pi pi-play-circle"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ activeEquipment }}</div>
                <div class="stat-label">Active</div>
              </div>
            </div>
            
            <div class="stat-card maintenance">
              <div class="stat-icon">
                <i class="pi pi-wrench"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ maintenanceEquipment }}</div>
                <div class="stat-label">Maintenance</div>
              </div>
            </div>
            
            <div class="stat-card overdue">
              <div class="stat-icon">
                <i class="pi pi-exclamation-triangle"></i>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ overdueInspections }}</div>
                <div class="stat-label">Overdue</div>
              </div>
            </div>
          </div>

          <!-- Equipment by Type Chart -->
          <div class="equipment-types">
            <h4>Equipment by Type</h4>
            <div class="type-list">
              <div 
                v-for="type in equipmentByType" 
                :key="type.type"
                class="type-item"
              >
                <div class="type-info">
                  <div class="type-name">{{ formatEquipmentType(type.type) }}</div>
                  <div class="type-count">{{ type.count }} units</div>
                </div>
                <div class="type-bar">
                  <div 
                    class="type-progress" 
                    :style="{ width: `${(type.count / totalEquipment) * 100}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Recent Equipment Activity -->
          <div class="recent-activity">
            <h4>Recent Activity</h4>
            <div v-if="recentEquipment.length === 0" class="no-activity">
              <Message severity="info" :closable="false">
                <template #messageicon>
                  <i class="pi pi-info-circle"></i>
                </template>
                No recent equipment activity.
              </Message>
            </div>
            <div v-else class="activity-list">
              <div 
                v-for="equipment in recentEquipment" 
                :key="equipment.id"
                class="activity-item"
              >
                <div class="equipment-info">
                  <div class="equipment-tag">{{ equipment.tag_number }}</div>
                  <div class="equipment-desc">{{ equipment.description }}</div>
                  <div class="equipment-meta">
                    <span class="location">{{ equipment.location }}</span>
                    <Tag 
                      :severity="getStatusSeverity(equipment.status)" 
                      size="small"
                    >
                      {{ formatStatus(equipment.status) }}
                    </Tag>
                  </div>
                </div>
                <div class="next-inspection">
                  <div class="inspection-date">
                    {{ formatDate(equipment.next_inspection_due) }}
                  </div>
                  <div class="inspection-label">Next Inspection</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { equipmentApi } from '@/api/equipment'
import type { Equipment, EquipmentType, EquipmentStatus } from '@/types'

interface EquipmentTypeCount {
  type: EquipmentType
  count: number
}

// Define emits
defineEmits<{
  'view-all': []
}>()

// State
const equipmentData = ref<Equipment[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Computed properties
const totalEquipment = computed(() => equipmentData.value.length)

const activeEquipment = computed(() => 
  equipmentData.value.filter(eq => eq.status === 'in_service').length
)

const maintenanceEquipment = computed(() => 
  equipmentData.value.filter(eq => eq.status === 'maintenance').length
)

const overdueInspections = computed(() => {
  const today = new Date()
  return equipmentData.value.filter(eq => {
    if (!eq.next_inspection_due) return false
    return new Date(eq.next_inspection_due) < today
  }).length
})

const equipmentByType = computed(() => {
  const typeMap = new Map<EquipmentType, number>()
  
  equipmentData.value.forEach(equipment => {
    const count = typeMap.get(equipment.equipment_type) || 0
    typeMap.set(equipment.equipment_type, count + 1)
  })
  
  return Array.from(typeMap.entries())
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
})

const recentEquipment = computed(() => {
  return equipmentData.value
    .slice()
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 5)
})

// Methods
async function loadEquipmentData() {
  try {
    loading.value = true
    error.value = null
    
    const response = await equipmentApi.getEquipment({ per_page: 1000 })
    equipmentData.value = response.data
    
  } catch (err: any) {
    error.value = err.message || 'Failed to load equipment data'
    console.error('Error loading equipment:', err)
  } finally {
    loading.value = false
  }
}

function formatEquipmentType(type: EquipmentType): string {
  const typeMap: Record<EquipmentType, string> = {
    [EquipmentType.PRESSURE_VESSEL]: 'Pressure Vessels',
    [EquipmentType.STORAGE_TANK]: 'Storage Tanks',
    [EquipmentType.HEAT_EXCHANGER]: 'Heat Exchangers',
    [EquipmentType.PIPING_SYSTEM]: 'Piping Systems',
    [EquipmentType.REACTOR]: 'Reactors'
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

function formatDate(dateString: string | null): string {
  if (!dateString) return 'Not scheduled'
  
  const date = new Date(dateString)
  const now = new Date()
  
  // Check if overdue
  if (date < now) {
    const daysOverdue = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))
    return `${daysOverdue} days overdue`
  }
  
  return date.toLocaleDateString()
}

// Lifecycle
onMounted(() => {
  loadEquipmentData()
})
</script>

<style scoped>
.equipment-summary {
  height: 100%;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color);
}

.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
}

.loading-state {
  color: var(--p-text-color-secondary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: var(--p-border-radius);
  border: 1px solid var(--p-surface-border);
  background: var(--p-surface-card);
}

.stat-card.total {
  border-left: 4px solid var(--p-primary-color);
}

.stat-card.active {
  border-left: 4px solid var(--p-green-500);
}

.stat-card.maintenance {
  border-left: 4px solid var(--p-orange-500);
}

.stat-card.overdue {
  border-left: 4px solid var(--p-red-500);
}

.stat-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--p-surface-100);
  color: var(--p-text-color-secondary);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.stat-label {
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
}

.equipment-types,
.recent-activity {
  margin-top: 2rem;
}

.equipment-types h4,
.recent-activity h4 {
  margin: 0 0 1rem 0;
  color: var(--p-text-color);
  font-size: 1.1rem;
  font-weight: 600;
}

.type-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.type-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.type-info {
  flex: 0 0 180px;
}

.type-name {
  font-weight: 500;
  color: var(--p-text-color);
}

.type-count {
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
}

.type-bar {
  flex: 1;
  height: 8px;
  background: var(--p-surface-200);
  border-radius: 4px;
  overflow: hidden;
}

.type-progress {
  height: 100%;
  background: var(--p-primary-color);
  transition: width 0.3s ease;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem;
  border: 1px solid var(--p-surface-border);
  border-radius: var(--p-border-radius);
  background: var(--p-surface-card);
}

.equipment-info {
  flex: 1;
}

.equipment-tag {
  font-weight: 600;
  color: var(--p-text-color);
  margin-bottom: 0.25rem;
}

.equipment-desc {
  color: var(--p-text-color-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.equipment-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.location {
  font-size: 0.85rem;
  color: var(--p-text-color-secondary);
}

.next-inspection {
  text-align: right;
  flex-shrink: 0;
}

.inspection-date {
  font-weight: 500;
  color: var(--p-text-color);
}

.inspection-label {
  font-size: 0.8rem;
  color: var(--p-text-color-secondary);
}

@media (max-width: 768px) {
  .summary-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .type-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  .type-info {
    flex: none;
  }
  
  .type-bar {
    width: 100%;
  }
  
  .activity-item {
    flex-direction: column;
    gap: 1rem;
  }
  
  .next-inspection {
    text-align: left;
    width: 100%;
  }
}
</style>