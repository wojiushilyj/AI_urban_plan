/** 格式化工具 */

export function fmtNumber(n: number, digits = 0): string {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function fmtArea(m2: number): string {
  if (m2 >= 1_000_000) return `${(m2 / 1_000_000).toFixed(2)} km²`
  return `${fmtNumber(m2, 0)} m²`
}

export function fmtScore(v: number): string {
  return v.toFixed(1)
}

/** 因子方向 → 中文说明 */
export function directionLabel(d: 1 | -1 | 2): string {
  if (d === 1) return '正向'
  if (d === -1) return '负向'
  return '区间'
}

export function directionTagType(d: 1 | -1 | 2): 'success' | 'danger' | 'warning' {
  if (d === 1) return 'success'
  if (d === -1) return 'danger'
  return 'warning'
}
