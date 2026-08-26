<script setup lang="ts">
import { ref } from 'vue'
import type { InquiryFormValue } from '../api'

defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ submit: [value: InquiryFormValue] }>()

const inquiryText = ref('')
const channel = ref('web')

function submit(): void {
  const value = inquiryText.value.trim()
  if (!value) return
  emit('submit', {
    requestId: crypto.randomUUID(),
    authSessionRef: 'browser-session',
    inquiryText: value,
    channel: channel.value,
  })
}
</script>

<template>
  <form class="inquiry-card" @submit.prevent="submit">
    <div class="section-heading">
      <span class="step-number">01</span>
      <div>
        <h2>카드 문의 입력</h2>
        <p>개인정보 대신 상황과 궁금한 점을 적어주세요.</p>
      </div>
    </div>
    <label for="inquiry">문의 내용</label>
    <textarea
      id="inquiry"
      v-model="inquiryText"
      :disabled="disabled"
      rows="9"
      placeholder="예: 해외 결제가 거절된 이유와 확인 절차를 알려주세요."
    />
    <div class="form-row">
      <label for="channel">상담 채널</label>
      <select id="channel" v-model="channel" :disabled="disabled">
        <option value="web">웹</option>
        <option value="mobile">모바일</option>
        <option value="phone">전화</option>
      </select>
    </div>
    <button type="submit" :disabled="disabled || !inquiryText.trim()">
      <span>{{ disabled ? '근거 확인 중' : '근거 답변 요청' }}</span>
      <span aria-hidden="true">→</span>
    </button>
  </form>
</template>
