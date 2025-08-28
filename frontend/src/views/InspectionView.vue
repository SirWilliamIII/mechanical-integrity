<template>
  <div class="inspection-view">
    <div class="page-header">
      <div class="header-content">
        <h2>Equipment Inspection</h2>
        <p class="subtitle">Create new inspection records manually or from scanned documents</p>
      </div>
      <div class="header-actions">
        <Button 
          label="Upload Document" 
          icon="pi pi-upload" 
          @click="showUploadDialog = true"
          severity="info"
          outlined
        />
      </div>
    </div>

    <Card>
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-wrench"></i>
          Manual Inspection Entry
        </div>
      </template>
      <template #content>
        <InspectionForm @submit="handleInspectionSubmit" />
      </template>
    </Card>

    <!-- Document Upload Dialog -->
    <DocumentUploadDialog 
      v-model:visible="showUploadDialog"
      @inspection-created="handleDocumentExtraction"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import InspectionForm from '@/components/forms/InspectionForm.vue'
import DocumentUploadDialog from '@/components/documents/DocumentUploadDialog.vue'
import { inspectionsApi } from '@/api/inspections'
import type { InspectionCreateRequest } from '@/types'

const toast = useToast()
const isSubmitting = ref(false)
const showUploadDialog = ref(false)

async function handleInspectionSubmit(data: InspectionCreateRequest) {
  if (isSubmitting.value) return
  
  isSubmitting.value = true
  
  try {
    const result = await inspectionsApi.createInspection(data)
    
    toast.add({
      severity: 'success',
      summary: 'Inspection Created',
      detail: `Inspection ${result.id} has been successfully created and is pending review.`,
      life: 5000
    })
    
    // Could navigate to inspection detail view
    // router.push(`/inspections/${result.id}`)
    
  } catch (error: any) {
    console.error('Inspection submission error:', error)
    
    toast.add({
      severity: 'error',
      summary: 'Submission Failed',
      detail: error.message || 'Failed to create inspection. Please try again.',
      life: 7000
    })
  } finally {
    isSubmitting.value = false
  }
}

function handleDocumentExtraction(extractionData: any) {
  showUploadDialog.value = false
  
  toast.add({
    severity: 'info',
    summary: 'Document Processed',
    detail: `Extracted ${extractionData.metrics?.total_extractions || 0} data points from ${extractionData.filename}`,
    life: 5000
  })
  
  // TODO: Pre-fill inspection form with extracted data
  // This would involve mapping extracted fields to form fields
  console.log('Extracted data:', extractionData)
}
</script>

<style scoped>
.inspection-view {
  padding: 2rem;
  max-width: 1200px;
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

@media (max-width: 1024px) {
  .inspection-view {
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
  }
}

@media (max-width: 768px) {
  .inspection-view {
    padding: 0.5rem;
  }
}
</style>