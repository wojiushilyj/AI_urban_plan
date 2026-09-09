<script setup lang="ts">
/** 卡片容器（模块 9.1）：标题 + 操作区插槽 + 内容插槽 */
defineProps<{
  title?: string
  subtitle?: string
}>()
</script>

<template>
  <section class="card-container">
    <header v-if="title || $slots.actions" class="card-container__header">
      <div>
        <h3 class="card-container__title">{{ title }}</h3>
        <p v-if="subtitle" class="card-container__subtitle">{{ subtitle }}</p>
      </div>
      <div class="card-container__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="card-container__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.card-container {
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--duration-base) var(--ease-in-out);
}
.card-container__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding: 12px var(--gap-lg);
  border-bottom: 1px solid var(--border-lighter);
}
.card-container__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.2px;
}
.card-container__subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 2px;
}
.card-container__actions {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
}
.card-container__body {
  padding: var(--gap-md) var(--gap-lg);
}
.card-container__body:empty {
  display: none;
}
</style>
