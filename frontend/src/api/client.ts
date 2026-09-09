/**
 * 接口统一入口：按 VITE_USE_MOCK 分流到 mock 函数或真实 axios。
 * 切换真实接口：修改 .env 中 VITE_USE_MOCK=false，代码零改动。
 */
import { api } from '../api'

export const USE_MOCK: boolean = import.meta.env.VITE_USE_MOCK !== 'false'

/** mock 模式下的模拟延迟基础值 */
export const MOCK_DELAY = 300

/** GET 请求（mock / real 分流） */
export async function get<T>(url: string, mockFn?: () => T | Promise<T>): Promise<T> {
  if (USE_MOCK && mockFn) return mockFn()
  const r = await api.get<T>(url)
  return r.data
}

/** POST 请求（mock / real 分流） */
export async function post<T>(url: string, body?: unknown, mockFn?: () => T | Promise<T>): Promise<T> {
  if (USE_MOCK && mockFn) return mockFn()
  const r = await api.post<T>(url, body)
  return r.data
}
