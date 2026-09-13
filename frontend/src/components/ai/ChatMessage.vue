<script setup lang="ts">
/** 单条消息气泡（模块 2.1）：头像用 AppIcon（Meta 图标体系） */
import type { ChatMessage } from '../../types/ai'
import AppIcon from '../common/AppIcon.vue'

defineProps<{ msg: ChatMessage }>()
</script>

<template>
  <div class="chat-message" :class="`chat-message--${msg.role}`">
    <div class="chat-message__avatar">
      <AppIcon :name="msg.role === 'assistant' ? 'assistant' : 'user'" :size="msg.role === 'assistant' ? 28 : 16" />
    </div>
    <div class="chat-message__body">
      <div class="chat-message__bubble">{{ msg.content }}</div>
      <div class="chat-message__time">{{ msg.time }}</div>
    </div>
  </div>
</template>

<style scoped>
.chat-message {
  display: flex;
  gap: 8px;
}
.chat-message--user {
  flex-direction: row-reverse;
}
.chat-message__avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-light-9);
  color: var(--text-secondary);
  flex-shrink: 0;
}
/* 助手头像自带品牌色圆底，不再叠加浅蓝底 */
.chat-message--assistant .chat-message__avatar {
  background: transparent;
  width: 24px;
  height: 24px;
  overflow: hidden;
}
.chat-message__body {
  max-width: 82%;
  display: flex;
  flex-direction: column;
}
.chat-message--user .chat-message__body {
  align-items: flex-end;
}
/* 气泡（原型 .bubble：12px/19px、圆角 12、无描边） */
.chat-message__bubble {
  padding: 10px;
  border-radius: 12px;
  background: var(--bg-subtle);
  font-size: 12px;
  line-height: 19px;
  color: var(--body);
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-message--user .chat-message__bubble {
  background: var(--brand);
  color: #fff;
}
.chat-message__time {
  font-size: 11px;
  color: var(--text-disabled);
  margin-top: 2px;
  padding: 0 2px;
}
</style>
