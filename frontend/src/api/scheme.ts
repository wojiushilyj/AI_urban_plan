/**
 * 方案管理接口（模块 1.3）。
 * mock / 真实均落 localStorage，纯前端自治（后端暂无该端点，预留切换）。
 */
export interface Scheme {
  id: string
  name: string
  scenarioId: string
  createdAt: string
  /** 完整参数快照：约束开关、权重、算法、AOI */
  payload: {
    constraints: Record<string, { enabled: boolean; buffer_m: number }>
    weights: Record<string, number>
    algorithm: string
    alpha: number
    topN: number
    gridSize: number
    aoi: unknown
  }
}

const KEY = 'aiurbanplan.schemes'

function load(): Scheme[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]') as Scheme[]
  } catch {
    return []
  }
}

function save(list: Scheme[]): void {
  localStorage.setItem(KEY, JSON.stringify(list))
}

export function listSchemes(): Scheme[] {
  return load()
}

export function saveScheme(scheme: Omit<Scheme, 'id' | 'createdAt'>): Scheme {
  const list = load()
  const full: Scheme = {
    ...scheme,
    id: `scheme-${Date.now().toString(36)}`,
    createdAt: new Date().toLocaleString('zh-CN'),
  }
  list.unshift(full)
  save(list)
  return full
}

export function deleteScheme(id: string): void {
  save(load().filter((s) => s.id !== id))
}
