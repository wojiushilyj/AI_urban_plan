/** 选址计算接口（模块 8.2：契约对齐后端 POST /api/selection/run） */
import type { SelectionRequest, SelectionResponse } from '../types/selection'
import type { ScenarioDetail } from '../types/scenario'
import { post } from './client'
import { mockRunSelection } from '../mock/candidates'

export async function runSelection(
  req: SelectionRequest,
  scenario: ScenarioDetail,
  onProgress?: (p: { percent: number; log: string }) => void
): Promise<SelectionResponse> {
  return post<SelectionResponse>(
    '/api/selection/run',
    req,
    () => mockRunSelection(req, scenario, onProgress)
  )
}
