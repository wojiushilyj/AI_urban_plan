<script setup lang="ts">
/**
 * 底图控制（模块 5.1）：天地图矢量 / OSM / 天地图影像。
 * 形态对齐设计稿 .map-panel：228px 面板、44px 头部、灰底胶囊分段页签。
 * 头部右侧并入原「地图状态胶囊」内容：当前底图名 + 缩放级别。
 */
import { computed } from 'vue'
import { useMapStore } from '../../store/map'
import { BASEMAPS } from '../../composables/useMap'
import AppIcon from '../common/AppIcon.vue'

const props = defineProps<{ zoom?: number }>()

const mapStore = useMapStore()

/** 展示顺序对齐设计稿：矢量 / OSM / 影像 */
const ORDER: string[] = ['tianditu-vec', 'osm', 'tianditu-img']
const items = computed(() =>
  ORDER.map((id) => BASEMAPS.find((b) => b.id === id)).filter(
    (b): b is (typeof BASEMAPS)[number] => Boolean(b)
  )
)

/** 当前底图名（OSM 不带前缀，天地图带「天地图 ·」前缀） */
const statusLabel = computed(() => {
  const b = BASEMAPS.find((x) => x.id === mapStore.basemap)
  if (!b) return '—'
  return mapStore.basemap === 'osm' ? 'OSM' : `天地图 · ${b.name}`
})

const zoomText = computed(() => (props.zoom ?? null) === null ? '—' : String(props.zoom))
</script>

<template>
  <div class="basemap-panel">
    <div class="basemap-panel__head">
      <AppIcon class="basemap-panel__icon" name="layers" :size="14" />
      <span class="basemap-panel__title">底图</span>
      <span class="basemap-panel__status">
        <i class="basemap-panel__dot" />
        <span class="basemap-panel__status-name">{{ statusLabel }}</span>
        <i class="basemap-panel__sep" />
        <span class="basemap-panel__status-zoom">缩放 {{ zoomText }}</span>
      </span>
    </div>
    <div class="basemap-panel__tabs">
      <el-radio-group v-model="mapStore.basemap" class="basemap-panel__group">
        <el-radio-button
          v-for="b in items"
          :key="b.id"
          :value="b.id"
          :disabled="!b.available"
        >
          {{ b.name }}
        </el-radio-button>
      </el-radio-group>
    </div>
  </div>
</template>

<style scoped>
.basemap-panel {
  width: 228px;
  background: #fff;
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.basemap-panel__head {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}
.basemap-panel__icon {
  color: var(--brand);
  flex: none;
}
.basemap-panel__title {
  flex: none;
}
/* 头部右侧：当前底图 + 缩放级别（原独立状态胶囊并入） */
.basemap-panel__status {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  white-space: nowrap;
}
.basemap-panel__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-success);
  flex: 0 0 6px;
}
.basemap-panel__status-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
}
.basemap-panel__sep {
  width: 1px;
  height: 10px;
  background: var(--border-lighter);
  flex: none;
}
.basemap-panel__status-zoom {
  font-size: 11px;
  font-weight: 500;
  color: var(--muted);
  flex: none;
}
/* 灰底胶囊分段（原型 .mp-tabs） */
.basemap-panel__tabs {
  padding: 4px;
  background: var(--bg-subtle);
  border-top: 1px solid var(--border-lighter);
}
.basemap-panel__group {
  display: flex;
  gap: 4px;
  width: 100%;
}
.basemap-panel__group :deep(.el-radio-button) {
  flex: 1 1 0;
  min-width: 0;
}
/* 底图档位为「透明胶囊 + 选中黑底」，与偏好档位的描边胶囊区分（原型 .mp-tab） */
.basemap-panel__group :deep(.el-radio-button__inner) {
  border: 0 !important;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
}
.basemap-panel__group :deep(.el-radio-button__inner:hover) {
  color: var(--ink-2);
}
.basemap-panel__group
  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--ink);
  color: #fff;
  font-weight: 700;
}
.basemap-panel__group :deep(.el-radio-button.is-disabled .el-radio-button__inner) {
  color: var(--muted-2);
  opacity: 0.6;
}
</style>
