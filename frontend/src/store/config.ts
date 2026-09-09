/**
 * 配置状态：约束开关/缓冲、选址偏好（5 维度）、权重、算法选型、计算入参。
 * 权重由「选址偏好」三档（在意/一般/不在意）驱动，评分与权重统一按 5 维度进行。
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { ScenarioDetail, WeightMap } from '../types/scenario'

export type AlgorithmId = 'topsis' | 'regression' | 'kmeans'

export const ALGORITHM_OPTIONS: { id: AlgorithmId; name: string; desc: string }[] = [
  { id: 'topsis', name: 'TOPSIS', desc: '逼近理想解排序，多因子综合评价，适合候选地块排序' },
  { id: 'regression', name: '多元回归', desc: '拟合历史选址偏好，预测地块适宜度' },
  { id: 'kmeans', name: 'K-Means 聚类', desc: '按因子特征自动分组，识别同类地块片区' },
]

export interface ConstraintState {
  enabled: boolean
  buffer_m: number
}

/* ============ 选址偏好（统一 5 维度） ============ */

export type PreferenceLevel = 'care' | 'neutral' | 'ignore'

export interface FactorDef {
  id: string
  name: string
  direction: 1 | -1
  unit: string
}

/** 统一评价维度：评分与权重均按此 5 项进行 */
export const FACTOR_DEFS: FactorDef[] = [
  { id: 'urban_planning', name: '城市规划', direction: 1, unit: '0-1' },
  { id: 'transport', name: '交通物流', direction: 1, unit: '0-1' },
  { id: 'industry', name: '产业协同', direction: 1, unit: '0-1' },
  { id: 'infrastructure', name: '基础配套', direction: 1, unit: '0-1' },
  { id: 'cost', name: '建造成本', direction: -1, unit: '0-1' },
]

/** 三档偏好及其权重基值 */
export const PREFERENCE_LEVELS: { value: PreferenceLevel; label: string; weight: number }[] = [
  { value: 'care', label: '在意', weight: 5 },
  { value: 'neutral', label: '一般', weight: 3 },
  { value: 'ignore', label: '不在意', weight: 1 },
]

const DEFAULT_PREFERENCES: Record<string, PreferenceLevel> = {
  urban_planning: 'neutral',
  transport: 'care',
  industry: 'neutral',
  infrastructure: 'neutral',
  cost: 'neutral',
}

export const useConfigStore = defineStore('config', () => {
  /** 约束状态：id → {enabled, buffer_m} */
  const constraints = ref<Record<string, ConstraintState>>({})
  /** 权重：维度 id → 0-1（和为 1，由偏好驱动） */
  const weights = ref<WeightMap>({})
  /** 选址偏好：维度 id → 在意程度 */
  const preferences = ref<Record<string, PreferenceLevel>>({ ...DEFAULT_PREFERENCES })
  const algorithm = ref<AlgorithmId>('topsis')
  const alpha = ref(0.5)
  const topN = ref(5)
  const gridSize = ref(30)
  const minAreaHa = ref(1)

  /** 权重和（展示用） */
  const weightSum = computed(() =>
    Object.values(weights.value).reduce((a, b) => a + b, 0)
  )

  /** 由偏好三档计算权重（自动归一化，和为 1） */
  function computeWeights(): WeightMap {
    const lv = (id: string) =>
      PREFERENCE_LEVELS.find((l) => l.value === (preferences.value[id] ?? 'neutral'))?.weight ?? 3
    const ids = FACTOR_DEFS.map((f) => f.id)
    const sum = ids.reduce((a, id) => a + lv(id), 0)
    const w: WeightMap = {}
    for (const id of ids) w[id] = Math.round((lv(id) / sum) * 1000) / 1000
    return w
  }

  /** 场景切换：重载约束，权重由当前偏好重算 */
  function applyScenario(s: ScenarioDetail): void {
    const c: Record<string, ConstraintState> = {}
    for (const item of s.constraints) {
      c[item.id] = { enabled: true, buffer_m: item.buffer_m }
    }
    constraints.value = c
    weights.value = computeWeights()
  }

  /** 设置偏好：立即重算权重 */
  function setPreference(id: string, level: PreferenceLevel): void {
    preferences.value[id] = level
    weights.value = computeWeights()
  }

  /** 权重自动归一化（保留，兼容旧调用） */
  function normalizeWeights(changedId?: string): void {
    const w = weights.value
    const ids = Object.keys(w)
    if (!ids.length) return
    const sum = ids.reduce((a, i) => a + w[i], 0)
    if (sum > 0) for (const i of ids) w[i] = w[i] / sum
    for (const i of ids) w[i] = Math.round(w[i] * 1000) / 1000
    weights.value = { ...w }
    void changedId
  }

  /** 重置为偏好默认权重 */
  function resetWeights(s: ScenarioDetail): void {
    void s
    weights.value = computeWeights()
  }

  /** 硬约束校验预览：返回启用的约束数 */
  const enabledConstraints = computed(() =>
    Object.entries(constraints.value).filter(([, v]) => v.enabled)
  )

  return {
    constraints, weights, preferences, algorithm, alpha, topN, gridSize, minAreaHa,
    weightSum, enabledConstraints,
    applyScenario, setPreference, computeWeights, normalizeWeights, resetWeights,
  }
})
