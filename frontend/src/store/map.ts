/** 地图状态：底图、图层分组开关、AOI、选中地块、弹窗（模块 5） */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Polygon } from 'geojson'
import type { CandidateParcel, SelectionResponse } from '../types/selection'
import { LAYER_URLS } from '../api/layers'

export type BasemapId = 'osm' | 'tianditu-vec' | 'tianditu-img'

/** 业务图层（真实 GeoJSON 图层 + 结果图层） */
export interface BusinessLayer {
  id: string
  name: string
  /** 所属大类 id（见 LayerGroup） */
  groupId: string
  visible: boolean
  /** 图层类型：geojson=真实数据静态加载；heat/candidates=计算结果动态渲染 */
  kind: 'geojson' | 'heat' | 'candidates'
  /** geojson 静态路径（仅 kind='geojson'） */
  sourceUrl?: string
}

/** 图层大类（可展开/收缩 + 总开关） */
export interface LayerGroup {
  id: string
  name: string
  expanded: boolean
}

/** 工具条「要素查询」模式下的单次拾取结果 */
export interface FeaturePick {
  /** 图层显示名（如「道路路网」） */
  layerName: string
  /** 几何类型中文（面 / 线 / 点） */
  geomLabel: string
  /** 要素属性（已剔除内部字段） */
  properties: Record<string, unknown>
  /** 几何体量测文案（面→面积 / 线→长度），无适用项时为 null */
  measure: string | null
  /** 点击位置：屏幕坐标（相对地图容器，像素） */
  screen: { x: number; y: number }
  /** 点击位置：经纬度文案（WGS84，保留 6 位小数） */
  lngLat: string
}

export const useMapStore = defineStore('map', () => {
  const basemap = ref<BasemapId>('tianditu-vec')
  /** MapLibre 实例（非序列化，仅运行时引用） */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mapInstance = ref<any>(null)

  /** 图层大类（顺序即展示顺序），默认全部折叠；选址结果类默认展开 */
  const groups = ref<LayerGroup[]>([
    { id: 'baseline', name: '底线管控', expanded: false },
    { id: 'control-line', name: '城市控制线', expanded: false },
    { id: 'industry', name: '产业用地', expanded: false },
    { id: 'facility', name: '服务与设施', expanded: false },
    // 交通类图层与原 4 大类语义不重合，单独成类（2026-09-10 新增）
    { id: 'transport', name: '交通设施', expanded: false },
    { id: 'result', name: '选址结果', expanded: true },
  ])

  /** 业务图层（真实 16 个），默认全部关闭，用户手动开启；路径统一由 api/layers.ts 维护 */
  const layers = ref<BusinessLayer[]>([
    // 底线管控
    { id: 'perm-farmland', name: '永久基本农田', groupId: 'baseline', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['perm-farmland'] },
    { id: 'eco-redline', name: '生态保护红线', groupId: 'baseline', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['eco-redline'] },
    { id: 'urban-boundary', name: '城镇开发边界', groupId: 'baseline', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['urban-boundary'] },
    // 城市控制线
    { id: 'yellow-line', name: '城市黄线', groupId: 'control-line', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['yellow-line'] },
    { id: 'blue-line', name: '城市蓝线', groupId: 'control-line', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['blue-line'] },
    { id: 'green-line', name: '城市绿线', groupId: 'control-line', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['green-line'] },
    // 产业用地
    { id: 'industrial-land', name: '总规工业用地', groupId: 'industry', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['industrial-land'] },
    { id: 'current-industrial-land', name: '临桂现状工业用地', groupId: 'industry', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['current-industrial-land'] },
    { id: 'regulated-industrial', name: '控规工业用地', groupId: 'industry', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['regulated-industrial'] },
    { id: 'industrial-park', name: '产业园区边界', groupId: 'industry', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['industrial-park'] },
    // 交通设施
    { id: 'road-network', name: '道路路网', groupId: 'transport', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['road-network'] },
    { id: 'highway-interchange', name: '高速出入口', groupId: 'transport', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['highway-interchange'] },
    { id: 'freight-station', name: '货运场站用地', groupId: 'transport', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['freight-station'] },
    // 服务与设施
    { id: 'prod-service-point', name: '生产性服务点位（点）', groupId: 'facility', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['prod-service-point'] },
    { id: 'prod-service-area', name: '生产性服务点位（面）', groupId: 'facility', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['prod-service-area'] },
    { id: 'cultural-relic', name: '文物保护单位', groupId: 'facility', visible: false, kind: 'geojson', sourceUrl: LAYER_URLS['cultural-relic'] },
    // 选址结果（分析完成后由 useMapLayers 动态渲染，默认开启）
    { id: 'candidates', name: '候选地块', groupId: 'result', visible: true, kind: 'candidates' },
    { id: 'candidate-labels', name: '地块序号', groupId: 'result', visible: true, kind: 'candidates' },
  ])

  /** 研究区：固定为桂林市临桂区（简化边界，样例数据） */
  const LINGUI_AOI: Polygon = {
    type: 'Polygon',
    coordinates: [[[110.0, 25.0], [110.42, 25.0], [110.42, 25.5], [110.0, 25.5], [110.0, 25.0]]],
  }
  const aoi = ref<Polygon | null>(LINGUI_AOI)
  /** 当前计算结果（渲染用） */
  const result = ref<SelectionResponse | null>(null)

  /** 选中的候选地块（地图-面板联动，模块 5.6） */
  const selectedRank = ref<number | null>(null)
  /** 弹窗状态 */
  const popupParcel = ref<CandidateParcel | null>(null)

  /** 要素查询（工具条）拾取到的要素信息；null = 未拾取 / 卡片关闭 */
  const featurePick = ref<FeaturePick | null>(null)

  /** 工具模式：pan | identify（要素查询）| measure-dist | measure-area */
  const toolMode = ref<'pan' | 'identify' | 'measure-dist' | 'measure-area'>('pan')

  function toggleLayer(id: string): void {
    const l = layers.value.find((x) => x.id === id)
    if (l) l.visible = !l.visible
  }

  /** 大类总开关：全开 → 全关；否则 → 全开 */
  function toggleGroup(groupId: string): void {
    const ls = layers.value.filter((x) => x.groupId === groupId)
    if (!ls.length) return
    const allOn = ls.every((x) => x.visible)
    ls.forEach((x) => { x.visible = !allOn })
  }

  /** 大类展开/收缩 */
  function toggleGroupExpand(groupId: string): void {
    const g = groups.value.find((x) => x.id === groupId)
    if (g) g.expanded = !g.expanded
  }

  /** 大类是否全开（用于总开关状态） */
  function isGroupAllOn(groupId: string): boolean {
    const ls = layers.value.filter((x) => x.groupId === groupId)
    return ls.length > 0 && ls.every((x) => x.visible)
  }

  /** 某大类开启的图层数 */
  function groupOnCount(groupId: string): number {
    return layers.value.filter((x) => x.groupId === groupId && x.visible).length
  }

  /** 指定图层是否开启（渲染层读取可见性用） */
  function layerVisible(id: string): boolean {
    return layers.value.find((x) => x.id === id)?.visible ?? false
  }

  function setAoi(poly: Polygon | null): void {
    aoi.value = poly
  }

  return {
    basemap, mapInstance, groups, layers, aoi, result,
    selectedRank, popupParcel, toolMode, featurePick,
    toggleLayer, toggleGroup, toggleGroupExpand, isGroupAllOn, groupOnCount, layerVisible, setAoi,
  }
})
