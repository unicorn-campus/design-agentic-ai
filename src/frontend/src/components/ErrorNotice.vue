<script setup lang="ts">
defineProps<{ message: string }>()
</script>

<template>
  <div class="error-notice" role="alert">
    <strong>요청을 완료하지 못했습니다.</strong>
    <span>{{ message }}</span>
  </div>
</template>
