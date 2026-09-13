<script setup lang="ts">
/**
 * 标签页面板（模块 9.2）。
 * 形态对齐设计稿 .seg：灰底胶囊分段 + 等宽胶囊页签 + 选中黑底白字（纯文字，无图标）。
 * 首屏只挂载当前页签，切换过的页签保留挂载（v-show），避免重复请求。
 */
import { ref, watch } from 'vue'

defineProps<{
  tabs: { name: string; label: string; icon?: string }[]
}>()
const active = defineModel<string>('active', { required: true })

/** 已访问过的页签（懒挂载 + 保活） */
const visited = ref<string[]>([active.value])
watch(active, (v) => {
  if (!visited.value.includes(v)) visited.value.push(v)
})
</script>

<template>
  <div class="tab-panel">
    <div class="seg" role="tablist">
      <button
        v-for="t in tabs"
        :key="t.name"
        type="button"
        class="seg-item"
        :class="{ 'is-active': active === t.name }"
        role="tab"
        :aria-selected="active === t.name"
        @click="active = t.name"
      >
        {{ t.label }}
      </button>
    </div>

    <div class="tab-panel__body">
      <template v-for="t in tabs" :key="t.name">
        <div
          v-if="visited.includes(t.name)"
          v-show="active === t.name"
          class="tab-panel__pane"
          role="tabpanel"
        >
          <slot :name="t.name" />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.tab-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: var(--panel-pad-right) var(--panel-pad-right) 0;
  gap: 16px;
}
/* 胶囊分段（原型 .seg） */
.seg {
  flex: none;
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
}
.seg-item {
  flex: 1 1 0;
  min-width: 0;
  height: 36px;
  border: 0;
  background: transparent;
  border-radius: var(--radius-pill);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  transition: 0.16s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.seg-item:hover {
  color: var(--ink-2);
}
.seg-item.is-active {
  background: var(--ink);
  color: #fff;
  font-weight: 700;
}
.tab-panel__body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.tab-panel__pane {
  height: 100%;
}
</style>
