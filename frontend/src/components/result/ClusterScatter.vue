<script setup lang="ts">
/**
 * 聚类散点图（模块 6.4）：X=首位因子，Y=综合得分，点大小=面积，颜色=聚类分组。
 */
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
  const firstFactor = scenario.detail?.factors[0]
  const clusters = [0, 1, 2].map((c) =>
    r.candidates
      .filter((p) => p.cluster === c)
      .map((p) => ({
        value: [
          firstFactor ? p.factors[firstFactor.id] : p.rank,
          p.score,
          p.area_ha,
        ],
        name: `No.${p.rank}`,
      }))
  )
  chart.setOption({
    grid: { left: 44, right: 20, top: 20, bottom: 40 },
    tooltip: {
      formatter: (p: { data: { name: string; value: number[] } }) =>
        `${p.data.name}<br/>${firstFactor?.name ?? '因子'}：${p.data.value[0]}<br/>得分：${p.data.value[1]}<br/>面积：${p.data.value[2]} ha`,
    },
    legend: { bottom: 0, fontSize: 12 },
    xAxis: {
      type: 'value',
      name: firstFactor?.name ?? '因子',
      nameTextStyle: { fontSize: 12 },
      axisLabel: { fontSize: 12 },
    },
    yAxis: { type: 'value', name: '综合得分', max: 100, axisLabel: { fontSize: 12 } },
    series: clusters.map((data, i) => ({
      name: ['优先开发类', '条件适合类', '储备备用类'][i],
      type: 'scatter',
      data,
      symbolSize: (v: number[]) => 10 + (v[2] / 40) * 12,
      itemStyle: { color: ['#3B82F6', '#F59E0B', '#9CA3AF'][i], opacity: 0.85 },
      label: { show: true, formatter: (p: { data: { name: string } }) => p.data.name, fontSize: 11, position: 'top' },
    })),
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
  <div ref="el" class="cluster-scatter" />
</template>

<style scoped>
.cluster-scatter {
  width: 100%;
  height: 260px;
}
</style>
