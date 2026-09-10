<script setup lang="ts">
/** 算法与权重说明（模块 6.1）：当前算法、原理公式、指标来源、初选-计算流程、权重总览 */
import { computed } from 'vue'
import { useConfigStore, ALGORITHM_OPTIONS, FACTOR_DEFS } from '../../store/config'
import { useResultStore } from '../../store/result'
import CardContainer from '../common/CardContainer.vue'

const config = useConfigStore()
const result = useResultStore()

/** 未选址前内容区空白（卡片标题常显） */
const hasResult = computed(() => Boolean(result.response))

const algo = computed(() => ALGORITHM_OPTIONS.find((a) => a.id === config.algorithm) ?? ALGORITHM_OPTIONS[0])

/** 算法原理 + 计算公式（按算法类型） */
const algoDetail = computed(() => {
  switch (config.algorithm) {
    case 'regression':
      return {
        principle: '拟合历史选址偏好，建立因子与适宜度的线性关系，预测候选地块适宜度。',
        formula: 'Y = β₀ + Σ βᵢ·Xᵢ + ε',
        formulaNote: 'Xᵢ 为标准化因子值，βᵢ 为回归系数（由历史样本最小二乘估计）。',
      }
    case 'kmeans':
      return {
        principle: '按因子特征将地块自动分组，最小化类内距离，识别同类地块片区。',
        formula: 'min Σᵢ Σₓ∈Cᵢ ‖x − μᵢ‖²',
        formulaNote: 'μᵢ 为第 i 类质心，迭代至质心稳定或达到最大轮次。',
      }
    case 'topsis':
    default:
      return {
        principle: '逼近理想解排序，计算候选与正/负理想解的距离，按贴近度综合评价。',
        formula: 'Cᵢ = Dᵢ⁻ / (Dᵢ⁺ + Dᵢ⁻)',
        formulaNote: 'Dᵢ⁺、Dᵢ⁻ 分别为到正、负理想解的加权欧氏距离，Cᵢ ∈ [0,1] 越接近 1 越优。',
      }
  }
})

/** 权重总览（由选址偏好三档归一化） */
const weightRows = computed(() =>
  FACTOR_DEFS.map((f) => ({
    name: f.name,
    weight: (config.weights[f.id] ?? 0) * 100,
  }))
)

/** 初选·计算流程（含本次生效的用地规模区间，末段随算法切换） */
const flowText = computed(() => {
  const area = config.areaRange
  const areaSeg =
    area === null
      ? `+ 用户未提及占地面积，不做规模匹配`
      : `+ 用地规模 ${area.lo}–${area.hi} 公顷（目标 ${config.targetAreaHa} 公顷 ±${Math.round(config.areaTolerance * 100)}%）`
  return (
    '候选池：控规工业用地图斑 → 初选：生态保护红线 / 永久基本农田硬约束一票否决 ' +
    `+ 最小面积 ${config.minAreaHa} 公顷 ` +
    `${areaSeg} → 计算：组合赋权多因子评价 → 精选：${algo.value.name} 排序输出 Top-N 候选地块。`
  )
})
</script>

<template>
  <CardContainer title="算法与权重说明">
    <div v-if="!hasResult" class="algo-doc algo-doc--empty" />
    <div v-else class="algo-doc">
      <div class="algo-doc__row">
        <span class="algo-doc__label">当前算法</span>
        <span class="algo-doc__value algo-doc__algo">{{ algo.name }}</span>
      </div>
      <div class="algo-doc__row">
        <span class="algo-doc__label">算法原理</span>
        <span class="algo-doc__value">{{ algoDetail.principle }}</span>
      </div>
      <div class="algo-doc__formula">{{ algoDetail.formula }}</div>
      <div class="algo-doc__formula-note">{{ algoDetail.formulaNote }}</div>

      <div class="algo-doc__divider" />

      <div class="algo-doc__row">
        <span class="algo-doc__label">指标来源</span>
        <span class="algo-doc__value">5 项评价维度（城市规划/交通物流/产业协同/基础配套/建造成本），由控规工业用地图斑与底线管控、现状工业用地、产业园区、服务点位等真实图层做空间关系统计后标准化到 0–100 分。</span>
      </div>
      <div class="algo-doc__row">
        <span class="algo-doc__label">初选·计算流程</span>
        <span class="algo-doc__value">{{ flowText }}</span>
      </div>

      <div class="algo-doc__divider" />

      <div class="algo-doc__weights">
        <div class="algo-doc__weights-title">本次权重总览</div>
        <div v-for="w in weightRows" :key="w.name" class="algo-doc__weight-row">
          <span class="algo-doc__weight-name">{{ w.name }}</span>
          <div class="algo-doc__weight-bar"><i :style="{ width: w.weight + '%' }" /></div>
          <span class="algo-doc__weight-val">{{ w.weight.toFixed(1) }}%</span>
        </div>
      </div>
    </div>
  </CardContainer>
</template>

<style scoped>
.algo-doc {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
  padding-right: 4px;
}
.algo-doc--empty {
  min-height: 150px;
}
.algo-doc__row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
}
.algo-doc__label {
  flex-shrink: 0;
  width: 72px;
  color: var(--text-secondary);
  font-weight: 600;
}
.algo-doc__value {
  color: var(--text-regular);
}
.algo-doc__algo {
  font-weight: 700;
  color: var(--brand);
}
.algo-doc__formula {
  font-family: 'Times New Roman', Georgia, serif;
  font-size: 15px;
  font-style: italic;
  color: var(--text-primary);
  padding: 8px 12px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-sm);
  text-align: center;
}
.algo-doc__formula-note {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}
.algo-doc__divider {
  height: 1px;
  background: var(--border-lighter);
  margin: 4px 0;
}
.algo-doc__weights {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.algo-doc__weights-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.algo-doc__weight-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.algo-doc__weight-name {
  width: 64px;
  flex-shrink: 0;
  color: var(--text-regular);
}
.algo-doc__weight-bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-subtle);
  overflow: hidden;
}
.algo-doc__weight-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--brand);
  transition: width 0.3s ease;
}
.algo-doc__weight-val {
  width: 46px;
  text-align: right;
  flex-shrink: 0;
  color: var(--brand-dark-2);
  font-weight: 600;
}
</style>
