/**
 * 权重归一化 composable（模块 4.3）。
 * 核心逻辑在 config store，此处提供便捷绑定与展示格式化。
 */
import { computed } from 'vue'
import { useConfigStore } from '../store/config'

export function useWeightNormalize() {
  const config = useConfigStore()

  /** 权重和（理论上恒为 1，用于 UI 校验展示） */
  const sum = computed(() =>
    Object.values(config.weights).reduce((a, b) => a + b, 0)
  )

  const isNormalized = computed(() => Math.abs(sum.value - 1) < 0.01)

  /** 拖动滑块：设置当前值并等比归一其余项 */
  function onSliderChange(id: string, val: number | number[]): void {
    config.weights[id] = Array.isArray(val) ? val[0] : val
    config.normalizeWeights(id)
  }

  /** 展示为百分比 */
  function pct(v: number): string {
    return `${(v * 100).toFixed(1)}%`
  }

  return { sum, isNormalized, onSliderChange, pct }
}
