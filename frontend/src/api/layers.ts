/**
 * 真实空间图层统一入口（/data/layers/*.geojson）。
 *
 * 单一数据源：地图渲染（useMapLayers）与选址计算（mock/candidates）共用同一份缓存，
 * 避免同一图层被重复下载（永久基本农田约 7.2 MB）。
 * 数据来源与坐标系见 data/README.md。
 */
import type { Feature, FeatureCollection, Geometry } from 'geojson'

/** 图层 id → 静态资源路径（与 store/map.ts 的业务图层一一对应） */
export const LAYER_URLS = {
  'perm-farmland': '/data/layers/perm-farmland.geojson',
  'eco-redline': '/data/layers/eco-redline.geojson',
  'urban-boundary': '/data/layers/urban-boundary.geojson',
  'yellow-line': '/data/layers/yellow-line.geojson',
  'blue-line': '/data/layers/blue-line.geojson',
  'green-line': '/data/layers/green-line.geojson',
  'industrial-land': '/data/layers/industrial-land.geojson',
  'current-industrial-land': '/data/layers/current-industrial-land.geojson',
  'regulated-industrial': '/data/layers/regulated-industrial.geojson',
  'industrial-park': '/data/layers/industrial-park.geojson',
  // 交通设施（2026-09-10 新增，原 4 大类无法归类，单独成类）
  'road-network': '/data/layers/road-network.geojson',
  'highway-interchange': '/data/layers/highway-interchange.geojson',
  'freight-station': '/data/layers/freight-station.geojson',
  'prod-service-point': '/data/layers/prod-service-point.geojson',
  'prod-service-area': '/data/layers/prod-service-area.geojson',
  'cultural-relic': '/data/layers/cultural-relic.geojson',
  // 市政设施 / 现状建设（2026-09-11 新增，各自单独成类）
  'municipal-land': '/data/layers/municipal-land.geojson',
  'current-building': '/data/layers/current-building.geojson',
} as const

export type LayerId = keyof typeof LAYER_URLS

/** 图层要素集合 */
export type LayerFeatures = FeatureCollection<Geometry>

/** 图层要素 */
export type LayerFeature = Feature<Geometry>

const ALL_LAYER_IDS = Object.keys(LAYER_URLS) as LayerId[]

/** 是否为本项目登记的图层 id */
export function isLayerId(id: string): id is LayerId {
  return (ALL_LAYER_IDS as string[]).includes(id)
}

/** 请求缓存（同一图层只下载一次；失败即移除，允许重试） */
const pending = new Map<LayerId, Promise<LayerFeatures>>()

/** 加载单个图层（带缓存） */
export function loadLayer(id: LayerId): Promise<LayerFeatures> {
  const hit = pending.get(id)
  if (hit) return hit
  const task = fetch(LAYER_URLS[id])
    .then(async (resp) => {
      if (!resp.ok) throw new Error(`图层「${id}」加载失败：HTTP ${resp.status}`)
      return (await resp.json()) as LayerFeatures
    })
    .catch((e: unknown) => {
      pending.delete(id)
      throw e
    })
  pending.set(id, task)
  return task
}

/** 并发加载多个图层 */
export function loadLayers(ids: LayerId[]): Promise<LayerFeatures[]> {
  return Promise.all(ids.map((id) => loadLayer(id)))
}
