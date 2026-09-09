<script setup lang="ts">
/** 图层管理（模块 5.2）：国土业务图层 + 结果图层开关；点击标题展开/收起 */
import { ref } from 'vue'
import { useMapStore } from '../../store/map'

const mapStore = useMapStore()
const expanded = ref(false)

function toggle(): void {
  expanded.value = !expanded.value
}
</script>

<template>
  <div class="layer-manager">
    <div class="layer-manager__header" @click="toggle">
      <span class="layer-manager__title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/><path d="M12 8v8M8 12h8"/></svg>
        图层
      </span>
      <span class="layer-manager__count">
        {{ mapStore.layers.filter((l) => l.visible).length }}/{{ mapStore.layers.length }}
        <svg class="layer-manager__chevron" :class="{ 'is-collapsed': !expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M6 9l6 6 6-6"/></svg>
      </span>
    </div>
    <div v-show="expanded" class="layer-manager__list">
      <div v-for="l in mapStore.layers" :key="l.id" class="layer-manager__item">
        <span class="layer-manager__name" :class="{ 'is-dim': !l.visible }">{{ l.name }}</span>
        <el-switch
          :model-value="l.visible"
          size="small"
          @change="mapStore.toggleLayer(l.id)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.layer-manager {
  width: 224px;
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.layer-manager__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding: 6px 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  cursor: pointer;
  user-select: none;
}
.layer-manager__header:hover {
  background: var(--bg-hover);
}
.layer-manager__title {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-primary);
}
.layer-manager__count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 400;
  color: var(--text-secondary);
  font-size: 13px;
}
.layer-manager__chevron {
  transition: transform var(--duration-fast) var(--ease-in-out, cubic-bezier(0.16, 1, 0.3, 1));
}
.layer-manager__chevron.is-collapsed {
  transform: rotate(-90deg);
}
.layer-manager__list {
  padding: 4px 10px 8px;
  border-top: 1px solid var(--border-lighter);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.layer-manager__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-md);
  font-size: 14px;
}
.layer-manager__name {
  color: var(--text-regular);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.layer-manager__name.is-dim {
  color: var(--text-disabled);
}
</style>
