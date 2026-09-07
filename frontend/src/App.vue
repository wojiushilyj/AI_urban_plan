<script setup lang="ts">
/**
 * 主界面骨架。
 *
 * 布局：左侧场景与参数面板 / 中间地图 / 右侧结果与报告。
 * 地图使用 MapLibre GL JS（开源免 Key），底图可切换 OSM 栅格或天地图 WMTS。
 *
 * TODO(09-11)：接入 /api/selection/run，实现绘制 AOI → 分析 → 渲染热力图 → Top-N 候选地块。
 */
import { onMounted, ref } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { api } from './api'

const mapContainer = ref<HTMLDivElement>()
const health = ref('检查中…')
const scenarios = ref<any[]>([])

onMounted(async () => {
  // 广西大致范围，演示默认视野
  new maplibregl.Map({
    container: mapContainer.value!,
    style: {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors'
        }
      },
      layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
    },
    center: [108.3665, 22.8170], // 南宁
    zoom: 9
  })

  try {
    const r = await api.get('/health')
    health.value = JSON.stringify(r.data)
  } catch (e: any) {
    health.value = '后端未启动：' + e.message
  }

  try {
    const r = await api.get('/api/scenarios')
    scenarios.value = r.data.items
  } catch {
    scenarios.value = []
  }
})
</script>

<template>
  <div class="layout">
    <aside class="panel">
      <h2>选址场景</h2>
      <el-select placeholder="选择场景" style="width: 100%" value-key="id">
        <el-option v-for="s in scenarios" :key="s.id" :label="s.name" :value="s" />
      </el-select>
      <p class="hint">后端状态：{{ health }}</p>
      <p class="hint">流程：绘制研究区 → 设置权重 → 一键分析 → 查看 Top-N 候选地块</p>
    </aside>

    <main ref="mapContainer" class="map"></main>

    <aside class="panel">
      <h2>分析结果</h2>
      <p class="hint">（09-12 联调后展示候选地块与适宜性得分）</p>
    </aside>
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; width: 100%; }
.panel { width: 280px; padding: 16px; box-sizing: border-box; border-right: 1px solid #e5e7eb; background: #fff; }
.panel:last-child { border-right: none; border-left: 1px solid #e5e7eb; }
.map { flex: 1; }
.hint { font-size: 12px; color: #6b7280; line-height: 1.6; }
h2 { font-size: 15px; margin: 0 0 12px; }
</style>
