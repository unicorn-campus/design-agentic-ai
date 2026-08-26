<script setup lang="ts">
import { computed, ref } from 'vue'
import { submitInquiry, type ApiRecord, type InquiryFormValue } from './api'
import ErrorNotice from './components/ErrorNotice.vue'
import InquiryForm from './components/InquiryForm.vue'
import ResultPanel from './components/ResultPanel.vue'
import ServiceHeader from './components/ServiceHeader.vue'

const result = ref<ApiRecord | null>(null)
const error = ref('')
const loading = ref(false)
const status = computed(() => {
  if (loading.value) return 'loading'
  if (error.value) return 'error'
  if (result.value) return 'done'
  return 'idle'
})

async function handleSubmit(value: InquiryFormValue): Promise<void> {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await submitInquiry(value)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : '요청 처리에 실패함'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page-shell">
    <ServiceHeader :status="status" />
    <ErrorNotice v-if="error" :message="error" />
    <div class="workspace-grid">
      <InquiryForm :disabled="loading" @submit="handleSubmit" />
      <ResultPanel :result="result" :loading="loading" />
    </div>
    <footer>
      민감정보는 입력하지 마세요. 답변은 안전 검사와 승인 정책을 거쳐 제공됩니다.
    </footer>
  </main>
</template>
