/** 场景模板类型（对齐 backend/app/services/scenarios.py） */

/** 硬性约束：布尔一票否决 */
export interface Constraint {
  id: string
  name: string
  /** 缓冲距离（米），0 = 几何本身即禁区 */
  buffer_m: number
  /** True = 不可关闭 */
  required: boolean
}

/** 软因子 direction: +1 越大越好 / -1 越小越好 / 2 区间型 */
export interface Factor {
  id: string
  name: string
  direction: 1 | -1 | 2
  unit: string
}

export interface ScenarioSummary {
  id: string
  name: string
  category: string
  description: string
}

export interface ScenarioDetail extends ScenarioSummary {
  constraints: Constraint[]
  factors: Factor[]
  weights_ahp: Record<string, number>
}

export type WeightMap = Record<string, number>
