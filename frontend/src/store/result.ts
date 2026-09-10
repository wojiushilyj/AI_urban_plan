/** 结果状态：任务、进度日志、候选列表、综合指标（模块 6） */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { ScenarioDetail } from '../types/scenario'
import type { SelectionRequest, SelectionResponse } from '../types/selection'
import { runSelection } from '../api/selection'
import { preloadSelectionLayers } from '../mock/candidates'
import { runWithProgress } from '../mock/delay'
import { useMapStore } from './map'
import { useConfigStore } from './config'
import { useAppStore } from './app'
import { useAiStore } from './ai'

export const useResultStore = defineStore('result', () => {
  const running = ref(false)
  const percent = ref(0)
  const logs = ref<string[]>([])
  const response = ref<SelectionResponse | null>(null)
  const error = ref<string>('')

  /** 综合指标（模块 6.2） */
  const summary = computed(() => {
    if (!response.value) return null
    const r = response.value
    const best = r.candidates[0]
    return {
      totalCells: r.total_cells,
      availableCells: r.available_cells,
      availableRate: r.total_cells ? (r.available_cells / r.total_cells) * 100 : 0,
      candidateCount: r.candidates.length,
      bestScore: best?.score ?? 0,
      bestArea: best?.area_ha ?? 0,
      taskId: r.task_id,
    }
  })

  /** 执行选址计算（模块 4.6 触发按钮调用） */
  async function run(scenario: ScenarioDetail): Promise<void> {
    const config = useConfigStore()
    const map = useMapStore()
    const app = useAppStore()
    const ai = useAiStore()

    // 研究区固定为临桂区（见 store/map.ts 初始 AOI）
    error.value = ''
    running.value = true
    percent.value = 0
    logs.value = []
    app.setStatus('正在执行选址计算…', 5)

    try {
      const req: SelectionRequest = {
        scenario_id: scenario.id,
        aoi: map.aoi!,
        grid_size_m: config.gridSize,
        min_area_ha: config.minAreaHa,
        top_n: config.topN,
        alpha: config.alpha,
        weights_override: config.weights,
        algorithm: config.algorithm,
        // 用地规模约束：AI 从聊天需求里解析到占地面积时才传（容差默认 ±50%）
        target_area_ha: config.targetAreaHa ?? undefined,
        area_tolerance: config.areaTolerance,
      }
      // 先并行预取空间图层（与进度动画重叠，避免进度走完后卡住），再推 5 阶段进度
      preloadSelectionLayers()
      await runWithProgress((t) => {
        percent.value = t.percent
        ai.pushProgress(t.label)
        app.setStatus(`选址计算中 ${t.percent}%`, t.percent)
      })
      const res = await runSelection(req, scenario)
      response.value = res
      map.result = res
      app.setStatus(`计算完成：Top-${res.candidates.length} 候选地块已生成`, 0)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      ai.pushProgress(`[错误] ${error.value}`)
      app.setStatus('计算失败', 0)
    } finally {
      running.value = false
      percent.value = 100
    }
  }

  function reset(): void {
    running.value = false
    percent.value = 0
    logs.value = []
    response.value = null
    error.value = ''
  }

  return { running, percent, logs, response, error, summary, run, reset }
})
