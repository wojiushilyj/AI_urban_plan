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
  /** 用地规模目标（公顷）：用户在 AI 聊天中提到占地面积时解析得到；不传则不做面积匹配 */
  target_area_ha?: number
  /** 用地规模容差（±比例，0–1）。初期限定 0.5（±50%），具体限值由后端算法设计人员核定 */
  area_tolerance?: number
}

export interface CandidateParcel {
  rank: number
  score: number
  area_ha: number
  geometry: Polygon
  factors: Record<string, number>
  notes: string
  /** 聚类分组（K-Means 演示用）：0 优先开发类 / 1 条件适合类 / 2 储备备用类 */
  cluster?: number
  /** 地块编码（由来源图层 + 要素序号生成，如 KG-065；展示在地块详细卡片中） */
  code?: string
  /** 来源图层名称（当前固定为「控规工业用地」） */
  source?: string
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
