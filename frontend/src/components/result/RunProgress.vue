<script setup lang="ts">
/**
 * 算法与权重说明（模块 6.1）。
 *
 * 两种状态：
 *  - 未计算：显示「尚未计算」提示，引导去左侧发起选址；
 *  - 已计算（点击「开始选址」出结果后）：展示本次分析的
 *    ① 采用的算法 ② 算法原理与公式 ③ 5 项评价维度 ④ 初选·计算流程 ⑤ 本次实际生效的权重分布总览。
 *
 * 权重总览取数优先级：后端本次返回的 selection.weights（combine_weights 的真实产出，
 * weight_source 标注组合方式）→ 缺失时退回前端「选址偏好」归一化值
 * （即 expert 模式下发给后端的 weights_override，两者必然一致）。
 */
import { computed } from 'vue'
import { useConfigStore, ALGORITHM_OPTIONS, FACTOR_DEFS, WEIGHT_MODES } from '../../store/config'
import { useResultStore } from '../../store/result'
import CardContainer from '../common/CardContainer.vue'

const config = useConfigStore()
const result = useResultStore()

/** 未选址前只显示「尚未计算」提示，出结果后展示本次分析内容 */
const hasResult = computed(() => Boolean(result.response))

const algo = computed(() => ALGORITHM_OPTIONS.find((a) => a.id === config.algorithm) ?? ALGORITHM_OPTIONS[0])

/** 权重来源模式（专家 / AI 学习 / 专家+AI），与本次计算真实下发/后端采用一致 */
const weightModeName = computed(() => WEIGHT_MODES.find((m) => m.id === config.weightMode)?.name ?? '—')

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

/** 本次实际生效的权重（后端 selection.weights 优先，缺失退回偏好归一化值） */
const weightRows = computed(() => {
  const effective = result.response?.weights
  return FACTOR_DEFS.map((f) => {
    const raw = effective?.[f.id] ?? config.weights[f.id] ?? 0
    return { id: f.id, name: f.name, pct: Math.round(raw * 1000) / 10 }
  })
})

/** 权重来源说明：后端标注的组合方式优先 */
const weightSource = computed(
  () => result.response?.weight_source ?? '本次计算未返回权重明细，以下为「选址偏好设置」归一化权重'
)

/** 展示取整后的合计（各维度四舍五入到 0.1%，直接相加可能为 99.x） */
const totalPct = computed(() => Math.round(weightRows.value.reduce((a, r) => a + r.pct, 0)))

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
  <CardContainer title="算法与权重说明" grow>
    <!-- 未计算：提示尚未计算（撑满卡片，与计算后布局完全一致，高度零跳动） -->
    <div v-if="!hasResult" class="algo-card__empty">
      <p class="algo-card__empty-title">尚未计算</p>
      <p class="algo-card__empty-text">
        在左侧选择行业门类、设置选址偏好后点击「开始选址」，此处将展示本次分析采用的算法、算法原理、
        评价维度、初选·计算流程与实际生效的权重分布总览。
        支持 TOPSIS / 多元回归 / K-Means 三种算法，以及专家 AHP、AI 学习、混合三种权重来源。
      </p>
    </div>

    <!-- 已计算：本次分析内容 -->
    <div v-else class="algo-doc">
      <div class="algo-doc__row">
        <span class="algo-doc__label">采用的算法</span>
        <span class="algo-doc__value">
          <b class="algo-doc__algo">{{ algo.name }}</b>（{{ algo.desc }}）；权重来源模式：<b>{{ weightModeName }}</b>
        </span>
      </div>
      <div class="algo-doc__row">
        <span class="algo-doc__label">算法原理</span>
        <span class="algo-doc__value">{{ algoDetail.principle }}</span>
      </div>
      <div class="algo-doc__formula">{{ algoDetail.formula }}</div>
      <div class="algo-doc__formula-note">{{ algoDetail.formulaNote }}</div>

      <div class="algo-doc__divider" />

      <div class="algo-doc__row">
        <span class="algo-doc__label">评价维度</span>
        <span class="algo-doc__value">5 项评价维度（城市规划/交通物流/产业协同/基础配套/建造成本），由控规工业用地图斑与底线管控、现状工业用地、产业园区、服务点位等真实图层做空间关系统计后标准化到 0–100 分。</span>
      </div>
      <div class="algo-doc__row">
        <span class="algo-doc__label">初选·计算流程</span>
        <span class="algo-doc__value">{{ flowText }}</span>
      </div>

      <div class="algo-doc__divider" />

      <!-- 本次权重总览（后端本次实际生效的组合权重） -->
      <div class="algo-weights">
        <div class="algo-weights__head">
          <h3 class="algo-weights__title">本次权重总览</h3>
          <span class="algo-weights__tag">合计 {{ totalPct }}%</span>
        </div>
        <div class="algo-weights__grid">
          <div v-for="r in weightRows" :key="r.id" class="algo-weights__cell">
            <span class="algo-weights__name">{{ r.name }}</span>
            <span class="algo-weights__val">{{ r.pct }}%</span>
            <span class="algo-weights__bar"><i :style="{ width: `${r.pct}%` }" /></span>
          </div>
        </div>
        <p class="algo-weights__note">权重来源：{{ weightSource }}</p>
      </div>
    </div>
  </CardContainer>
</template>

<style scoped>
/* ---- 未计算提示：撑满 grow 卡片并居中，保证计算前后右栏三卡高度不变 ---- */
.algo-card__empty {
  height: 100%;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px 16px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  text-align: center;
}
.algo-card__empty-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}
.algo-card__empty-text {
  margin: 0;
  font-size: 12px;
  line-height: 19px;
  color: var(--muted);
}

/* ---- 本次分析内容（卡片为 grow 模式：高度自适应剩余空间，滚动由 CardContainer body 承担） ---- */
.algo-doc {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.algo-doc__row {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
}
.algo-doc__label {
  flex-shrink: 0;
  width: 86px;
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

/* ---- 本次权重总览（原型 .sec-head + .metrics） ---- */
.algo-weights {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.algo-weights__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.algo-weights__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}
/* 「合计 N%」标签（原型 .tag.soft） */
.algo-weights__tag {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: var(--brand-light-9);
  color: var(--brand);
  white-space: nowrap;
}
.algo-weights__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
/* 指标格（原型 .metric） */
.algo-weights__cell {
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  background: #fff;
  transition: 0.16s;
}
.algo-weights__cell:hover {
  border-color: var(--brand-light-7);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.10);
}
.algo-weights__name {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
}
.algo-weights__val {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.2px;
  line-height: 1.2;
}
.algo-weights__bar {
  height: 4px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
  overflow: hidden;
}
.algo-weights__bar i {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--brand);
  transition: width var(--duration-base) var(--ease-out);
}
.algo-weights__note {
  font-size: 11px;
  line-height: 17px;
  color: var(--muted);
}
</style>
