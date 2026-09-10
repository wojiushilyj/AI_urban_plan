<script setup lang="ts">
/**
 * AI 需求交互主面板（模块 2）：门类选择 + 选址偏好 + AI 聊天卡片 + 开始选址。
 */
import { nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAiStore } from '../../store/ai'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore } from '../../store/config'
import { useResultStore } from '../../store/result'
import { useMapStore } from '../../store/map'
import ChatMessage from './ChatMessage.vue'
import ScenarioSwitcher from '../scenario/ScenarioSwitcher.vue'
import PreferenceCard from '../config/PreferenceCard.vue'
import CardContainer from '../common/CardContainer.vue'

const ai = useAiStore()
const scenario = useScenarioStore()
const config = useConfigStore()
const result = useResultStore()
const map = useMapStore()
const input = ref('')
const messagesEl = ref<HTMLElement>()

// 新消息到达时自动滚动到底部
watch(
  () => ai.messages.length,
  async () => {
    await nextTick()
    messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight })
  }
)

async function startSelection(): Promise<void> {
  if (!scenario.detail) return
  // 1) 需求文本作为用户消息显示 + 调用 AI 分析（输出分析过程，识别门类与约束）
  const text = input.value.trim()
  if (text && !ai.thinking) {
    input.value = ''
    const pr = await ai.parse(text)
    // 2) 自动应用 AI 识别出的门类、约束与用地规模
    if (pr) {
      const detail = await scenario.switchScenario(pr.scenarioId)
      config.applyScenario(detail)
      const enabledSet = new Set(pr.constraints)
      for (const c of detail.constraints) {
        if (!c.required) config.constraints[c.id].enabled = enabledSet.has(c.id)
      }
      // 需求中提到占地面积 → 记为用地规模目标（未提到则清空，不做面积匹配）
      config.targetAreaHa = pr.targetAreaHa ?? null
      result.reset()
      map.selectedRank = null
    }
  }
  // 3) 权重校验后执行选址计算
  if (Math.abs(config.weightSum - 1) >= 0.01) {
    ElMessage.warning('权重之和不为 1，请重新选择行业门类')
    return
  }
  await result.run(scenario.detail)
  if (result.error) ElMessage.error(result.error)
  else ElMessage.success('选址计算完成，结果已渲染到地图与右侧面板')
}
</script>

<template>
  <div class="chat-panel">
    <div class="chat-panel__config">
      <CardContainer title="门类选择">
        <ScenarioSwitcher class="chat-panel__scenario" />
      </CardContainer>
      <PreferenceCard />
    </div>

    <div class="chat-panel__chat">
      <div ref="messagesEl" class="chat-panel__messages">
        <ChatMessage v-for="m in ai.messages" :key="m.id" :msg="m" />
        <div v-if="ai.thinking" class="chat-panel__thinking">
          <span class="dot" /><span class="dot" /><span class="dot" /> 正在解析…
        </div>
      </div>

      <div class="chat-panel__input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="5"
          resize="none"
          placeholder="描述选址需求，例如：在临桂区为装备制造项目寻找连片用地，占地面积约 20 公顷，交通便利、产业配套好…"
          @keydown.enter.exact.prevent="startSelection"
        />
        <div class="chat-panel__actions">
          <el-button type="primary" size="large" class="chat-panel__start" :loading="result.running || ai.thinking" @click="startSelection">▶ 开始选址</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.chat-panel__config {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  padding: var(--gap-md);
  border-bottom: 1px solid var(--border-lighter);
}
.chat-panel__config :deep(.el-select) {
  width: 100% !important;
}
/* AI 聊天卡片：消息展示 + 输入框同一卡片 */
.chat-panel__chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: var(--gap-md);
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.chat-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--gap-md);
}
.chat-panel__input {
  padding: var(--gap-md);
  border-top: 1px solid var(--border-lighter);
}
/* 输入框：占位符 11px，输入文字 12px */
.chat-panel__input :deep(.el-textarea__inner) {
  font-size: 12px;
  line-height: 1.6;
}
.chat-panel__input :deep(.el-textarea__inner::placeholder) {
  font-size: 11px;
}
.chat-panel__actions {
  display: flex;
  margin-top: 8px;
}
.chat-panel__start {
  width: 100%;
  flex: 1;
}
.chat-panel__thinking {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--text-secondary);
  padding: 6px 12px;
}
.chat-panel__thinking .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-light-5);
  animation: blink 1.2s infinite ease-in-out;
}
.chat-panel__thinking .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.chat-panel__thinking .dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%, 80%, 100% { opacity: 0.25; }
  40% { opacity: 1; }
}
</style>
