<template>
  <div class="home-view">
    <div class="dashboard-header">
      <h2>Mechanical Integrity Dashboard</h2>
      <p class="subtitle">Safety-critical equipment inspection and API 579 compliance monitoring</p>
    </div>

    <div class="dashboard-grid">
      <!-- Quick Actions -->
      <Card class="quick-actions-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-bolt"></i>
            Quick Actions
          </div>
        </template>
        <template #content>
          <div class="action-buttons">
            <Button 
              label="New Inspection" 
              icon="pi pi-wrench" 
              @click="$router.push('/inspections')"
              class="action-button"
              severity="primary"
            />
            <Button 
              label="Equipment Registry" 
              icon="pi pi-database" 
              @click="$router.push('/equipment')"
              class="action-button"
              severity="secondary"
            />
            <Button 
              label="Generate Report" 
              icon="pi pi-file-pdf" 
              class="action-button"
              severity="info"
              disabled
            />
          </div>
        </template>
      </Card>

      <!-- System Status -->
      <Card class="status-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-shield"></i>
            System Status
          </div>
        </template>
        <template #content>
          <div class="status-items">
            <div class="status-item">
              <Tag severity="success" icon="pi pi-check">
                API 579 Engine: Online
              </Tag>
            </div>
            <div class="status-item">
              <Tag severity="success" icon="pi pi-check">
                Database: Connected
              </Tag>
            </div>
            <div class="status-item">
              <Tag severity="info" icon="pi pi-info-circle">
                Last Sync: 2 minutes ago
              </Tag>
            </div>
          </div>
        </template>
      </Card>

      <!-- Recent Activity -->
      <Card class="activity-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-clock"></i>
            Recent Activity
          </div>
        </template>
        <template #content>
          <div class="activity-list">
            <div class="activity-item">
              <div class="activity-icon">
                <i class="pi pi-wrench"></i>
              </div>
              <div class="activity-content">
                <div class="activity-title">Inspection Form Ready</div>
                <div class="activity-description">Professional inspection data entry forms with API 579 validation</div>
                <div class="activity-time">Just now</div>
              </div>
            </div>
            <div class="activity-item">
              <div class="activity-icon">
                <i class="pi pi-cog"></i>
              </div>
              <div class="activity-content">
                <div class="activity-title">System Initialization</div>
                <div class="activity-description">Frontend application configured with PrimeVue components</div>
                <div class="activity-time">5 minutes ago</div>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Equipment Summary -->
      <EquipmentSummary @view-all="handleViewEquipment" />
    </div>

    <!-- Getting Started -->
    <Card class="getting-started">
      <template #title>
        <div class="card-title">
          <i class="pi pi-info-circle"></i>
          Getting Started
        </div>
      </template>
      <template #content>
        <div class="getting-started-content">
          <p>Welcome to the Mechanical Integrity Management System. This application provides:</p>
          <ul>
            <li><strong>Inspection Forms:</strong> Professional data entry with safety-critical validation</li>
            <li><strong>API 579 Compliance:</strong> Automated fitness-for-service calculations</li>
            <li><strong>Equipment Registry:</strong> Comprehensive asset management (coming soon)</li>
            <li><strong>Audit Trail:</strong> Complete traceability for regulatory compliance</li>
          </ul>
          <Message severity="info" :closable="false">
            <template #messageicon>
              <i class="pi pi-lightbulb"></i>
            </template>
            Start by creating a new inspection using the "New Inspection" button above.
          </Message>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import EquipmentSummary from '@/components/dashboard/EquipmentSummary.vue'

const router = useRouter()

function handleViewEquipment() {
  router.push('/equipment')
}
</script>

<style scoped>
.home-view {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  margin-bottom: 2rem;
}

.dashboard-header h2 {
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

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color);
}

.quick-actions-card .action-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.action-button {
  justify-content: flex-start;
}

.status-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.activity-item {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.activity-icon {
  width: 2.5rem;
  height: 2.5rem;
  background: var(--p-primary-50);
  color: var(--p-primary-500);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
}

.activity-title {
  font-weight: 600;
  color: var(--p-text-color);
  margin-bottom: 0.25rem;
}

.activity-description {
  color: var(--p-text-color-secondary);
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.activity-time {
  color: var(--p-text-color-secondary);
  font-size: 0.8rem;
}


.getting-started {
  grid-column: 1 / -1;
}

.getting-started-content ul {
  margin: 1rem 0;
  padding-left: 1.5rem;
}

.getting-started-content li {
  margin-bottom: 0.5rem;
  color: var(--p-text-color-secondary);
}

@media (max-width: 768px) {
  .home-view {
    padding: 1rem;
  }
  
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
  
  
  .dashboard-header h2 {
    font-size: 1.5rem;
  }
}
</style>
