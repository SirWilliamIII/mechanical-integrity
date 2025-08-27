<!--
  API579Results - Professional component for displaying safety-critical calculation results
  Features:
  - Displays API 579 fitness-for-service calculations with precision handling
  - Safety alerts for RSF < 0.9 and remaining life < 2 years
  - Critical findings visualization with regulatory compliance status
  - Connects to backend calculation APIs for real-time data
-->
<template>
  <div class="api579-results">
    <Card>
      <template #title>
        <div class="results-header">
          <div class="title-section">
            <i class="pi pi-calculator"></i>
            <span>API 579 Fitness-for-Service Analysis</span>
          </div>
          <Tag 
            :severity="complianceSeverity" 
            :icon="complianceIcon"
            class="compliance-tag"
          >
            {{ calculation?.fitness_for_service || 'Pending' }}
          </Tag>
        </div>
      </template>
      
      <template #content>
        <div v-if="!calculation" class="no-calculation">
          <Message severity="info" :closable="false">
            <template #messageicon>
              <i class="pi pi-info-circle"></i>
            </template>
            API 579 calculations will be performed automatically when thickness readings are submitted.
          </Message>
        </div>

        <div v-else class="calculation-content">
          <!-- Critical Safety Metrics -->
          <div class="safety-metrics">
            <div class="metric-grid">
              <div class="metric-card" :class="rsfSeverityClass">
                <div class="metric-header">
                  <i class="pi pi-shield"></i>
                  <span>Remaining Strength Factor</span>
                </div>
                <div class="metric-value">{{ formatDecimal(calculation.remaining_strength_factor) }}</div>
                <div class="metric-status">
                  <Tag :severity="rsfSeverity" size="small">
                    {{ rsfStatus }}
                  </Tag>
                </div>
              </div>

              <div class="metric-card" :class="lifeSeverityClass">
                <div class="metric-header">
                  <i class="pi pi-clock"></i>
                  <span>Remaining Life</span>
                </div>
                <div class="metric-value">{{ formatDecimal(calculation.remaining_life_years) }} years</div>
                <div class="metric-status">
                  <Tag :severity="lifeSeverity" size="small">
                    {{ lifeStatus }}
                  </Tag>
                </div>
              </div>

              <div class="metric-card">
                <div class="metric-header">
                  <i class="pi pi-calendar"></i>
                  <span>Next Inspection</span>
                </div>
                <div class="metric-value">{{ formatDecimal(calculation.recommendedInspectionInterval) }} years</div>
                <div class="metric-status">
                  <Tag severity="info" size="small">
                    Recommended
                  </Tag>
                </div>
              </div>
            </div>
          </div>

          <!-- Critical Findings Alert -->
          <div v-if="calculation.criticalFindings && calculation.criticalFindings.length > 0" class="critical-findings">
            <Message severity="error" :closable="false">
              <template #messageicon>
                <i class="pi pi-exclamation-triangle"></i>
              </template>
              <div class="findings-content">
                <strong>Critical Findings Detected:</strong>
                <ul class="findings-list">
                  <li v-for="finding in calculation.criticalFindings" :key="finding">
                    {{ finding }}
                  </li>
                </ul>
              </div>
            </Message>
          </div>

          <!-- Calculation Details -->
          <Fieldset legend="Calculation Details" class="calculation-details">
            <div class="details-grid">
              <div class="detail-item">
                <label>Calculation Type:</label>
                <span>{{ calculation.calculationType }}</span>
              </div>
              <div class="detail-item">
                <label>Minimum Required Thickness:</label>
                <span>{{ formatThickness(calculation.calculationDetails?.minimumThickness) }} in</span>
              </div>
              <div class="detail-item">
                <label>Actual Thickness:</label>
                <span>{{ formatThickness(calculation.calculationDetails?.actualThickness) }} in</span>
              </div>
              <div class="detail-item">
                <label>Allowable Stress:</label>
                <span>{{ formatNumber(calculation.calculationDetails?.allowableStress) }} psi</span>
              </div>
              <div class="detail-item">
                <label>Safety Factor:</label>
                <span>{{ formatDecimal(calculation.calculationDetails?.safetyFactor) }}</span>
              </div>
              <div class="detail-item">
                <label>Future Corrosion Allowance:</label>
                <span>{{ formatThickness(calculation.calculationDetails?.futureCorrosionAllowance) }} in</span>
              </div>
            </div>
          </Fieldset>

          <!-- Calculation Metadata -->
          <div class="calculation-metadata">
            <div class="metadata-item">
              <i class="pi pi-clock"></i>
              <span>Calculated: {{ formatDateTime(calculation.calculatedAt) }}</span>
            </div>
            <div class="metadata-item">
              <i class="pi pi-cog"></i>
              <span>Engine: {{ calculation.calculatedBy }}</span>
            </div>
          </div>

          <!-- Safety Warnings -->
          <div class="safety-warnings">
            <Message 
              v-if="calculation.remainingStrengthFactor < 0.9" 
              severity="warn" 
              :closable="false"
            >
              <template #messageicon>
                <i class="pi pi-exclamation-triangle"></i>
              </template>
              <strong>Safety Alert:</strong> Remaining Strength Factor below 0.9 requires immediate engineering review.
            </Message>
            
            <Message 
              v-if="calculation.remainingLife < 2" 
              severity="error" 
              :closable="false"
            >
              <template #messageicon>
                <i class="pi pi-times-circle"></i>
              </template>
              <strong>Critical Alert:</strong> Remaining life less than 2 years. Equipment requires immediate attention.
            </Message>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { API579Calculation } from '@/types'

