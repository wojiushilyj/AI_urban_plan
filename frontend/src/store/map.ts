/** 地图状态：底图、图层开关、AOI、选中地块、弹窗（模块 5） */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { FeatureCollection, Polygon } from 'geojson'
import type { CandidateParcel, SelectionResponse } from '../types/selection'

export type BasemapId = 'osm' | 'tianditu-vec' | 'tianditu-img'

export interface BusinessLayer {
  id: string
  name: string
  visible: boolean
}

export const useMapStore = defineStore('map', () => {
  const basemap = ref<BasemapId>('tianditu-vec')
  /** MapLibre 实例（非序列化，仅运行时引用） */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapInstance = ref<any>(null)

  /** 国土业务图层开关（模块 5.2，样例示意） */
  const layers = ref<BusinessLayer[]>([
    { id: 'ly-prime-farmland', name: '永久基本农田（示意）', visible: false },
    { id: 'ly-eco-redline', name: '生态保护红线（示意）', visible: false },
    { id: 'ly-river', name: '河湖管理范围（示意）', visible: false },
    { id: 'ly-road', name: '路网', visible: false },
    { id: 'ly-udb', name: '城镇开发边界（示意）', visible: false },
    { id: 'ly-result-heat', name: '适宜度热力图', visible: true },
    { id: 'ly-candidates', name: '候选地块', visible: true },
  ])

  /** 研究区：固定为桂林市临桂区（简化边界，样例数据） */
  const LINGUI_AOI: Polygon = {
    type: 'Polygon',
    coordinates: [[[110.0, 25.0], [110.42, 25.0], [110.42, 25.5], [110.0, 25.5], [110.0, 25.0]]],
  }
  const aoi = ref<Polygon | null>(LINGUI_AOI)
  /** 当前计算结果（渲染用） */
  const result = ref<SelectionResponse | null>(null)
  const heatGrid = ref<FeatureCollection<Polygon, { weight: number }> | null>(null)

  /** 选中的候选地块（地图-面板联动，模块 5.6） */
  const selectedRank = ref<number | null>(null)
  /** 弹窗状态 */
  const popupParcel = ref<CandidateParcel | null>(null)

  /** 绘制/工具模式：pan | measure-dist | measure-area */
  const toolMode = ref<'pan' | 'measure-dist' | 'measure-area'>('pan')

  function toggleLayer(id: string): void {
    const l = layers.value.find((x) => x.id === id)
    if (l) l.visible = !l.visible
  }

  function setAoi(poly: Polygon | null): void {
    aoi.value = poly
  }

  return {
    basemap, mapInstance, layers, aoi, result, heatGrid,
    selectedRank, popupParcel, toolMode,
    toggleLayer, setAoi,
  }
})
