<script setup lang="ts">
/** 雷达图（模块 6.4）：对比 Top-3 候选地块的各因子得分（归一化 0-100） */
import { nextTick, ref, watch } from 'vue'
import type { ECharts } from 'echarts'
import { useResultStore } from '../../store/result'
import { useScenarioStore } from '../../store/scenario'
import { useECharts } from '../../composables/useECharts'

const result = useResultStore()
const scenario = useScenarioStore()
const el = ref<HTMLDivElement>()
let chart: ECharts | null = null

function render(): void {
  const r = result.response
  if (!r || !chart) return
  const indicators = (scenario.detail?.factors ?? []).map((f) => ({ name: f.name, max: 100 }))
  const top3 = r.candidates.slice(0, 3)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, fontSize: 12 },
    radar: {
      indicator: indicators,
      radius: '62%',
      axisName: { fontSize: 12, color: '#6B7280' },
      splitArea: { areaStyle: { color: ['#FFFFFF', '#F9FAFB'] } },
    },
    series: [
      {
        type: 'radar',
        data: top3.map((c, i) => ({
          name: `No.${c.rank}`,
          value: (scenario.detail?.factors ?? []).map((f) => c.factors[f.id] ?? 0),
          areaStyle: { opacity: 0.15 },
          lineStyle: { width: 2 },
          itemStyle: { color: ['#3B82F6', '#F59E0B', '#EF4444'][i % 3] },
        })),
      },
    ],
  })
}

watch(el, async (n) => {
  if (n) {
    chart = useECharts(n).value
    // 首次挂载时容器宽度可能尚未稳定，延迟一帧并 resize 后再渲染
    await nextTick()
    requestAnimationFrame(() => {
      chart?.resize()
      render()
    })
  }
})

watch(() => result.response, render)
</script>

<template>
  <div ref="el" class="radar-chart" />
</template>

<style scoped>
.radar-chart {
  width: 100%;
  height: 260px;
}
</style>
