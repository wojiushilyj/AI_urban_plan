/** 选址计算类型（对齐 backend/app/schemas/selection.py） */
import type { Polygon } from 'geojson'

/** 权重来源：expert=AHP+熵权（专家知识）/ learned=AI 学习权重 / blended=各半 */
export type WeightMode = 'expert' | 'learned' | 'blended'

export interface SelectionRequest {
  scenario_id: string
  /** 研究区 GeoJSON Polygon，EPSG:4490 */
  aoi: Polygon
  grid_size_m: number
  min_area_ha: number
  top_n: number
  /** AHP 主观权重占比（0-1） */
  alpha: number
  weights_override?: Record<string, number>
  /** 权重来源（AI 能力的接入点） */
  weight_mode?: WeightMode
  /** 显式启用的硬约束 id；不传则默认只启用模板中 required 的约束 */
  constraints?: string[]
  /** 算法选型（模块清单 4.5） */
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

  /** 因子贡献分解（留一法，可解释 AI）：正值 = 优势，负值 = 短板 */
  contributions?: Record<string, number>
  /** 贡献最大的正项（主导优势） */
  top_driver?: string
  /** 贡献最小的负项（主要短板） */
  top_weakness?: string
  /** 地块内现状建筑占地率（拆迁量代理），0–1 */
  build_density?: number
  /** 权重扰动下该地块保持在 Top-N 的概率（0–1，蒙特卡洛 200 次） */
  robustness?: number
}

export interface SelectionResponse {
  task_id: string
  scenario_id: string
  grid_size_m: number
  total_cells: number
  available_cells: number
  candidates: CandidateParcel[]
  message: string
  /** 本次实际生效的权重 */
  weights?: Record<string, number>
  /** 对照用专家权重（AHP + 熵权） */
  expert_weights?: Record<string, number>
  /** 本次权重来源 */
  weight_mode?: WeightMode
  /** 权重来源的中文说明 */
  weight_source?: string
  /** 各因子的全局平均绝对贡献（留一法） */
  sensitivity?: Record<string, number>
  /** 蒙特卡洛稳健性摘要 */
  robustness?: {
    samples: number
    top_n: number
    prob_top_n: number[]
    mean_stability: number
  }
}

/** 运行进度阶段 */
export interface RunStage {
  label: string
  percent: number
}
