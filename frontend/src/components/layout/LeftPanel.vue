<script setup lang="ts">
/** 左侧面板（模块 2）：AI 需求交互 */
import ChatPanel from '../ai/ChatPanel.vue'
</script>

<template>
  <div class="left-panel">
    <ChatPanel />
  </div>
</template>

<style scoped>
.left-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