interface Props {
  calculation?: API579Calculation | null
}

const props = defineProps<Props>()

// Computed properties for safety assessments
const complianceSeverity = computed(() => {
  if (!props.calculation) return 'info'
  
  switch (props.calculation.complianceStatus) {
    case 'Acceptable': return 'success'
    case 'Acceptable with Conditions': return 'warn'
    case 'Not Acceptable': return 'error'
    default: return 'info'
  }
})

const complianceIcon = computed(() => {
  switch (complianceSeverity.value) {
    case 'success': return 'pi-check-circle'
    case 'warn': return 'pi-exclamation-triangle'
    case 'error': return 'pi-times-circle'
    default: return 'pi-info-circle'
  }
})

const rsfSeverity = computed(() => {
  if (!props.calculation) return 'info'
  const rsf = props.calculation.remainingStrengthFactor
  
  if (rsf >= 0.95) return 'success'
  if (rsf >= 0.9) return 'warn'
  return 'error'
})

const rsfSeverityClass = computed(() => `severity-${rsfSeverity.value}`)

const rsfStatus = computed(() => {
  if (!props.calculation) return 'Unknown'
  const rsf = props.calculation.remainingStrengthFactor
  
  if (rsf >= 0.95) return 'Excellent'
  if (rsf >= 0.9) return 'Acceptable'
  return 'Critical'
})

const lifeSeverity = computed(() => {
  if (!props.calculation) return 'info'
  const life = props.calculation.remainingLife
  
  if (life >= 5) return 'success'
  if (life >= 2) return 'warn'
  return 'error'
})

const lifeSeverityClass = computed(() => `severity-${lifeSeverity.value}`)

const lifeStatus = computed(() => {
  if (!props.calculation) return 'Unknown'
  const life = props.calculation.remainingLife
  
  if (life >= 5) return 'Good'
  if (life >= 2) return 'Monitor'
  return 'Critical'
})

// Formatting functions
function formatDecimal(value: number | undefined): string {
  if (value === undefined || value === null) return '--'
  return value.toFixed(2)
}

function formatThickness(value: number | undefined): string {
  if (value === undefined || value === null) return '--'
  return value.toFixed(3)
}

function formatNumber(value: number | undefined): string {
  if (value === undefined || value === null) return '--'
  return value.toLocaleString()
}

function formatDateTime(dateString: string | undefined): string {
  if (!dateString) return '--'
  return new Date(dateString).toLocaleString()
}
</script>

<style scoped>
.api579-results {
  margin-top: 1.5rem;
}

.results-header {
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

.compliance-tag {
  font-weight: 600;
}

.no-calculation {
  text-align: center;
  padding: 2rem;
}

.safety-metrics {
  margin-bottom: 1.5rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.metric-card {
  padding: 1.5rem;
  border-radius: var(--p-border-radius);
  border: 2px solid var(--p-surface-border);
  background: var(--p-surface-card);
  transition: all 0.2s ease;
}

.metric-card.severity-success {
  border-color: var(--p-green-500);
  background: var(--p-green-50);
}

.metric-card.severity-warn {
  border-color: var(--p-orange-500);
  background: var(--p-orange-50);
}

.metric-card.severity-error {
  border-color: var(--p-red-500);
  background: var(--p-red-50);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  color: var(--p-text-color-secondary);
  font-size: 0.9rem;
  font-weight: 500;
}

.metric-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--p-text-color);
  margin-bottom: 0.5rem;
}

.metric-status {
  display: flex;
  justify-content: flex-end;
}

.critical-findings {
  margin-bottom: 1.5rem;
}

.findings-list {
  margin: 0.5rem 0 0 1rem;
  padding: 0;
}

.findings-list li {
  margin-bottom: 0.25rem;
}

.calculation-details {
  margin-bottom: 1.5rem;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: var(--p-surface-50);
  border-radius: var(--p-border-radius);
}

.detail-item label {
  font-weight: 600;
  color: var(--p-text-color-secondary);
}

.detail-item span {
  font-weight: 500;
  color: var(--p-text-color);
}

.calculation-metadata {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--p-surface-100);
  border-radius: var(--p-border-radius);
}

.metadata-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color-secondary);
  font-size: 0.9rem;
}

.safety-warnings {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (max-width: 768px) {
  .results-header {
    flex-direction: column;
    gap: 1rem;
    align-items: flex-start;
  }
  
  .metric-grid {
    grid-template-columns: 1fr;
  }
  
  .details-grid {
    grid-template-columns: 1fr;
  }
  
  .calculation-metadata {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
}
</style>