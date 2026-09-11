<script setup lang="ts">
/**
 * AI 能力卡片：偏好学习模型的指标、学习权重与专家权重对比、消融实验。
 *
 * 模型以「控规工业地块是否已被实际开发」为标签，从临桂区真实开发事实中
 * 反推区位偏好权重（详见 backend/app/services/ai_model.py）。
 * 后端不可用时（mock 模式）整卡自动隐藏，不影响演示。
 */
import { computed, onMounted, ref } from 'vue'
import { getAiModel, type AiModelInfo } from '../../api/ai'
import { FACTOR_DEFS, WEIGHT_MODES, useConfigStore } from '../../store/config'
import { useResultStore } from '../../store/result'

const config = useConfigStore()
const result = useResultStore()
const model = ref<AiModelInfo | null>(null)
const loading = ref(false)
const failed = ref(false)
const showDetail = ref(false)

/** 柱状条相对最大值的宽度（%） */
const maxWeight = computed(() => {
  const lw = model.value?.learned_weights ?? {}
  const ew = result.response?.expert_weights ?? {}
  const vals = [...Object.values(lw), ...Object.values(ew)]
  return vals.length ? Math.max(...vals) : 1
})
const barW = (v: number): string => `${Math.max(2, (v / (maxWeight.value || 1)) * 100)}%`

/** 学习权重 vs 专家权重（专家权重来自最近一次计算，未计算时为空） */
const rows = computed(() => {
  const lw = model.value?.learned_weights
  if (!lw) return []
  const ew = result.response?.expert_weights
  return FACTOR_DEFS.map((f) => ({
    id: f.id,
    name: f.name,
    learned: lw[f.id] ?? 0,
    expert: ew ? (ew[f.id] ?? 0) : null,
  }))
})

/** 消融实验按 AUC 降序 */
const ablations = computed(() => {
  const a = model.value?.ablation ?? {}
  return Object.entries(a)
    .map(([name, v]) => ({ name, ...v }))
    .sort((x, y) => y.auc - x.auc)
})

