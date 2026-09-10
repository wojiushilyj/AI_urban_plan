/**
 * 用地规模需求的自然语言解析（模块 2.4）。
 *
 * 用户在 AI 聊天里提到「占地面积」时，从文本里抽出一个**目标面积（公顷）**，
 * 供选址引擎按 ±容差（见 config.areaTolerance）筛出规模匹配的候选地块。
 *
 * 全部换算为公顷：1 公顷 = 15 亩 = 10000 平方米 = 1 万平方米。
 * 后端接入 LLM 后，本模块即为兜底的正则解析器（换算口径需与后端保持一致）。
 */

/** 1 公顷折合的亩数（国标：1 亩 = 666.67 m² = 1/15 公顷） */
export const MU_PER_HA = 15

/**
 * 用地规模容差初值：±50%。
 *
 * 用户在 AI 聊天中提到占地面积时，候选地块面积须落在
 * [目标 × (1 − 容差), 目标 × (1 + 容差)] 区间内。
 *
 * ⚠️ 这里只是**初期限定**，最终限值由后端算法设计人员按行业门类核定，
 * 后端对应位置：`backend/app/config.py → DEFAULT_AREA_TOLERANCE`。
 * 调整时两处务必同步，否则前后端口径不一致。
 */
export const DEFAULT_AREA_TOLERANCE = 0.5

/** 面积合理范围（公顷）：超出即视为噪声数字，不施加面积约束 */
const MIN_HA = 0.05
const MAX_HA = 5000

/**
 * 单位换算表。**顺序即匹配优先级：长单位必须排在短单位之前**
 * （「万平方米」含「平方米」，「万亩」含「亩」）。
 */
const UNITS: { re: string; toHa: number; label: string }[] = [
  { re: '万平方(?:米|公尺)|万平米|万㎡|万m²|万m2', toHa: 1, label: '万平方米' },
  { re: '平方(?:公里|千米)|k㎡|km²|km2', toHa: 100, label: '平方公里' },
  { re: '万亩', toHa: 10000 / MU_PER_HA, label: '万亩' },
  { re: '公顷|平方百米|hectare|ha(?![a-z])', toHa: 1, label: '公顷' },
  { re: '亩', toHa: 1 / MU_PER_HA, label: '亩' },
  { re: '平方(?:米|公尺)|平米|㎡|m²|m2', toHa: 1 / 10000, label: '平方米' },
]

/** 「数字 + 单位」的完整匹配模板；第 1 组为数值，第 2 组为完整单位token */
const AREA_RE = new RegExp(
  `(\\d+(?:\\.\\d+)?)\\s*(${UNITS.map((u) => u.re).join('|')})`,
  'i'
)

/** 单位 token → 换算系数 */
function findUnit(token: string) {
  return UNITS.find((u) => new RegExp(`^(?:${u.re})$`, 'i').test(token))
}

export interface AreaRequirement {
  /** 目标用地规模（公顷，保留两位小数） */
  targetHa: number
  /** 原始表述，如「500亩」，用于对话回显 */
  text: string
  /** 命中文本所用的单位名，如「亩」 */
  unit: string
  /** 用户原文中的数值（按原单位） */
  value: number
}

/**
 * 从需求文本中解析用地规模。
 *
 * 取**第一个**「数字 + 面积单位」组合并换算为公顷。
 * 区间写法（如「500-800亩」）会取区间上限，作为需求上限处理。
 * 未提及面积、或换算结果超出合理范围时返回 null（此时不施加面积约束）。
 */
export function parseAreaRequirement(text: string): AreaRequirement | null {
  const m = AREA_RE.exec(text)
  if (!m) return null

  const value = Number(m[1])
  const unit = findUnit(m[2])
  if (!unit || !Number.isFinite(value) || value <= 0) return null

  const targetHa = value * unit.toHa
  if (targetHa < MIN_HA || targetHa > MAX_HA) return null

  return {
    targetHa: Math.round(targetHa * 100) / 100,
    text: m[0].replace(/\s+/g, ''),
    unit: unit.label,
    value,
  }
}

/** 用地规模允许区间：target ± tolerance（比例，0.5 = 上下浮动 50%） */
export function areaWindow(targetHa: number, tolerance: number): { lo: number; hi: number } {
  const t = Math.max(0, tolerance)
  return {
    lo: Math.round(targetHa * (1 - t) * 100) / 100,
    hi: Math.round(targetHa * (1 + t) * 100) / 100,
  }
}

/** 公顷 → 亩（展示用） */
export function haToMu(ha: number): number {
  return Math.round(ha * MU_PER_HA * 10) / 10
}
