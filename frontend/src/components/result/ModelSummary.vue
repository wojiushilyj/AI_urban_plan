<script setup lang="ts">
/** 模型综合指标输出（模块 6.2）：网格统计、可利用率、最佳候选、聚类类型 */
import { computed } from 'vue'
import { useResultStore } from '../../store/result'
import { fmtNumber } from '../../utils/format'
import CardContainer from '../common/CardContainer.vue'

const result = useResultStore()

const stats = computed(() => {
  const s = result.summary
  if (!s) return []
  return [
    { label: '候选池图斑数', value: fmtNumber(s.totalCells), unit: '个' },
    { label: '初筛通过图斑', value: fmtNumber(s.availableCells), unit: `个（${s.availableRate.toFixed(1)}%）` },
    { label: '候选地块数', value: String(s.candidateCount), unit: '个' },
    { label: '最佳综合得分', value: s.bestScore.toFixed(1), unit: '分' },
    { label: '首选地块面积', value: s.bestArea.toFixed(2), unit: '公顷' },
    { label: '聚类类型', value: s.candidateCount ? '3 类' : '—', unit: '' },
  ]
})

/** 无数据时的占位标签 */
const PLACEHOLDER = [
  { label: '候选池图斑数', value: '—', unit: '' },
  { label: '初筛通过图斑', value: '—', unit: '' },
  { label: '候选地块数', value: '—', unit: '' },
  { label: '最佳综合得分', value: '—', unit: '' },
  { label: '首选地块面积', value: '—', unit: '' },
  { label: '聚类类型', value: '—', unit: '' },
]
</script>

<template>
  <CardContainer title="模型综合指标">
    <div class="model-summary">
      <div v-for="s in (stats.length ? stats : PLACEHOLDER)" :key="s.label" class="model-summary__cell">
        <span class="model-summary__value">{{ s.value }}<em>{{ s.unit }}</em></span>
        <span class="model-summary__label">{{ s.label }}</span>
      </div>
    </div>
  </CardContainer>
</template>

<style scoped>
.model-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-sm);
}
.model-summary__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-sm);
  text-align: center;
}
.model-summary__value {
  font-size: 17px;
  font-weight: 700;
  color: var(--brand);
}
.model-summary__value em {
  font-style: normal;
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: 2px;
}
.model-summary__label {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
