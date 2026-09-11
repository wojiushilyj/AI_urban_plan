<script setup lang="ts">
/**
 * 候选地块信息卡片（地图右侧贴边浮动）
 * 显示选中地块的综合得分、面积、评估结论、各因子得分，
 * 以及可解释 AI 的因子贡献分解（优势/短板）与蒙特卡洛入选概率。
 */
import { computed } from 'vue'
import type { CandidateParcel } from '../../types/selection'
import { fmtScore } from '../../utils/format'

const props = defineProps<{
  parcel: CandidateParcel | null
  factorNames: Record<string, string>
}>()

const emit = defineEmits<{ close: [] }>()

const factorRows = computed(() => {
  if (!props.parcel) return []
  return Object.entries(props.parcel.factors).map(([id, v]) => ({
    id,
    name: props.factorNames[id] ?? id,
    value: v,
  }))
})

/** 因子贡献分解：正值=优势，负值=短板；条形长度为相对最大绝对贡献的比例 */
const contribRows = computed(() => {
  const c = props.parcel?.contributions
  if (!c) return []
  const maxAbs = Math.max(...Object.values(c).map((v) => Math.abs(v)), 1e-6)
  return Object.entries(c)
    .map(([id, v]) => ({ id, name: props.factorNames[id] ?? id, value: v }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .map((r) => ({ ...r, width: `${Math.max(3, (Math.abs(r.value) / maxAbs) * 100)}%` }))
})

/** 入选概率（0–1 → 百分比） */
const robustPct = computed(() => {
  const r = props.parcel?.robustness
  return r === null || r === undefined ? null : Math.round(r * 100)
})

const driverName = computed(() =>
  props.parcel?.top_driver ? (props.factorNames[props.parcel.top_driver] ?? props.parcel.top_driver) : ''
)
const weaknessName = computed(() =>
  props.parcel?.top_weakness
    ? (props.factorNames[props.parcel.top_weakness] ?? props.parcel.top_weakness)
    : ''
)
</script>

<template>
  <transition name="parcel-card">
    <aside v-if="parcel" class="parcel-info-card">
      <header class="parcel-info-card__head">
        <span class="parcel-info-card__rank">候选地块 · No.{{ parcel.rank }}</span>
        <el-button class="parcel-info-card__close" text @click="emit('close')">✕</el-button>
      </header>

      <div class="parcel-info-card__score">
        <span class="parcel-info-card__score-val">{{ fmtScore(parcel.score) }}</span>
        <span class="parcel-info-card__score-unit">综合得分</span>
      </div>

      <div class="parcel-info-card__meta">
        <div class="parcel-info-card__meta-row">
          <span class="parcel-info-card__meta-label">地块编码</span>
          <span class="parcel-info-card__meta-code">{{ parcel.code ?? '—' }}</span>
        </div>
        <div class="parcel-info-card__meta-row">
          <span class="parcel-info-card__meta-label">来源</span>
          <span class="parcel-info-card__meta-val">{{ parcel.source ?? '控规工业用地' }}</span>
        </div>
        <div class="parcel-info-card__meta-row">
          <span class="parcel-info-card__meta-label">面积</span>
          <span class="parcel-info-card__meta-val">{{ parcel.area_ha }} 公顷</span>
        </div>
        <div class="parcel-info-card__meta-row">
          <span class="parcel-info-card__meta-label">结论</span>
          <span class="parcel-info-card__meta-val">{{ parcel.notes }}</span>
        </div>
      </div>

      <div class="parcel-info-card__factors">
        <div class="parcel-info-card__factors-title">指标得分</div>
        <div v-for="f in factorRows" :key="f.id" class="parcel-info-card__factor">
          <span class="parcel-info-card__factor-name">{{ f.name }}</span>
          <span class="parcel-info-card__factor-val">{{ fmtScore(f.value) }}</span>
        </div>
      </div>

      <div v-if="parcel.build_density !== undefined" class="parcel-info-card__robust">
        <div class="parcel-info-card__robust-row">
          <span class="parcel-info-card__robust-label">现状建筑占地（拆迁量）</span>
          <span class="parcel-info-card__robust-val">{{ (parcel.build_density * 100).toFixed(0) }}%</span>
        </div>
        <div v-if="robustPct !== null" class="parcel-info-card__robust-row">
          <span class="parcel-info-card__robust-label">入选概率（扰动 200 次）</span>
          <span class="parcel-info-card__robust-val">{{ robustPct }}%</span>
        </div>
      </div>

      <div v-if="contribRows.length" class="parcel-info-card__contrib">
        <div class="parcel-info-card__contrib-title">
          因子贡献
          <span class="parcel-info-card__contrib-hint">留一法 · 正向为优势</span>
        </div>
        <div class="parcel-info-card__contrib-legend">
          <span v-if="driverName">优势：{{ driverName }}</span>
          <span v-if="weaknessName">短板：{{ weaknessName }}</span>
        </div>
        <div v-for="r in contribRows" :key="r.id" class="parcel-info-card__contrib-row">
          <span class="parcel-info-card__contrib-name">{{ r.name }}</span>
          <span class="parcel-info-card__contrib-bar-wrap">
            <i
              class="parcel-info-card__contrib-bar"
              :class="r.value >= 0 ? 'is-pos' : 'is-neg'"
              :style="{ width: r.width }"
            />
          </span>
          <span
            class="parcel-info-card__contrib-val"
            :class="r.value >= 0 ? 'is-pos' : 'is-neg'"
          >{{ r.value >= 0 ? '+' : '' }}{{ r.value.toFixed(3) }}</span>
        </div>
      </div>
    </aside>
  </transition>
</template>

<style scoped>
.parcel-info-card {
  width: 288px;
  max-height: calc(100% - 32px);
  overflow-y: auto;
  padding: var(--gap-md) var(--gap-lg);
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}
.parcel-info-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid var(--border-lighter);
}
.parcel-info-card__rank {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  letter-spacing: 0.3px;
}
/* 地块编码（由来源图层 + 要素序号生成，如 KG-065） */
.parcel-info-card__meta-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--brand);
}
.parcel-info-card__close {
  font-size: 16px;
  color: var(--text-secondary);
  padding: 2px 4px;
}
.parcel-info-card__score {
  display: flex;
  align-items: baseline;
  gap: var(--gap-sm);
  padding: var(--gap-md) 0 var(--gap-sm);
}
.parcel-info-card__score-val {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  color: #3B82F6;
  letter-spacing: -1px;
}
.parcel-info-card__score-unit {
  font-size: 14px;
  color: var(--text-secondary);
}
.parcel-info-card__meta {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid var(--border-lighter);
}
.parcel-info-card__meta-row {
  display: flex;
  gap: var(--gap-sm);
  font-size: 14px;
}
.parcel-info-card__meta-label {
  flex-shrink: 0;
  width: 58px;
  color: var(--text-secondary);
}
.parcel-info-card__meta-val {
  color: var(--text-regular);
}
.parcel-info-card__factors {
  padding-top: var(--gap-sm);
}
.parcel-info-card__factors-title {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: var(--gap-xs);
}
.parcel-info-card__factor {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  padding: 3px 0;
}
.parcel-info-card__factor-name {
  color: var(--text-regular);
}
.parcel-info-card__factor-val {
  font-weight: 600;
  color: var(--brand-dark-2);
}

