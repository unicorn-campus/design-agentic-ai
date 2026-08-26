<script setup lang="ts">
import { computed } from 'vue'
import type { ApiRecord } from '../api'

const props = defineProps<{
  result: ApiRecord | null
  loading: boolean
}>()

const answerText = computed(() => {
  const answer = props.result?.answer
  if (typeof answer === 'string') return answer
  if (answer && typeof answer === 'object') return JSON.stringify(answer, null, 2)
  return ''
})
</script>

<template>
  <section class="result-card" aria-live="polite">
    <div class="section-heading">
      <span class="step-number">02</span>
      <div>
        <h2>처리 결과</h2>
        <p>안전 검사와 근거 확인을 통과한 결과만 표시합니다.</p>
      </div>
    </div>
    <div v-if="loading" class="result-empty loading-state">
      <span class="loader" aria-hidden="true" />
      <p>내부 지식과 공식 근거를 확인하고 있습니다.</p>
    </div>
    <div v-else-if="!result" class="result-empty">
      <span class="empty-mark" aria-hidden="true">◇</span>
      <p>문의를 보내면 처리 상태와 근거 답변이 이곳에 표시됩니다.</p>
    </div>
    <div v-else class="result-content">
      <dl class="result-meta">
        <div>
          <dt>결과 유형</dt>
          <dd>{{ result.result_type ?? '확인 중' }}</dd>
        </div>
        <div>
          <dt>요청 상태</dt>
          <dd>{{ result.request_status ?? '확인 중' }}</dd>
        </div>
      </dl>
      <article v-if="answerText" class="answer-block">
        <h3>근거 답변</h3>
        <pre>{{ answerText }}</pre>
      </article>
      <aside v-if="result.handoff_ref" class="handoff-block">
        상담사 인계 번호: <strong>{{ result.handoff_ref }}</strong>
      </aside>
    </div>
  </section>
</template>
