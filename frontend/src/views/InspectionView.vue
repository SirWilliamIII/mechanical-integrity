<template>
  <div class="inspection-view">
    <Card>
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-wrench"></i>
          Equipment Inspection
        </div>
      </template>
      <template #content>
        <InspectionForm @submit="handleInspectionSubmit" />
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import InspectionForm from '@/components/forms/InspectionForm.vue'
import { inspectionsApi } from '@/api/inspections'
import type { InspectionCreateRequest } from '@/types'

const toast = useToast()
const isSubmitting = ref(false)

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
</script>

<style scoped>
.inspection-view {
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .inspection-view {
    padding: 0.5rem;
  }
}
</style>