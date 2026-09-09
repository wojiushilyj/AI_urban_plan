<script setup lang="ts">
/** 得分柱状图（模块 6.4）：候选地块综合得分排序 */
import { nextTick, ref, watch } from 'vue'
import { useResultStore } from '../../store/result'
import { useECharts } from '../../composables/useECharts'

const result = useResultStore()
const el = ref<HTMLDivElement>()
const chart = ref<any>(null)

/** 渲染（实例就绪 + 数据就绪两个条件都满足时才出图，避免竞态导致空白） */
function render(): void {
  const r = result.response
  if (!r || !chart.value) return
  chart.value.setOption({
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: r.candidates.map((c) => `No.${c.rank}`),
      axisLabel: { fontSize: 13 },
    },
    yAxis: { type: 'value', max: 100, axisLabel: { fontSize: 13 } },
    series: [
      {
        type: 'bar',
        data: r.candidates.map((c) => c.score),
        barWidth: '52%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#3B82F6' },
              { offset: 1, color: '#93C5FD' },
            ],
          },
        },
        label: { show: true, position: 'top', fontSize: 12, color: '#2563EB' },
      },
    ],
  })
}

watch(el, async (n) => {
  if (n) {
    chart.value = useECharts(n).value
    // 首次挂载时容器宽度可能尚未稳定（el-tabs 内），延迟一帧并 resize 后再渲染，避免柱子挤在一起
    await nextTick()
    requestAnimationFrame(() => {
      chart.value?.resize()
      render()
    })
  }
})

watch(() => result.response, render)
</script>

<template>
  <div ref="el" class="score-bar-chart" />
</template>

<style scoped>
.score-bar-chart {
  width: 100%;
  height: 240px;
}
</style>