async function load(): Promise<void> {
  loading.value = true
  failed.value = false
  try {
    model.value = await getAiModel()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="!failed" class="ai-card">
    <div class="ai-card__title">
      <span>AI 偏好学习</span>
      <span class="ai-card__badge">机器学习</span>
    </div>

    <div class="ai-card__body">
      <template v-if="model?.available">
        <div class="ai-card__metrics">
          <div class="ai-card__metric">
            <span class="ai-card__metric-val">{{ model.metrics?.auc_mean?.toFixed(3) }}</span>
            <span class="ai-card__metric-label">交叉验证 AUC</span>
          </div>
          <div class="ai-card__metric">
            <span class="ai-card__metric-val">{{ model.samples }}</span>
            <span class="ai-card__metric-label">训练样本</span>
          </div>
          <div class="ai-card__metric">
            <span class="ai-card__metric-val">{{ model.positives }}</span>
            <span class="ai-card__metric-label">已开发地块</span>
          </div>
        </div>

        <div class="ai-card__note">
          以「控规地块是否已被实际开发」为标签，反推区位偏好权重
        </div>

        <div class="ai-card__weights">
          <div class="ai-card__weights-head">
            <span>维度</span>
            <span class="ai-card__legend">
              <i class="ai-card__dot ai-card__dot--ai" />AI
              <i class="ai-card__dot ai-card__dot--expert" />专家
            </span>
          </div>
          <div v-for="r in rows" :key="r.id" class="ai-card__row">
            <span class="ai-card__row-name">{{ r.name }}</span>
            <span class="ai-card__bars">
              <i class="ai-card__bar ai-card__bar--ai" :style="{ width: barW(r.learned) }" />
              <i
                v-if="r.expert !== null"
                class="ai-card__bar ai-card__bar--expert"
                :style="{ width: barW(r.expert) }"
              />
            </span>
            <span class="ai-card__row-val">{{ (r.learned * 100).toFixed(1) }}%</span>
          </div>
        </div>

        <div class="ai-card__source">
          <div class="ai-card__source-label">权重来源</div>
          <el-radio-group v-model="config.weightMode" size="small">
            <el-radio-button v-for="m in WEIGHT_MODES" :key="m.id" :value="m.id">
              {{ m.name }}
            </el-radio-button>
          </el-radio-group>
          <div class="ai-card__source-desc">
            {{ WEIGHT_MODES.find((m) => m.id === config.weightMode)?.desc }}
          </div>
        </div>

        <button class="ai-card__toggle" @click="showDetail = !showDetail">
          {{ showDetail ? '收起模型细节 ▴' : '查看消融实验与局限 ▾' }}
        </button>

        <div v-if="showDetail" class="ai-card__detail">
          <div class="ai-card__detail-title">消融实验（5 折交叉验证 AUC）</div>
          <div v-for="a in ablations" :key="a.name" class="ai-card__ablation">
            <span class="ai-card__ablation-name">{{ a.name }}</span>
            <span class="ai-card__ablation-val">{{ a.auc.toFixed(3) }}</span>
          </div>
          <div class="ai-card__ablation ai-card__ablation--base">
            <span class="ai-card__ablation-name">随机基线</span>
            <span class="ai-card__ablation-val">0.500</span>
          </div>

          <div class="ai-card__detail-title">能力边界</div>
          <ul class="ai-card__limits">
            <li>样本仅 {{ model.samples }} 个地块，AUC 约 {{ model.metrics?.auc_mean?.toFixed(2) }}，折间波动 ±{{ model.metrics?.auc_std?.toFixed(2) }}</li>
            <li>规划因子对实际开发的解释力有限，说明开发决策还受供地节奏、招商等非空间因素影响</li>
            <li>本模型提供权重参照，<b>不作为选址最终依据</b></li>
            <li>{{ model.leakage_note }}</li>
          </ul>
        </div>
      </template>

      <div v-else class="ai-card__empty">
        {{ model?.reason ?? (loading ? '正在载入模型…' : '模型不可用') }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-card {
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border: 1px solid var(--glass-border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glass);
  overflow: hidden;
}
.ai-card__title {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  padding: 10px var(--gap-lg) 10px calc(var(--gap-lg) + 10px);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-lighter);
}
.ai-card__title::before {
  content: '';
  position: absolute;
  left: var(--gap-lg);
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  background: #7C5CE6;
  border-radius: 2px;
}
.ai-card__badge {
  font-size: 11px;
  font-weight: 500;
  color: #7C5CE6;
  background: rgba(124, 92, 230, 0.1);
  border: 1px solid rgba(124, 92, 230, 0.25);
  border-radius: 999px;
  padding: 1px 7px;
}
.ai-card__body {
  padding: var(--gap-sm) var(--gap-lg) var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ai-card__metrics {
  display: flex;
  justify-content: space-between;
  gap: var(--gap-sm);
}
.ai-card__metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  padding: 6px 0;
  background: rgba(124, 92, 230, 0.06);
  border-radius: var(--radius-sm);
}
.ai-card__metric-val {
  font-size: 17px;
  font-weight: 700;
  color: #6B4FD8;
  font-variant-numeric: tabular-nums;
}
.ai-card__metric-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 1px;
}
.ai-card__note {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}
.ai-card__weights {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ai-card__weights-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 2px;
}
.ai-card__legend {
  display: flex;
  align-items: center;
  gap: 4px;
}
.ai-card__dot {
  width: 7px;
  height: 7px;
  border-radius: 2px;
  display: inline-block;
}
.ai-card__dot--ai { background: #7C5CE6; }
.ai-card__dot--expert { background: #9AA4B2; }
.ai-card__row {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 13px;
}
.ai-card__row-name {
  width: 56px;
  flex-shrink: 0;
  color: var(--text-regular);
}
.ai-card__bars {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ai-card__bar {
  display: block;
  height: 5px;
  border-radius: 3px;
  transition: width var(--duration-base) var(--ease-out);
}
.ai-card__bar--ai { background: #7C5CE6; }
.ai-card__bar--expert { background: #9AA4B2; }
.ai-card__row-val {
  width: 46px;
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--brand-dark-2);
  font-weight: 600;
}
.ai-card__source {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-top: 8px;
  border-top: 1px solid var(--border-lighter);
}
.ai-card__source-label {
  font-size: 12px;
  color: var(--text-secondary);
}
.ai-card__source :deep(.el-radio-button__inner) {
  padding: 4px 8px;
  font-size: 12px;
}
.ai-card__source-desc {
  font-size: 11px;
  color: var(--text-tertiary, var(--text-secondary));
}
.ai-card__toggle {
  align-self: flex-start;
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #6B4FD8;
  cursor: pointer;
}
.ai-card__detail {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 6px;
  border-top: 1px solid var(--border-lighter);
}
.ai-card__detail-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-regular);
  margin: 6px 0 2px;
}
.ai-card__ablation {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-regular);
  padding: 1px 0;
}
.ai-card__ablation-name { color: var(--text-secondary); }
.ai-card__ablation-val {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.ai-card__ablation--base .ai-card__ablation-val { color: var(--text-secondary); }
.ai-card__limits {
  margin: 0;
  padding-left: 16px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--text-secondary);
}
.ai-card__empty {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 0;
}
</style>
