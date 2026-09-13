<script setup lang="ts">
/**
 * 地图工具条（模块 5.4）：缩放、要素查询、测距、测面积、出图。
 * 查询与测量均为独立模式（mapStore.toolMode）。
 * 形态对齐设计稿 .map-toolbar：左上角 48px 竖向白卡，内部 36px 圆角按钮，选中品牌蓝底。
 */
import { ElMessage } from 'element-plus'
import { useMapStore } from '../../store/map'
import { doExport } from '../../api/export'
import AppIcon from '../common/AppIcon.vue'

const mapStore = useMapStore()

/** 工具模式项（对应原型 .tool 系列） */
const tools = [
  { mode: 'identify', icon: 'pointer', label: '要素信息查询（单击图层要素弹出属性卡片）' },
  { mode: 'measure-dist', icon: 'ruler', label: '测量距离（点击加点，双击结束）' },
  { mode: 'measure-area', icon: 'polygon', label: '测量面积（至少 3 点，双击结束）' },
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
  ElMessage.success('图纸图片已导出')
}
</script>

<template>
  <div class="map-toolbar">
    <!-- 选择 / 要素查询 -->
    <el-tooltip
      v-for="t in tools"
      :key="t.mode"
      :content="t.label"
      placement="right"
    >
      <button
        type="button"
        class="tool"
        :class="{ 'is-active': mapStore.toolMode === t.mode }"
        @click="onTool(t.mode)"
      >
        <AppIcon :name="t.icon" :size="24" />
      </button>
    </el-tooltip>

    <el-tooltip content="放大" placement="right">
      <button type="button" class="tool" @click="zoom(1)">
        <AppIcon name="zoom-in" :size="24" />
      </button>
    </el-tooltip>
    <el-tooltip content="缩小" placement="right">
      <button type="button" class="tool" @click="zoom(-1)">
        <AppIcon name="zoom-out" :size="24" />
      </button>
    </el-tooltip>

    <el-tooltip content="导出图纸图片" placement="right">
      <button type="button" class="tool" @click="snapshot">
        <AppIcon name="camera" :size="22" />
      </button>
    </el-tooltip>
  </div>
</template>

<style scoped>
/* 竖向工具卡（原型 .map-toolbar） */
.map-toolbar {
  width: 48px;
  padding: 6px;
  border-radius: var(--radius-card);
  background: #fff;
  border: 1px solid var(--border-lighter);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tool {
  width: 36px;
  height: 36px;
  border: 0;
  background: transparent;
  border-radius: 12px;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: 0.16s;
  color: var(--ink-2);
  padding: 0;
}
.tool:hover {
  background: var(--bg-subtle);
}
.tool.is-active {
  background: var(--brand);
  color: #fff;
}
</style>
