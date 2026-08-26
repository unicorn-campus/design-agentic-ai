<script setup lang="ts">
defineProps<{
  status: 'idle' | 'loading' | 'done' | 'error'
}>()

const labels = {
  idle: '문의 대기',
  loading: '근거 확인 중',
  done: '처리 완료',
  error: '확인 필요',
}
</script>

<template>
  <header class="service-header">
    <div>
      <p class="eyebrow">CARD SERVICE INTELLIGENCE</p>
      <h1>Help Desk Copilot</h1>
      <p class="subtitle">승인된 근거를 바탕으로 카드 문의를 안전하게 처리합니다.</p>
    </div>
    <div class="status-pill" :data-status="status">
      <span class="status-dot" aria-hidden="true" />
      {{ labels[status] }}
    </div>
  </header>
</template>
