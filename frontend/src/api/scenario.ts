/** 场景接口（模块 8.3：契约对齐后端 /api/scenarios） */
import type { ScenarioDetail, ScenarioSummary } from '../types/scenario'
import { get } from './client'
import { mockGetScenario, mockListScenarios } from '../mock/scenarios'

export async function getScenarios(): Promise<ScenarioSummary[]> {
  const r = await get<{ items: ScenarioSummary[] }>('/api/scenarios', () => mockListScenarios())
  return r.items
}

export async function getScenarioDetail(id: string): Promise<ScenarioDetail> {
  return get<ScenarioDetail>(`/api/scenarios/${id}`, () => mockGetScenario(id))
}
