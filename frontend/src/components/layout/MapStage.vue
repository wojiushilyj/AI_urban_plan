<script setup lang="ts">
/**
 * 中央地图舞台（模块 5）：
 * MapLibre 初始化、底图切换、结果渲染、测量、弹窗、图例、工具条。
 */
import { computed, onMounted, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import { ElMessage } from 'element-plus'
import { useMap, TIANDITU_AVAILABLE } from '../../composables/useMap'
import { useMapLayers } from '../../composables/useMapLayers'
import { useMeasure } from '../../composables/useMeasure'
import { useMapStore } from '../../store/map'
import { useAppStore } from '../../store/app'
import { useScenarioStore } from '../../store/scenario'
import MapToolbar from '../map/MapToolbar.vue'
import BasemapControl from '../map/BasemapControl.vue'
import LayerManager from '../map/LayerManager.vue'
import ParcelInfoCard from '../map/ParcelInfoCard.vue'

const container = ref<HTMLDivElement>()
const mapStore = useMapStore()
const appStore = useAppStore()
const scenario = useScenarioStore()

/** 选中地块（用于右侧贴边卡片） */
const selectedParcel = computed(
  () => mapStore.result?.candidates.find((c) => c.rank === mapStore.selectedRank) ?? null
)
/** 因子名映射（卡片显示指标得分用） */
const factorNames = computed(() => {
  const m: Record<string, string> = {}
  for (const f of scenario.detail?.factors ?? []) m[f.id] = f.name
  return m
})

const { map, init, setBasemap } = useMap()
const measure = useMeasure(() => map.value)
const layers = useMapLayers(() => map.value, {
  onParcelClick: (parcel) => {
    // 点击候选地块：选中 → 红色加粗描边 + 放大居中 + 右侧卡片
    mapStore.selectedRank = parcel.rank
  },
})

/** 把全部业务图层重新挂到当前 style（底图切换后调用） */
function reapplyAll(): void {
  if (!mapStore.result) return
  layers.renderHeat(mapStore.heatGrid!, isLayerVisible('ly-result-heat'))
  layers.renderCandidates(mapStore.result, mapStore.selectedRank, isLayerVisible('ly-candidates'))
  layers.renderBusinessLayers(mapStore.layers)
}

function isLayerVisible(id: string): boolean {
  return mapStore.layers.find((l) => l.id === id)?.visible ?? true
}

onMounted(() => {
  if (!container.value) return
  const m = init(container.value, mapStore.basemap)
  mapStore.mapInstance = m
  m.on('load', () => {
    layers.renderBusinessLayers(mapStore.layers)
  })
})

// 底图切换（模块 5.1）
watch(
  () => mapStore.basemap,
  (id) => {
    if (id !== 'osm' && !TIANDITU_AVAILABLE) {
      ElMessage.warning('未配置天地图 Key（VITE_TIANDITU_KEY），已降级 OSM 底图')
      mapStore.basemap = 'osm'
      return
    }
    setBasemap(id)
    // style 重设后所有图层被清除，等 style 加载完重挂
    map.value?.once('styledata', () => reapplyAll())
  }
)

// 计算结果渲染（模块 5.3）
watch(
  () => mapStore.result,
  (r) => {
    if (!r || !mapStore.heatGrid) return
    reapplyAll()
    // 视野适配到 AOI
    if (mapStore.aoi && map.value) {
      const ring = mapStore.aoi.coordinates[0]
      const bounds = ring.reduce(
        (b, p) => b.extend(p as [number, number]),
        new maplibregl.LngLatBounds(ring[0] as [number, number], ring[0] as [number, number])
      )
      map.value.fitBounds(bounds, { padding: 80, maxZoom: 13, duration: 800 })
    }
  }
)

// 选中地块联动（模块 5.6）：表格/地图点击 → 放大居中 + 加粗描边
watch(
  () => mapStore.selectedRank,
  (rank) => {
    if (!mapStore.result) return
    layers.renderCandidates(mapStore.result, rank, isLayerVisible('ly-candidates'))
    const c = mapStore.result.candidates.find((x) => x.rank === rank)
    if (c && map.value) {
      // fitBounds 放大居中到该地块
      const ring = c.geometry.coordinates[0]
      const bounds = ring.reduce(
        (b, p) => b.extend(p as [number, number]),
        new maplibregl.LngLatBounds(ring[0] as [number, number], ring[0] as [number, number])
      )
      map.value.fitBounds(bounds, { padding: 140, maxZoom: 16, duration: 600 })
    }
  }
)

// 业务图层开关（模块 5.2）
watch(
  () => mapStore.layers,
  (ls) => {
    layers.renderBusinessLayers(ls)
    // 热力图 / 候选图层可见性
    const m = map.value
    if (!m) return
    if (m.getLayer('heat-layer')) {
      m.setLayoutProperty('heat-layer', 'visibility', isLayerVisible('ly-result-heat') ? 'visible' : 'none')
    }
    if (m.getLayer('candidates-fill')) {
      m.setLayoutProperty('candidates-fill', 'visibility', isLayerVisible('ly-candidates') ? 'visible' : 'none')
      m.setLayoutProperty('candidates-line', 'visibility', isLayerVisible('ly-candidates') ? 'visible' : 'none')
    }
  },
  { deep: true }
)

// 工具模式切换（测量）
watch(
  () => mapStore.toolMode,
  (mode) => {
    if (mode === 'pan') return
    if (mode === 'measure-dist' || mode === 'measure-area') {
      const kind = mode === 'measure-dist' ? 'dist' : 'area'
      measure.start(
        kind,
        (r) => {
          const v = r.type === 'dist' ? `${(r.value / 1000).toFixed(2)} km` : `${(r.value / 1_000_000).toFixed(2)} km²`
          appStore.setStatus(r.type === 'dist' ? `距离：${v}` : `面积：${v}`, 0)
        },
        () => {
          mapStore.toolMode = 'pan'
        }
      )
    }
  }
)
</script>

<template>
  <div ref="container" class="map-stage">
    <MapToolbar class="map-stage__toolbar" />
    <div class="map-stage__tr">
      <BasemapControl />
      <LayerManager />
    </div>
    <ParcelInfoCard
      class="map-stage__parcel-card"
      :parcel="selectedParcel"
      :factor-names="factorNames"
      @close="mapStore.selectedRank = null"
    />
  </div>
</template>

<style scoped>
.map-stage {
  position: relative;
  width: 100%;
  height: 100%;
}
.map-stage :deep(canvas) {
  outline: none;
}
.map-stage__toolbar {
  position: absolute;
  top: var(--gap-md);
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}
.map-stage__tr {
  position: absolute;
  top: var(--gap-md);
  right: var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  z-index: 10;
  align-items: flex-end;
}
.map-stage__parcel-card {
  position: absolute;
  bottom: var(--gap-md);
  right: var(--gap-md);
  z-index: 20;
}
</style>
