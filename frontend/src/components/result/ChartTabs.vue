<script setup lang="ts">
/** 图表分析容器（模块 6.4）：得分柱状 / 雷达图 / 聚类散点 三个图切换 */
import { computed, ref } from 'vue'
import { useResultStore } from '../../store/result'
import ScoreBarChart from './ScoreBarChart.vue'
import RadarChart from './RadarChart.vue'
import ClusterScatter from './ClusterScatter.vue'

const result = useResultStore()
const active = ref<'bar' | 'radar' | 'scatter'>('bar')

const hasResult = computed(() => Boolean(result.response))

const tabs = [
  { name: 'bar', label: '得分柱状' },
  { name: 'radar', label: '因子雷达' },
  { name: 'scatter', label: '聚类散点' },
]
</script>

<template>
  <div class="chart-tabs">
    <el-radio-group v-model="active" size="small" class="chart-tabs__switch">
      <el-radio-button v-for="t in tabs" :key="t.name" :value="t.name">{{ t.label }}</el-radio-button>
    </el-radio-group>

    <template v-if="hasResult">
      <ScoreBarChart v-if="active === 'bar'" />
      <RadarChart v-if="active === 'radar'" />
      <ClusterScatter v-if="active === 'scatter'" />
    </template>
    <el-empty v-else description="完成选址计算后展示统计图表" :image-size="80" />
  </div>
</template>

<style scoped>
.chart-tabs {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}
.chart-tabs__switch {
  display: flex;
}
.chart-tabs__switch :deep(.el-radio-button) {
  flex: 1;
}
.chart-tabs__switch :deep(.el-radio-button__inner) {
  width: 100%;
}
</style>
