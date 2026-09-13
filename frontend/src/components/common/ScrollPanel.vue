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
  /* 面板内边距由 TabPanel 统一提供，此处仅补底部留白 */
  padding: 0 0 var(--panel-pad-right) 0;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}
/* 子卡默认不收缩（空间不足时走外层滚动，而不是把卡内容压扁）；
   带 .card-container--grow 的卡按自身规则弹性填充剩余空间 */
.scroll-panel > * {
  flex: none;
}
</style>
