<template>
  <Dialog v-model:visible="visible" modal header="Upload Inspection Document" :style="{ width: '50rem' }">
    <div class="flex flex-column gap-4">
      <!-- Upload Area -->
      <div class="upload-section">
        <FileUpload
          ref="fileUpload"
          mode="basic"
          name="file"
          :url="uploadUrl"
          accept=".pdf"
          :maxFileSize="10000000"
          chooseLabel="Select PDF Document"
          @upload="onUpload"
          @select="onFileSelect"
          @error="onUploadError"
          :auto="false"
          class="w-full"
        />
        <small class="text-color-secondary">
          Supports PDF files up to 10MB. Works with both text-based and scanned documents.
        </small>
      </div>

      <!-- OCR Options -->
      <div v-if="selectedFile" class="ocr-options">
        <h4>Processing Options</h4>
        <div class="flex align-items-center gap-2">
          <Checkbox v-model="forceOCR" binary />
          <label>Force OCR (Use for scanned/image-based documents)</label>
        </div>
        <small class="text-color-secondary">
          OCR is automatically used for scanned documents, but you can force it for better accuracy on poor quality text PDFs.
        </small>
      </div>

      <!-- Processing Button -->
      <div v-if="selectedFile" class="flex justify-content-center">
        <Button 
          label="Process Document" 
          icon="pi pi-cog" 
          @click="processDocument"
          :loading="processing"
          class="p-button-primary"
        />
      </div>

      <!-- Processing Results -->
      <div v-if="extractionResults" class="results-section">
        <h4>Extraction Results</h4>
        
        <!-- Extraction Metadata -->
        <Card class="mb-3">
          <template #content>
            <div class="grid">
              <div class="col-6">
                <strong>Extraction Method:</strong> 
                <Badge 
                  :value="extractionResults.extraction_method?.toUpperCase() || 'TEXT'" 
                  :severity="extractionResults.extraction_method === 'ocr' ? 'info' : 'success'"
                />
              </div>
              <div class="col-6">
                <strong>Total Pages:</strong> {{ extractionResults.total_pages }}
                <span v-if="extractionResults.ocr_pages > 0" class="text-color-secondary ml-2">
                  ({{ extractionResults.ocr_pages }} OCR processed)
                </span>
              </div>
            </div>
          </template>
        </Card>

        <!-- Quality Metrics -->
        <Card class="mb-3" v-if="extractionResults.metrics">
          <template #content>
            <h5>Quality Metrics</h5>
            <div class="grid">
              <div class="col-4">
                <div class="text-center">
                  <div class="text-2xl font-semibold text-green-500">
                    {{ extractionResults.metrics.total_extractions }}
                  </div>
                  <div class="text-sm">Total Extractions</div>
                </div>
              </div>
              <div class="col-4">
                <div class="text-center">
                  <div class="text-2xl font-semibold" :class="getConfidenceColor(extractionResults.metrics.high_confidence_ratio)">
                    {{ (extractionResults.metrics.high_confidence_ratio * 100).toFixed(0) }}%
                  </div>
                  <div class="text-sm">High Confidence</div>
                </div>
              </div>
              <div class="col-4">
                <div class="text-center">
                  <div class="text-2xl font-semibold text-orange-500">
                    {{ extractionResults.metrics.extractions_with_warnings }}
                  </div>
                  <div class="text-sm">Need Review</div>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- Extracted Data -->
        <div v-if="extractionResults.extractions" class="extracted-data">
          <h5>Extracted Data</h5>
          <div class="grid">
            <div 
              v-for="(extraction, field) in extractionResults.extractions" 
              :key="field"
              class="col-6"
            >
              <Card class="h-full" :class="getExtractionCardClass(extraction)">
                <template #content>
                  <div class="flex align-items-center justify-content-between mb-2">
                    <strong>{{ formatFieldName(field) }}</strong>
                    <Badge 
                      :value="`${(extraction.confidence * 100).toFixed(0)}%`"
                      :severity="getConfidenceSeverity(extraction.confidence)"
                    />
                  </div>
                  
                  <div class="extraction-value mb-2">
                    <span class="text-lg font-semibold">{{ extraction.value }}</span>
                  </div>
                  
                  <div class="text-sm text-color-secondary mb-2">
                    <strong>Source:</strong> {{ extraction.source }}
                    <br>
                    <strong>Page:</strong> {{ extraction.page }}
                    <strong class="ml-2">Method:</strong> {{ extraction.method }}
                  </div>
                  
                  <div v-if="extraction.warnings && extraction.warnings.length > 0" class="warnings">
                    <div v-for="warning in extraction.warnings" :key="warning" class="text-orange-600 text-sm">
                      <i class="pi pi-exclamation-triangle mr-1"></i>{{ warning }}
                    </div>
                  </div>
                  
                  <div v-if="extraction.alternatives > 0" class="text-xs text-color-secondary mt-1">
                    {{ extraction.alternatives }} alternative value(s) found
                  </div>
                </template>
              </Card>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-content-center gap-2 mt-4">
          <Button 
            label="Create Inspection Record" 
            icon="pi pi-plus" 
            @click="createInspectionRecord"
            :disabled="!hasHighQualityExtractions"
            severity="success"
          />
          <Button 
            label="Export Results" 
            icon="pi pi-download" 
            @click="exportResults"
            severity="secondary"
            outlined
          />
        </div>
      </div>

      <!-- Warning for Low Quality -->
      <Message 
        v-if="extractionResults && extractionResults.requires_review"
        severity="warn"
        :closable="false"
        class="mt-3"
      >
        This document has low-confidence extractions that require manual review before creating inspection records.
      </Message>
    </div>

    <template #footer>
      <Button label="Close" @click="closeDialog" class="p-button-text" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import FileUpload from 'primevue/fileupload'
