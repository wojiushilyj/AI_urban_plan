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
import { detectWebgl } from '../../utils/webgl'
import { OSM_PROBE_TILE, probeRasterTile } from '../../utils/tile'
import MapToolbar from '../map/MapToolbar.vue'
import BasemapControl from '../map/BasemapControl.vue'
import LayerManager from '../map/LayerManager.vue'
import ParcelInfoCard from '../map/ParcelInfoCard.vue'
import FeatureInfoCard from '../map/FeatureInfoCard.vue'

const container = ref<HTMLDivElement>()
const mapStore = useMapStore()
const appStore = useAppStore()
const scenario = useScenarioStore()

/** WebGL 探测结果（MapLibre GL 强依赖 WebGL，不可用则整块地图无法渲染） */
const webgl = detectWebgl()
/** 非空即表示地图无法渲染，模板改为显示说明面板而不是一片白 */
const mapIssue = ref('')

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
  if (!webgl.supported) {
    mapIssue.value = '浏览器未提供 WebGL 上下文'
    // eslint-disable-next-line no-console
    console.warn('[MapStage] WebGL 不可用，地图无法渲染。请检查 edge://gpu 或 chrome://gpu 的 WebGL 状态。')
    return
  }
  try {
    const m = init(container.value, mapStore.basemap)
    mapStore.mapInstance = m
    m.on('load', () => {
      layers.renderGeoLayers(mapStore.layers)
      // 要素查询的点击监听挂在 map 上（不绑定具体图层），底图切换重建 style 后依然有效
      m.on('click', onMapClick)
    })

    // 瓦片加载失败兜底：天地图 Key 失效/欠额，或被网络/WAF 拦截时切到 OSM。
    // 实测：天地图会按发起请求的 IP 做风控（云机房 IP 返回 418「疑似攻击行为」），
    // 而 OSM 在境外出口可达、国内直连超时 —— 两边都可能不通，故切换前先探测 OSM。
    let tileErrors = 0
    let downgraded = false

    async function fallbackToOsm(): Promise<void> {
      const reachable = await probeRasterTile(OSM_PROBE_TILE)
      if (reachable) {
        ElMessage.warning('天地图瓦片被当前网络拦截，已自动切换为 OSM 底图')
        mapStore.basemap = 'osm'
      } else {
        ElMessage.error('底图不可用：天地图被当前网络拦截，OSM 也不可达。请更换网络，或从能正常访问天地图的电脑打开本系统')
      }
    }

    m.on('error', (ev) => {
      const sourceId = (ev as { sourceId?: string }).sourceId
      if (sourceId !== 'tdt' && sourceId !== 'tdtAnno') return
      tileErrors += 1
      if (tileErrors === 1) {
        // eslint-disable-next-line no-console
        console.warn('[MapStage] 天地图瓦片请求失败：', (ev as { error?: Error }).error)
      }
      if (tileErrors >= 4 && !downgraded && mapStore.basemap !== 'osm') {
        downgraded = true
        void fallbackToOsm()
      }
    })
  } catch (e) {
    mapIssue.value = e instanceof Error ? e.message : String(e)
  }
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
    <div class="map-stage__tl">
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

    <div v-if="mapIssue" class="map-stage__fallback">
      <div class="map-stage__fallback-box">
        <h3>当前环境无法渲染地图</h3>
        <p class="map-stage__fallback-reason">
          检测结果：{{ mapIssue }}<span v-if="webgl.renderer">（渲染器：{{ webgl.renderer }}）</span>
        </p>
        <p>
          本系统地图基于 MapLibre GL，需要浏览器支持 <b>WebGL</b>。无独立显卡的云服务器 / 虚拟机，
          以及关闭了硬件加速的浏览器，会禁用 WebGL，症状正是整块地图全白。
        </p>
        <p class="map-stage__fallback-title">可以这样解决：</p>
        <ol>
          <li>在浏览器地址栏打开 <code>edge://gpu</code>（Chrome 为 <code>chrome://gpu</code>），查看 WebGL 一行是否为 Disabled。</li>
          <li>给浏览器加启动参数 <code>--enable-unsafe-swiftshader</code>，用软件方式渲染 WebGL。</li>
          <li>换用 Firefox 打开本页试试。</li>
          <li>或者最简单：<b>从另一台电脑</b>访问本服务的公网地址。</li>
        </ol>
        <p class="map-stage__fallback-note">
          AI 需求解析、选址计算、报告导出等功能不依赖 WebGL，在上方各面板中可正常使用。
        </p>
      </div>
    </div>
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
/* 底图选择 + 图层选择：地图左上角（用户要求移到最左侧） */
.map-stage__tl {
  position: absolute;
  top: var(--gap-md);
  left: var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  z-index: 10;
  align-items: flex-start;
}
.map-stage__parcel-card {
  position: absolute;
  bottom: var(--gap-md);
  right: var(--gap-md);
  z-index: 20;
}
/* WebGL 不可用时的说明面板（覆盖地图区域，避免一片白无从判断） */
.map-stage__fallback {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
}
.map-stage__fallback-box {
  max-width: 560px;
  padding: 20px 24px;
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  background: var(--bg-panel);
  box-shadow: var(--shadow-md);
  color: var(--text-regular);
  font-size: 13px;
  line-height: 1.7;
}
.map-stage__fallback-box h3 {
  margin: 0 0 10px;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
}
.map-stage__fallback-box p {
  margin: 0 0 8px;
}
.map-stage__fallback-reason {
  color: var(--c-warning);
}
.map-stage__fallback-title {
  margin-top: 12px !important;
  color: var(--text-primary);
  font-weight: 600;
}
.map-stage__fallback-box ol {
  margin: 0 0 8px;
  padding-left: 20px;
}
.map-stage__fallback-box li {
  margin-bottom: 4px;
}
.map-stage__fallback-box code {
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
}
.map-stage__fallback-note {
  margin-top: 12px !important;
  color: var(--text-secondary);
}
</style>
