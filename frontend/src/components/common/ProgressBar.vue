<script setup lang="ts">
/** 进度条组件（模块 9.3）：el-progress 封装 */
withDefaults(
  defineProps<{
    percent?: number
    label?: string
    showText?: boolean
  }>(),
  { percent: 0, label: '', showText: true }
)
</script>

<template>
  <div class="progress-bar">
    <span v-if="label" class="progress-bar__label">{{ label }}</span>
    <el-progress
      :percentage="percent"
      :stroke-width="8"
      :show-text="showText"
      :status="percent >= 100 ? 'success' : undefined"
    />
  </div>
</template>

<style scoped>
.progress-bar {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}
.progress-bar__label {
  font-size: 14px;
  color: var(--text-secondary);
}
</style>
