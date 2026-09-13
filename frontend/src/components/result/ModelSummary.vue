<script setup lang="ts">
/** 模型综合指标输出（模块 6.2）：候选池统计、初筛通过、最佳候选、聚类类型 */
import { computed } from 'vue'
import { useConfigStore } from '../../store/config'
import { useResultStore } from '../../store/result'
import { fmtNumber } from '../../utils/format'
import CardContainer from '../common/CardContainer.vue'

const config = useConfigStore()
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
    // 聚类类型仅 K-Means 算法有意义（后端仅在 kmeans 时返回 cluster）
    { label: '聚类类型', value: s.candidateCount && config.algorithm === 'kmeans' ? '3 类' : '—', unit: '' },
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
        <span class="model-summary__label">{{ s.label }}</span>
        <span class="model-summary__value">{{ s.value }}<em>{{ s.unit }}</em></span>
      </div>
    </div>
  </CardContainer>
</template>

<style scoped>
/* 指标格（对齐设计稿 .metric：白底描边、名称在上、值 18/700 墨黑、hover 阴影） */
.model-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.model-summary__cell {
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 7px;
  background: #fff;
  transition: 0.16s;
}
.model-summary__cell:hover {
  border-color: var(--brand-light-7);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.10);
}
.model-summary__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.model-summary__value {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.2px;
  line-height: 1.2;
  white-space: nowrap;
}
.model-summary__value em {
  font-style: normal;
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
  margin-left: 2px;
}
</style>
