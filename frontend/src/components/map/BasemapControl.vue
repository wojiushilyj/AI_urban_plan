<script setup lang="ts">
/** 底图控制（模块 5.1）：OSM / 天地图矢量 / 天地图影像 */
import { useMapStore } from '../../store/map'
import { BASEMAPS } from '../../composables/useMap'

const mapStore = useMapStore()
</script>

<template>
  <div class="basemap-control">
    <div class="basemap-control__header">
      <span>底图</span>
    </div>
    <div class="basemap-control__body">
      <el-radio-group v-model="mapStore.basemap" size="small" class="basemap-control__group">
        <el-radio-button
          v-for="b in BASEMAPS"
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
.basemap-control {
  min-width: 200px;
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
.basemap-control__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding: 6px 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  cursor: default;
}
.basemap-control__body {
  padding: 6px;
  border-top: 1px solid var(--border-lighter);
}
.basemap-control__group {
  display: flex;
  width: 100%;
}
.basemap-control__group :deep(.el-radio-button) {
  flex: 1;
}
.basemap-control__group :deep(.el-radio-button__inner) {
  width: 100%;
}
</style>
