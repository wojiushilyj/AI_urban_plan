/**
 * ECharts 实例管理：初始化 + ResizeObserver 自适应 + 卸载清理（模块 6.4）。
 */
import * as echarts from 'echarts'
import { onUnmounted, shallowRef } from 'vue'

export function useECharts(el: HTMLElement) {
  const chart = shallowRef<echarts.ECharts | null>(null)
  let ro: ResizeObserver | null = null

  chart.value = echarts.init(el)
  ro = new ResizeObserver(() => chart.value?.resize())
  ro.observe(el)

  onUnmounted(() => {
    ro?.disconnect()
    ro = null
    chart.value?.dispose()
    chart.value = null
  })

  return chart
}
