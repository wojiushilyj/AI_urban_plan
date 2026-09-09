<script setup lang="ts">
/** 滚动面板（模块 9.5）：统一内部滚动 */
defineProps<{
  height?: string
}>()
</script>

<template>
  <div class="scroll-panel" :style="height ? { height } : undefined">
    <slot />
  </div>
</template>

<style scoped>
.scroll-panel {
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}
</style>
