<script setup lang="ts">
/**
 * 地图工具条（模块 5.4）：缩放、要素查询、测距、测面积、出图。
 * 查询与测量均为独立模式（mapStore.toolMode）。
 */
import { ElMessage } from 'element-plus'
import { useMapStore } from '../../store/map'
import { doExport } from '../../api/export'

const mapStore = useMapStore()

const tools = [
  // icon 为空表示该按钮使用内联 SVG（见模板），其余用 emoji
  { mode: 'identify', icon: '', label: '要素信息查询（单击图层要素弹出属性卡片）' },
  { mode: 'measure-dist', icon: '📏', label: '测量距离（点击加点，双击结束）' },
  { mode: 'measure-area', icon: '📐', label: '测量面积（至少 3 点，双击结束）' },
] as const

/** 各工具模式激活时的操作提示 */
const TIPS: Record<string, string> = {
  identify: '单击地图上的图层要素，弹出信息卡片；点击空白处关闭',
  'measure-dist': '点击地图加点，双击结束测距',
  'measure-area': '点击地图加点（至少 3 点），双击结束测面积',
}

function onTool(mode: (typeof tools)[number]['mode']): void {
  mapStore.toolMode = mapStore.toolMode === mode ? 'pan' : mode
  if (mapStore.toolMode !== 'pan') ElMessage.info(TIPS[mode])
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
        <!-- 要素查询用鼠标指针图形（SVG 描边随主题色，比 emoji 更贴合"单击拾取"语义） -->
        <svg
          v-if="t.mode === 'identify'"
          class="map-toolbar__icon"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path d="M4 4l7.07 17 2.51-7.39L21 11.07 4 4z" fill="currentColor" />
        </svg>
        <template v-else>{{ t.icon }}</template>
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
.map-toolbar__icon {
  display: block;
  width: 14px;
  height: 14px;
  fill: currentColor;
}
.map-toolbar__divider {
  width: 1px;
  height: 16px;
  background: var(--glass-border-soft);
  margin: 0 3px;
}
</style>
