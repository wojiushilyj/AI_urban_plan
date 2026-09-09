<script setup lang="ts">
/**
 * AI 解析结果展示（模块 2.5）：识别门类 + 建议约束，支持一键应用。
 * 权重由「选址偏好」三档决定（store/config.ts），AI 不再覆盖权重。
 */
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAiStore } from '../../store/ai'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore } from '../../store/config'
import { useMapStore } from '../../store/map'
import { useResultStore } from '../../store/result'
import CardContainer from '../common/CardContainer.vue'

const ai = useAiStore()
const scenario = useScenarioStore()
const config = useConfigStore()
const map = useMapStore()
const result = useResultStore()

const pr = computed(() => ai.parseResult)

const constraintNames = computed(() => {
  const detail = scenario.detail
  if (!detail || !pr.value) return []
  return pr.value.constraints.map(
    (id) => detail.constraints.find((c) => c.id === id)?.name ?? id
  )
})

/** 一键应用：切换门类 + 应用约束子集（权重保持由偏好驱动） */
async function apply(): Promise<void> {
  if (!pr.value) return
  const detail = await scenario.switchScenario(pr.value.scenarioId)
  config.applyScenario(detail)
  const enabledSet = new Set(pr.value.constraints)
  for (const c of detail.constraints) {
    if (!c.required) config.constraints[c.id].enabled = enabledSet.has(c.id)
  }
  result.reset()
  map.selectedRank = null
  ElMessage.success(`已应用「${pr.value.scenarioName}」门类与约束，权重由选址偏好决定`)
}
</script>

<template>
  <CardContainer v-if="pr" title="AI 解析结果" :subtitle="`识别门类：${pr.scenarioName}`">
    <div class="parse-result">
      <div class="parse-result__row">
        <span class="parse-result__label">建议约束</span>
        <span class="parse-result__value">
          <el-tag v-for="n in constraintNames" :key="n" size="small" type="info" style="margin: 1px 3px 1px 0">{{ n }}</el-tag>
        </span>
      </div>
      <el-button type="primary" size="small" style="width: 100%; margin-top: 8px" @click="apply">
        ⚡ 一键应用门类与约束
      </el-button>
    </div>
  </CardContainer>
</template>

<style scoped>
.parse-result {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
}
.parse-result__row {
  display: flex;
  gap: 6px;
}
.parse-result__label {
  flex-shrink: 0;
  color: var(--text-secondary);
  width: 60px;
}
.parse-result__value {
  flex: 1;
  color: var(--text-regular);
  line-height: 1.8;
}
.parse-result__weight {
  display: inline-block;
  margin: 0 8px 2px 0;
  padding: 0 6px;
  background: var(--brand-light-9);
  color: var(--brand-dark-2);
  border-radius: 4px;
  font-size: 13px;
}
</style>
