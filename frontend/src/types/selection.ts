/** 选址计算类型（对齐 backend/app/schemas/selection.py） */
import type { Polygon } from 'geojson'

export interface SelectionRequest {
  scenario_id: string
  /** 研究区 GeoJSON Polygon，EPSG:4490 */
  aoi: Polygon
  grid_size_m: number
  min_area_ha: number
  top_n: number
  /** AHP 主观权重占比（0-1），后端预留 */
  alpha: number
  weights_override?: Record<string, number>
  /** 前端扩展：算法选型（模块清单 4.5，后端暂未实现） */
  algorithm?: 'topsis' | 'regression' | 'kmeans'
}

export interface CandidateParcel {
  rank: number
  score: number
  area_ha: number
  geometry: Polygon
  factors: Record<string, number>
  notes: string
  /** mock 扩展：聚类分组（K-Means 演示用） */
  cluster?: number
}

export interface SelectionResponse {
  task_id: string
  scenario_id: string
  grid_size_m: number
  total_cells: number
  available_cells: number
  candidates: CandidateParcel[]
  message: string
}

/** 运行进度阶段 */
export interface RunStage {
  label: string
  percent: number
}
