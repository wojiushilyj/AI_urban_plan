/**
 * 要素属性 → 卡片展示行的纯函数转换。
 *
 * 与组件解耦（不依赖 Vue / DOM），便于用 esbuild + Node 直接对真实 GeoJSON 断言。
 * 规则：
 * - 剔除内部字段与空值
 * - 数值统一最多 2 位小数（避免 386.56000000000006 这类浮点噪声）
 * - 字段名补中文标签、补单位
 * - 长文本（如园区「介绍」整段）标记 long，由组件改用整段排版
 */

/** 字段友好标签（shapefile 字段名被截断或为编码制时补中文名） */
const LABELS: Record<string, string> = {
  DLBM: '地类编码',
  DLMC: '地类名称',
  BSM: '标识码',
  OBJECTID: '对象 ID',
  TBMJ: '图斑面积',
  主导产: '主导产业',
  介绍: '园区介绍',
}

/** 字段单位（源数据无单位信息，按属性含义补） */
const UNITS: Record<string, string> = {
  图斑面积: '㎡',
  产值: '万元',
  时速: 'km/h',
}

/** 内部字段不展示（候选地块要素携带的整份 JSON 字符串） */
const HIDDEN = new Set(['parcel'])

/** 超过该长度的字符串值改用「整段」排版（标签单独一行），避免挤在两栏窄格里 */
export const LONG_TEXT_LEN = 24

export interface FeatureFieldRow {
  key: string
  label: string
  value: string
  unit: string
  /** true 表示长文本，组件应整段渲染 */
  long: boolean
}

export function toFieldRows(
  properties: Record<string, unknown> | null | undefined
): FeatureFieldRow[] {
  if (!properties) return []
  return Object.entries(properties)
    .filter(([k, v]) => !HIDDEN.has(k) && v !== null && v !== undefined && v !== '')
    .map(([k, v]) => ({
      key: k,
      label: LABELS[k] ?? k,
      value: typeof v === 'number' ? String(Number(v.toFixed(2))) : String(v),
      unit: UNITS[k] ?? '',
      long: typeof v === 'string' && v.length > LONG_TEXT_LEN,
    }))
}
