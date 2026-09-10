<script setup lang="ts">
/** 图层管理（模块 5.2）：图层按大类分组，每类有总开关 + 每图层单独开关，大类可点击展开/收缩 */
import { computed, ref } from 'vue'
import { useMapStore } from '../../store/map'

const mapStore = useMapStore()
const expanded = ref(false)

function toggle(): void {
  expanded.value = !expanded.value
}

/** 某大类的图层列表 */
function groupLayers(groupId: string) {
  return mapStore.layers.filter((l) => l.groupId === groupId)
}

/** 某大类开启的图层数 */
function groupOnCount(groupId: string): number {
  return mapStore.layers.filter((l) => l.groupId === groupId && l.visible).length
}

/** 某大类图层总数 */
function groupTotal(groupId: string): number {
  return mapStore.layers.filter((l) => l.groupId === groupId).length
}

/** 开启图层总数 */
const onCount = computed(() => mapStore.layers.filter((l) => l.visible).length)
</script>

<template>
  <div class="layer-manager">
    <!-- 面板级标题：点击展开/收缩 -->
    <div class="layer-manager__header" @click="toggle">
      <span class="layer-manager__title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/><path d="M12 8v8M8 12h8"/></svg>
        图层
      </span>
      <span class="layer-manager__count">
        {{ onCount }}/{{ mapStore.layers.length }}
        <svg class="layer-manager__chevron" :class="{ 'is-collapsed': !expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M6 9l6 6 6-6"/></svg>
      </span>
    </div>

    <!-- 分组列表 -->
    <div v-show="expanded" class="layer-manager__groups">
      <div v-for="g in mapStore.groups" :key="g.id" class="layer-group">
        <!-- 大类标题：点击展开/收缩 + 右侧总开关 -->
        <div class="layer-group__header">
          <div class="layer-group__title" @click="mapStore.toggleGroupExpand(g.id)">
            <svg class="layer-manager__chevron" :class="{ 'is-collapsed': !g.expanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
            <span class="layer-group__name">{{ g.name }}</span>
            <span class="layer-group__count">{{ groupOnCount(g.id) }}/{{ groupTotal(g.id) }}</span>
          </div>
          <el-switch
            :model-value="mapStore.isGroupAllOn(g.id)"
            size="small"
            @change="mapStore.toggleGroup(g.id)"
          />
        </div>

        <!-- 大类下图层 -->
        <div v-show="g.expanded" class="layer-group__list">
          <div v-for="l in groupLayers(g.id)" :key="l.id" class="layer-manager__item">
            <span class="layer-manager__name" :class="{ 'is-dim': !l.visible }">{{ l.name }}</span>
            <el-switch
              :model-value="l.visible"
              size="small"
              @change="mapStore.toggleLayer(l.id)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.layer-manager {
  width: 240px;
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
  padding: 7px 10px;
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
  flex: none;
  transition: transform var(--duration-fast) var(--ease-in-out, cubic-bezier(0.16, 1, 0.3, 1));
}
.layer-manager__chevron.is-collapsed {
  transform: rotate(-90deg);
}
.layer-manager__groups {
  border-top: 1px solid var(--border-lighter);
  padding: 6px 0 8px;
  max-height: 360px;
  overflow-y: auto;
}

/* 大类 */
.layer-group + .layer-group {
  margin-top: 2px;
}
.layer-group__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding: 4px 10px;
}
.layer-group__title {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  user-select: none;
  flex: 1;
  min-width: 0;
}
.layer-group__title:hover .layer-group__name {
  color: var(--text-primary);
}
.layer-group__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-regular);
}
.layer-group__count {
  font-size: 12px;
  color: var(--text-secondary);
}
.layer-group__list {
  padding: 2px 10px 2px 24px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

/* 图层条目 */
.layer-manager__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-md);
  font-size: 13px;
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
