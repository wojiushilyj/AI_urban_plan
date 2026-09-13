<script setup lang="ts">
/** 图层管理（模块 5.2）：图层按大类分组，每类有总开关 + 每图层单独开关，大类可点击展开/收缩 */
import { computed, ref } from 'vue'
import { useMapStore, type BusinessLayer } from '../../store/map'
import { LAYER_COUNTS } from '../../api/layerCounts.generated'
import AppIcon from '../common/AppIcon.vue'

const mapStore = useMapStore()
const expanded = ref(false)

/** 某图层的要素数量文案：选址结果类跟随计算结果，其余取离线统计；未知为 null（不显示）。格式如「（7851项）」 */
function countText(l: BusinessLayer): string | null {
  if (l.groupId === 'result') {
    // 候选地块 / 地块序号共用同一批候选要素
    return mapStore.result ? `（${mapStore.result.candidates.length}项）` : null
  }
  const n = LAYER_COUNTS[l.id]
  return typeof n === 'number' ? `（${n}项）` : null
}

function toggle(): void {
  expanded.value = !expanded.value
}

/** 「选址结果」类在分析完成前取不到数据，开关置灰 */
function isGroupPending(groupId: string): boolean {
  return groupId === 'result' && !mapStore.result
}
function isPending(l: BusinessLayer): boolean {
  return l.groupId === 'result' && !mapStore.result
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
        <AppIcon class="layer-manager__title-icon" name="layers" :size="17" />
        图层
      </span>
      <span class="layer-manager__count">
        {{ onCount }}/{{ mapStore.layers.length }}
        <AppIcon class="layer-manager__chevron" :class="{ 'is-collapsed': !expanded }" name="chevron-down" :size="15" />
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
            <span class="layer-group__count">
              {{ isGroupPending(g.id) ? '待分析' : `${groupOnCount(g.id)}/${groupTotal(g.id)}` }}
            </span>
          </div>
          <el-switch
            :model-value="mapStore.isGroupAllOn(g.id)"
            size="small"
            :disabled="isGroupPending(g.id)"
            @change="mapStore.toggleGroup(g.id)"
          />
        </div>

        <!-- 大类下图层 -->
        <div v-show="g.expanded" class="layer-group__list">
          <div v-for="l in groupLayers(g.id)" :key="l.id" class="layer-manager__item">
            <span class="layer-manager__name" :class="{ 'is-dim': !l.visible || isPending(l) }">{{ l.name }}<span class="layer-manager__num">{{ countText(l) }}</span></span>
            <el-switch
              :model-value="l.visible"
              size="small"
              :disabled="isPending(l)"
              @change="mapStore.toggleLayer(l.id)"
            />
          </div>
          <!-- 分析前该大类无内容可渲染，给出说明 -->
          <div v-if="isGroupPending(g.id)" class="layer-group__empty">完成选址分析后自动上图</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.layer-manager {
  width: 244px;
  background: #fff;
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
/* 面板头（对齐原型 .mp-head：44px / 13px / 700） */
.layer-manager__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  height: 44px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
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
/* 图层图标用品牌钴蓝（Meta 原型 .mp-head 的处理方式） */
.layer-manager__title-icon {
  color: var(--brand);
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
/* 图层名右侧的要素数量（离线统计 / 候选地块数），如「（7851项）」 */
.layer-manager__num {
  margin-left: 3px;
  font-size: 10px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.layer-manager__name.is-dim .layer-manager__num {
  color: var(--text-disabled);
}
/* 尚未可用的说明（分析前「选址结果」类无内容可渲染） */
.layer-group__empty {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-disabled);
  padding: 1px 0 2px;
}
</style>
