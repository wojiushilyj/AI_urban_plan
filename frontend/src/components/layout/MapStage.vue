<script setup lang="ts">
/**
 * 中央地图舞台（模块 5）：
 * MapLibre 初始化、底图切换、结果渲染、要素查询、测量、弹窗、图例、工具条。
 */
import { computed, onMounted, ref, watch } from 'vue'
import maplibregl from 'maplibre-gl'
import type { Geometry } from 'geojson'
import { ElMessage } from 'element-plus'
import { useMap, TIANDITU_AVAILABLE } from '../../composables/useMap'
import { useMapLayers } from '../../composables/useMapLayers'
import { useMeasure } from '../../composables/useMeasure'
import { useMapStore, type FeaturePick } from '../../store/map'
import { useAppStore } from '../../store/app'
import { useScenarioStore } from '../../store/scenario'
import { geometryMeasureText, geometryTypeLabel } from '../../utils/geo'
import { fmtScore } from '../../utils/format'
import MapToolbar from '../map/MapToolbar.vue'
import BasemapControl from '../map/BasemapControl.vue'
import LayerManager from '../map/LayerManager.vue'
import ParcelInfoCard from '../map/ParcelInfoCard.vue'
import FeatureInfoCard from '../map/FeatureInfoCard.vue'

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
    // 要素查询模式下由统一的拾取逻辑接管，避免同时弹出两张卡片
    if (mapStore.toolMode === 'identify') return
    // 点击候选地块：选中 → 红色加粗描边 + 放大居中 + 右侧卡片
    mapStore.selectedRank = parcel.rank
  },
})

/* ==================== 要素查询（工具条「🔍」模式） ==================== */

/** 把一次地图点击解析为要素信息；未命中任何要素时返回 null */
function buildPick(e: maplibregl.MapMouseEvent): FeaturePick | null {
  const hit = layers.pickTop(e, layers.pickLayers(mapStore.layers))
  if (!hit) return null

  const isCandidate = hit.layerId === 'candidates-fill'
  const def = mapStore.layers.find((l) => `${l.id}-layer` === hit.layerId)
  // 候选地块属性里的 parcel 是整份地块 JSON 字符串，剔除后只保留可读字段
  const raw = { ...hit.feature.properties } as Record<string, unknown>
  delete raw['parcel']

  const g = hit.feature.geometry as Geometry | null
  return {
    layerName: isCandidate ? '候选地块' : (def?.name ?? hit.layerId),
    geomLabel: geometryTypeLabel(g),
    properties: isCandidate
      ? {
          候选编号: `No.${String(raw['rank'] ?? '—')}`,
          综合得分: fmtScore(Number(raw['score'] ?? 0)),
          地块编码: String(raw['code'] || '—'),
        }
      : raw,
    measure: geometryMeasureText(g),
    screen: { x: e.point.x, y: e.point.y },
    lngLat: `${e.lngLat.lng.toFixed(6)}, ${e.lngLat.lat.toFixed(6)}`,
  }
}

function onMapClick(e: maplibregl.MapMouseEvent): void {
  if (mapStore.toolMode !== 'identify') return
  // 命中要素则弹出卡片；点击空白处等价于关闭卡片
  mapStore.featurePick = buildPick(e)
}

/** 候选地块图层的可见性（由图层面板「选址结果」大类控制） */
const candidateVis = computed(() => ({
  parcels: mapStore.layerVisible('candidates'),
  labels: mapStore.layerVisible('candidate-labels'),
}))

/** 把全部业务图层重新挂到当前 style（底图切换后调用） */
async function reapplyAll(): Promise<void> {
  // 真实业务图层始终重挂（不依赖计算结果）；必须等它加载完再画候选地块，
  // 否则懒加载的大图层会晚一步挂上来、盖住候选地块（图层顺序 = 添加顺序）
  await layers.renderGeoLayers(mapStore.layers)
  if (!mapStore.result) return
  layers.renderCandidates(mapStore.result, mapStore.selectedRank, candidateVis.value)
}

onMounted(() => {
  if (!container.value) return
  const m = init(container.value, mapStore.basemap)
  mapStore.mapInstance = m
  m.on('load', () => {
    layers.renderGeoLayers(mapStore.layers)
    // 要素查询的点击监听挂在 map 上（不绑定具体图层），底图切换重建 style 后依然有效
    m.on('click', onMapClick)
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
    if (!r) return
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
    layers.renderCandidates(mapStore.result, rank, candidateVis.value)
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

// 业务图层 / 候选地块图层开关（模块 5.2）
watch(
  () => mapStore.layers,
  async (ls) => {
    await layers.renderGeoLayers(ls)
    // 选址结果图层的可见性也由面板控制（放最后，保证候选地块在最上层）
    if (mapStore.result) {
      layers.renderCandidates(mapStore.result, mapStore.selectedRank, candidateVis.value)
    }
  },
  { deep: true }
)

// 工具模式切换（要素查询 / 测量，三者互斥）
watch(
  () => mapStore.toolMode,
  (mode) => {
    const m = map.value
    // 离开测量模式时务必收尾：否则监听残留、active 卡在 true，后续无法再次启动测量
    if (mode !== 'measure-dist' && mode !== 'measure-area') measure.stop()

    if (mode === 'identify') {
      // 与地块卡片互斥，避免两张卡片同时在图上
      mapStore.selectedRank = null
      if (m) m.getCanvas().style.cursor = 'pointer'
      return
    }

    if (mode === 'pan') {
      mapStore.featurePick = null
      if (m) m.getCanvas().style.cursor = ''
      return
    }

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
    <FeatureInfoCard :pick="mapStore.featurePick" @close="mapStore.featurePick = null" />
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
