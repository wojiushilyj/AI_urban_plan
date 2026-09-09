<script setup lang="ts">
/**
 * 地图工具条（模块 5.4）：缩放、测距、测面积、出图。
 * 测量为独立模式（mapStore.toolMode）。
 */
import { ElMessage } from 'element-plus'
import { useMapStore } from '../../store/map'
import { doExport } from '../../api/export'

const mapStore = useMapStore()

const tools = [
  { mode: 'measure-dist', icon: '📏', label: '测量距离（点击加点，双击结束）' },
  { mode: 'measure-area', icon: '📐', label: '测量面积（至少 3 点，双击结束）' },
] as const

function onTool(mode: (typeof tools)[number]['mode']): void {
  mapStore.toolMode = mapStore.toolMode === mode ? 'pan' : mode
  if (mapStore.toolMode !== 'pan') {
    const tip: Record<string, string> = {
      'measure-dist': '点击地图加点，双击结束测距',
      'measure-area': '点击地图加点（至少 3 点），双击结束测面积',
    }
    ElMessage.info(tip[mode])
  }
}

function zoom(delta: number): void {
  if (delta > 0) mapStore.mapInstance?.zoomIn()
  else mapStore.mapInstance?.zoomOut()
}

function snapshot(): void {
  if (!mapStore.mapInstance) return
  doExport('image', { map: mapStore.mapInstance })
  ElMessage.success('图纸图片已导出（样例数据）')
}
</script>

<template>
  <div class="map-toolbar">
    <el-tooltip content="放大" placement="bottom">
      <el-button size="small" @click="zoom(1)">＋</el-button>
    </el-tooltip>
    <el-tooltip content="缩小" placement="bottom">
      <el-button size="small" @click="zoom(-1)">－</el-button>
    </el-tooltip>
    <span class="map-toolbar__divider" />
    <el-tooltip v-for="t in tools" :key="t.mode" :content="t.label" placement="bottom">
      <el-button
        size="small"
        :type="mapStore.toolMode === t.mode ? 'primary' : 'default'"
        @click="onTool(t.mode)"
      >
        {{ t.icon }}
      </el-button>
    </el-tooltip>
    <span class="map-toolbar__divider" />
    <el-tooltip content="导出图纸图片" placement="bottom">
      <el-button size="small" @click="snapshot">📷</el-button>
    </el-tooltip>
  </div>
</template>

<style scoped>
.map-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 8px;
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border: 1px solid var(--glass-border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glass);
}
.map-toolbar :deep(.el-button) {
  background: transparent;
  border-color: transparent;
  color: var(--text-regular);
}
.map-toolbar :deep(.el-button:hover),
.map-toolbar :deep(.el-button:focus) {
  background: var(--bg-hover);
  border-color: var(--glass-border-soft);
  color: var(--brand-dark-2);
}
.map-toolbar :deep(.el-button--primary) {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.map-toolbar__divider {
  width: 1px;
  height: 16px;
  background: var(--glass-border-soft);
  margin: 0 3px;
}
</style>
