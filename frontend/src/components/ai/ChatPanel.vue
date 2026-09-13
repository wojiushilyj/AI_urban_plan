<script setup lang="ts">
/**
 * AI 需求交互主面板（模块 2）：门类选择 + 选址偏好（含 AI 偏好学习页签）+ 选址助手对话卡 + 开始选址。
 * 形态对齐设计稿：左栏为扁平列表（无卡片外壳），对话卡为「头部 / 消息体 / 输入行」三段结构，
 * 「开始选址」抽为独立的 48px 胶囊主行动按钮（原型 .cta）。
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
import PreferenceTabsCard from '../config/PreferenceTabsCard.vue'
import AppIcon from '../common/AppIcon.vue'

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

/** 把一段需求文本交给 AI 解析，并落库为门类 / 约束 / 用地规模 */
async function applyParse(text: string): Promise<void> {
  const pr = await ai.parse(text)
  if (!pr) return
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

/** 发送：仅做需求解析与权重回显（对话区可见分析过程） */
async function onSend(): Promise<void> {
  const text = input.value.trim()
  if (!text || ai.thinking) return
  input.value = ''
  await applyParse(text)
}

/** 开始选址：先解析未发送的需求，再执行选址计算 */
async function startSelection(): Promise<void> {
  if (!scenario.detail) return
  const text = input.value.trim()
  if (text && !ai.thinking) {
    input.value = ''
    await applyParse(text)
  }
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
    <!-- 配置区：门类选择 + 偏好 / AI 学习 -->
    <div class="chat-panel__config">
      <div class="chat-panel__field">
        <div class="field-label">门类选择</div>
        <ScenarioSwitcher />
      </div>
      <PreferenceTabsCard />
    </div>

    <!-- 选址助手对话卡（原型 .chat）：弹性填充配置区之下的剩余空间，不留大块空白 -->
    <div class="chat-card">
      <div class="chat-head">
        <div class="chat-head__left">
          <AppIcon name="assistant" :size="28" />
          <span class="chat-head__name">选址助手</span>
          <span class="chat-head__badge">AI</span>
        </div>
        <div class="chat-head__online"><i class="dot-on" />在线</div>
      </div>

      <div ref="messagesEl" class="chat-body">
        <ChatMessage v-for="m in ai.messages" :key="m.id" :msg="m" />
        <div v-if="ai.thinking" class="chat-panel__thinking">
          <span class="dot" /><span class="dot" /><span class="dot" /> 正在解析…
        </div>
        <div class="chat-hint">例：临桂区找 20 公顷连片工业用地。</div>
      </div>

      <div class="chat-input">
        <input
          v-model="input"
          class="chat-input__field"
          type="text"
          placeholder="描述选址需求…"
          @keydown.enter="onSend"
        />
        <button
          class="chat-input__send"
          type="button"
          title="发送"
          :disabled="ai.thinking"
          @click="onSend"
        >
          <AppIcon name="send" :size="26" />
        </button>
      </div>
    </div>

    <!-- 主行动按钮（原型 .cta） -->
    <button
      class="cta"
      type="button"
      :disabled="result.running || ai.thinking"
      @click="startSelection"
    >
      <AppIcon name="play" :size="16" />
      <span>{{ result.running ? '选址计算中…' : '开始选址' }}</span>
    </button>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
/*
 * 配置区（门类选择 + 偏好 / AI 学习）：
 * 可收缩 + 内部滚动，矮屏上优先压缩本区，保证对话卡与 CTA 不被挤没。
 */
.chat-panel__config {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: var(--panel-pad-left);
}
.chat-panel__field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.field-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
}

/* ============ 对话卡（原型 .chat） ============ */
/* 弹性填充配置区之下的剩余空间（基准 0：高度只取决于剩余空间，与消息条数无关），
   「开始选址」稳定贴底、进度消息追加时上方卡片高度零变动 */
.chat-card {
  flex: 1 1 0;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  margin: 0 var(--panel-pad-left) 12px;
  background: #fff;
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-card);
  overflow: hidden;
}
.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-subtle);
  flex: none;
}
.chat-head__left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.chat-head__name {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  white-space: nowrap;
}
.chat-head__badge {
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: var(--brand);
  padding: 2px 7px;
  border-radius: var(--radius-pill);
  line-height: 1.35;
  flex: none;
}
.chat-head__online {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 500;
  color: var(--c-success);
  flex: none;
}
.dot-on {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-success);
  flex: 0 0 6px;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
/* 需求示例提示（原型 .hint：白底描边，与灰底气泡区分） */
.chat-hint {
  background: #fff;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  padding: 8px;
  font-size: 11px;
  line-height: 17px;
  color: var(--muted);
}

.chat-input {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px;
  border-top: 1px solid var(--border-lighter);
  flex: none;
}
.chat-input__field {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font-family: var(--font);
  font-size: 13px;
  color: var(--ink-2);
}
.chat-input__field::placeholder {
  color: var(--placeholder);
}
.chat-input__send {
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  padding: 0;
  border: 0;
  background: transparent;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: 0.16s;
}
.chat-input__send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ============ 主行动按钮（原型 .cta） ============ */
.cta {
  flex: none;
  height: 48px;
  margin: 0 var(--panel-pad-left) var(--panel-pad-left);
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--brand);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  cursor: pointer;
  font-family: var(--font);
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.28);
  transition: 0.18s;
}
.cta:hover:not(:disabled) {
  background: var(--brand-dark-2);
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.34);
}
.cta:active:not(:disabled) {
  transform: translateY(0);
}
.cta:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  box-shadow: none;
}

.chat-panel__thinking {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 6px 10px;
}
.chat-panel__thinking .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-light-5);
  animation: blink 1.2s infinite ease-in-out;
}
.chat-panel__thinking .dot:nth-child(2) { animation-delay: 0.2s; }
.chat-panel__thinking .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0%, 80%, 100% { opacity: 0.25; }
  40% { opacity: 1; }
}
</style>