/* 拆迁量与入选概率 */
.parcel-info-card__robust {
  margin-top: var(--gap-sm);
  padding-top: var(--gap-sm);
  border-top: 1px solid var(--border-lighter);
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.parcel-info-card__robust-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}
.parcel-info-card__robust-label {
  color: var(--text-secondary);
}
.parcel-info-card__robust-val {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--text-regular);
}

/* 因子贡献（可解释 AI） */
.parcel-info-card__contrib {
  margin-top: var(--gap-sm);
  padding-top: var(--gap-sm);
  border-top: 1px solid var(--border-lighter);
}
.parcel-info-card__contrib-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 3px;
}
.parcel-info-card__contrib-hint {
  font-size: 11px;
  color: var(--text-tertiary, var(--text-secondary));
}
.parcel-info-card__contrib-legend {
  display: flex;
  gap: var(--gap-sm);
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 5px;
}
.parcel-info-card__contrib-row {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  font-size: 12px;
  padding: 2px 0;
}
.parcel-info-card__contrib-name {
  width: 54px;
  flex-shrink: 0;
  color: var(--text-regular);
}
.parcel-info-card__contrib-bar-wrap {
  flex: 1;
  display: flex;
}
.parcel-info-card__contrib-bar {
  display: block;
  height: 5px;
  border-radius: 3px;
  transition: width var(--duration-base) var(--ease-out);
}
.parcel-info-card__contrib-bar.is-pos { background: #3B82F6; }
.parcel-info-card__contrib-bar.is-neg { background: #E5484D; }
.parcel-info-card__contrib-val {
  width: 48px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.parcel-info-card__contrib-val.is-pos { color: #2563EB; }
.parcel-info-card__contrib-val.is-neg { color: #C42B2F; }

/* 右侧滑入过渡 */
.parcel-card-enter-active,
.parcel-card-leave-active {
  transition: transform var(--duration-slow) var(--ease-out), opacity var(--duration-base) ease;
}
.parcel-card-enter-from,
.parcel-card-leave-to {
  transform: translateX(16px);
  opacity: 0;
}
</style>
