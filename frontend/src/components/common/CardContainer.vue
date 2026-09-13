<script setup lang="ts">
/** 卡片容器（模块 9.1）：标题 + 操作区插槽 + 内容插槽；grow 时卡片撑满剩余空间、内容区内部滚动 */
defineProps<{
  title?: string
  subtitle?: string
  /** 弹性填充模式：卡片占满父级剩余高度，body 内部滚动（用于结果页签的自适应高度卡） */
  grow?: boolean
}>()
</script>

<template>
  <section class="card-container" :class="{ 'card-container--grow': grow }">
    <header v-if="title || $slots.actions" class="card-container__header">
      <div class="card-container__title-wrap">
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
  border-radius: var(--radius-card);
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
.card-container__title-wrap {
  display: flex;
  flex-direction: column;
  position: relative;
  padding-left: 10px;
}
.card-container__title-wrap::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  background: var(--brand, var(--el-color-primary));
  border-radius: 2px;
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
/* 弹性填充：卡片占满父级剩余高度，超出内容在 body 内滚动（细滚动条）。
   双类名提高优先级，确保覆盖 ScrollPanel 的 `> * { flex: none }` */
.card-container.card-container--grow {
  flex: 1 1 auto;
  min-height: 150px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-container--grow .card-container__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.card-container--grow .card-container__body::-webkit-scrollbar {
  width: 6px;
}
.card-container--grow .card-container__body::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: var(--radius-pill);
}
.card-container--grow .card-container__body::-webkit-scrollbar-thumb:hover {
  background: var(--muted-2);
}
.card-container--grow .card-container__body::-webkit-scrollbar-track {
  background: transparent;
}
</style>
