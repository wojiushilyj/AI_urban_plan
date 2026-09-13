/**
 * MapLibre 地图实例管理 + 底图切换（模块 5.1）。
 * 底图：OSM 栅格（默认，免 Key）/ 天地图矢量 / 天地图影像（需 VITE_TIANDITU_KEY）。
 */
import { onUnmounted, shallowRef } from 'vue'
import maplibregl from 'maplibre-gl'
import type { Map as MlMap } from 'maplibre-gl'
import type { FeatureCollection, Polygon } from 'geojson'
import type { BasemapId } from '../store/map'

const TIANDITU_KEY: string = import.meta.env.VITE_TIANDITU_KEY ?? ''
export const TIANDITU_AVAILABLE: boolean = TIANDITU_KEY.length > 0

/** 桂林市临桂区 */
export const DEFAULT_CENTER: [number, number] = [110.2, 25.24]
export const DEFAULT_ZOOM = 11

export interface BasemapDef {
  id: BasemapId
  name: string
  available: boolean
}

export const BASEMAPS: BasemapDef[] = [
  { id: 'osm', name: 'OSM', available: true },
  { id: 'tianditu-vec', name: '矢量', available: TIANDITU_AVAILABLE },
  { id: 'tianditu-img', name: '影像', available: TIANDITU_AVAILABLE },
]

/** 按底图 id 解析样式（天地图无 Key 时回退 OSM） */
function resolveStyle(id: BasemapId): maplibregl.StyleSpecification {
  if (id === 'tianditu-vec' && TIANDITU_AVAILABLE) return tiandituStyle('vec_w', 'cva_w')
  if (id === 'tianditu-img' && TIANDITU_AVAILABLE) return tiandituStyle('img_w', 'cia_w')
  return osmStyle()
}

function osmStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: [{ id: 'osm-base', type: 'raster', source: 'osm' }],
  }
}

function tiandituStyle(layer: 'vec_w' | 'img_w', anno: 'cva_w' | 'cia_w'): maplibregl.StyleSpecification {
  const data = (t: string) =>
    [0, 1, 2, 3, 4, 5, 6, 7].map(
      (i) => `https://t${i}.tianditu.gov.cn/DataServer?T=${t}&x={x}&y={y}&l={z}&tk=${TIANDITU_KEY}`
    )
  return {
    version: 8,
    sources: {
      tdt: { type: 'raster', tiles: data(layer), tileSize: 256, attribution: '© 天地图'},
      tdtAnno: { type: 'raster', tiles: data(anno), tileSize: 256, attribution: '© 天地图' },
    },
    layers: [
      { id: 'tdt-base', type: 'raster', source: 'tdt' },
      { id: 'tdt-anno', type: 'raster', source: 'tdtAnno' },
    ],
  }
}

/** 临桂区边界示意（断网兜底：无瓦片时仍显示研究范围） */
const LINGUI_OUTLINE: FeatureCollection<Polygon, { name: string }> = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [110.02, 24.98], [110.40, 25.00], [110.44, 25.30], [110.30, 25.54],
          [110.05, 25.50], [109.98, 25.22], [110.02, 24.98],
        ]],
      },
      properties: { name: '临桂区（示意边界）' },
    },
  ],
}

export function useMap() {
  const map = shallowRef<MlMap | null>(null)
  const loaded = shallowRef(false)

  function init(container: HTMLElement, basemap: BasemapId = 'osm'): MlMap {
    const m = new maplibregl.Map({
      container,
      style: resolveStyle(basemap),
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      // 出图导出需要 preserveDrawingBuffer
      preserveDrawingBuffer: true,
      attributionControl: false,
    })
    m.on('load', () => {
      loaded.value = true
      // 兜底边界示意（瓦片加载失败时地图不至于全空）
      m.addSource('lingui-outline', { type: 'geojson', data: LINGUI_OUTLINE })
      m.addLayer({
        id: 'lingui-outline-line',
        type: 'line',
        source: 'lingui-outline',
        paint: { 'line-color': '#9CA3AF', 'line-width': 1, 'line-dasharray': [4, 3] },
      })
    })
    map.value = m
    return m
  }

  /** 切换底图（模块 5.1）：保留结果图层需由 useMapLayers 在 style 切换后重挂 */
  function setBasemap(id: BasemapId): void {
    const m = map.value
    if (!m) return
    m.setStyle(resolveStyle(id))
  }

  onUnmounted(() => {
    map.value?.remove()
    map.value = null
  })

  return { map, loaded, init, setBasemap }
}
