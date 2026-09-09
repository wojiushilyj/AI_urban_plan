<script setup lang="ts">
/** 单条消息气泡（模块 2.1） */
import type { ChatMessage } from '../../types/ai'

defineProps<{ msg: ChatMessage }>()
</script>

<template>
  <div class="chat-message" :class="`chat-message--${msg.role}`">
    <div class="chat-message__avatar">
      {{ msg.role === 'assistant' ? '🤖' : '👤' }}
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
  gap: var(--gap-sm);
  margin-bottom: 10px;
}
.chat-message--user {
  flex-direction: row-reverse;
}
.chat-message__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-light-9);
  flex-shrink: 0;
  font-size: 16px;
}
.chat-message__body {
  max-width: 78%;
  display: flex;
  flex-direction: column;
}
.chat-message--user .chat-message__body {
  align-items: flex-end;
}
.chat-message__bubble {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  border: 1px solid var(--border-lighter);
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-regular);
  word-break: break-word;
}
.chat-message--user .chat-message__bubble {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.chat-message__time {
  font-size: 12px;
  color: var(--text-disabled);
  margin-top: 2px;
  padding: 0 2px;
}
</style>