import Checkbox from 'primevue/checkbox'
import Card from 'primevue/card'
import Badge from 'primevue/badge'
import Message from 'primevue/message'

// Props and emits
const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'inspection-created': [data: any]
}>()

// Reactive data
const selectedFile = ref<File | null>(null)
const forceOCR = ref(false)
const processing = ref(false)
const extractionResults = ref<any>(null)
const fileUpload = ref()

// Computed
const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const uploadUrl = computed(() => {
  return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/documents/extract`
})

const hasHighQualityExtractions = computed(() => {
  if (!extractionResults.value || !extractionResults.value.metrics) return false
  return extractionResults.value.metrics.high_confidence_ratio >= 0.7
})

// Methods
const onFileSelect = (event: any) => {
  selectedFile.value = event.files[0] || null
  extractionResults.value = null
}

const onUpload = (event: any) => {
  console.log('Upload event:', event)
}

const onUploadError = (event: any) => {
  console.error('Upload error:', event)
}

const processDocument = async () => {
  if (!selectedFile.value) return
  
  try {
    processing.value = true
    
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('force_ocr', forceOCR.value.toString())
    
    const response = await fetch(`${uploadUrl.value}?force_ocr=${forceOCR.value}`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    extractionResults.value = await response.json()
    
  } catch (error) {
    console.error('Document processing failed:', error)
    // Show error message to user
  } finally {
    processing.value = false
  }
}

const getConfidenceColor = (ratio: number) => {
  if (ratio >= 0.8) return 'text-green-500'
  if (ratio >= 0.6) return 'text-orange-500' 
  return 'text-red-500'
}

const getConfidenceSeverity = (confidence: number) => {
  if (confidence >= 0.9) return 'success'
  if (confidence >= 0.7) return 'warning'
  return 'danger'
}

const getExtractionCardClass = (extraction: any) => {
  if (extraction.warnings && extraction.warnings.length > 0) {
    return 'border-orange-500 bg-orange-50'
  }
  if (extraction.confidence >= 0.9) {
    return 'border-green-500 bg-green-50'
  }
  return 'border-blue-500 bg-blue-50'
}

const formatFieldName = (field: string) => {
  const fieldMap: Record<string, string> = {
    'equipment_tag': 'Equipment Tag',
    'thickness': 'Thickness Measurements',
    'date': 'Inspection Date',
    'pressure': 'Pressure Values',
    'inspector_name': 'Inspector',
    'corrosion_rate': 'Corrosion Rate',
    'next_inspection': 'Next Inspection Due'
  }
  return fieldMap[field] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const createInspectionRecord = () => {
  // Emit event with extracted data for parent to handle
  emit('inspection-created', extractionResults.value)
}

const exportResults = () => {
  const dataStr = JSON.stringify(extractionResults.value, null, 2)
  const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
  
  const exportFileDefaultName = `inspection-extraction-${new Date().toISOString().split('T')[0]}.json`
  
  const linkElement = document.createElement('a')
  linkElement.setAttribute('href', dataUri)
  linkElement.setAttribute('download', exportFileDefaultName)
  linkElement.click()
}

const closeDialog = () => {
  visible.value = false
  selectedFile.value = null
  extractionResults.value = null
  forceOCR.value = false
  processing.value = false
}
</script>

<style scoped>
.upload-section {
  border: 2px dashed var(--p-surface-border);
  border-radius: var(--p-border-radius);
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
}

.upload-section:hover {
  border-color: var(--p-primary-color);
  background: var(--p-surface-50);
}

.results-section {
  border-top: 1px solid var(--p-surface-border);
  padding-top: 1.5rem;
}

.extraction-value {
  min-height: 2rem;
  display: flex;
  align-items: center;
}

.warnings {
  background: var(--p-orange-50);
  border: 1px solid var(--p-orange-200);
  border-radius: var(--p-border-radius);
  padding: 0.5rem;
  margin-top: 0.5rem;
}

.ocr-options {
  background: var(--p-surface-50);
  border: 1px solid var(--p-surface-border);
  border-radius: var(--p-border-radius);
  padding: 1rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
}

.col-4 { grid-column: span 4; }
.col-6 { grid-column: span 6; }

@media (max-width: 768px) {
  .col-4, .col-6 {
    grid-column: span 12;
  }
}
</style>