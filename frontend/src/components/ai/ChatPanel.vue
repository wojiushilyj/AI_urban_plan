<script setup lang="ts">
/**
 * AI 需求交互主面板（模块 2）：
 * 支持两种模式：
 * 1. 经典多准则选址（门类选择 + 偏好滑动条 + 开始选址）
 * 2. LangGraph 空间智能体（PostGIS 检索 + 三区三线审查 + 双方案比选）
 */
import { nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useAiStore } from '../../store/ai'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore } from '../../store/config'
import { useResultStore } from '../../store/result'
import { useMapStore } from '../../store/map'
import { useAgentStore } from '../../store/agent'
import ChatMessage from './ChatMessage.vue'
import ScenarioSwitcher from '../scenario/ScenarioSwitcher.vue'
import PreferenceTabsCard from '../config/PreferenceTabsCard.vue'
import AppIcon from '../common/AppIcon.vue'

const ai = useAiStore()
const scenario = useScenarioStore()
const config = useConfigStore()
const result = useResultStore()
const map = useMapStore()
const agent = useAgentStore()
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
  config.targetAreaHa = pr.targetAreaHa ?? null
  result.reset()
  map.selectedRank = null
}

/** 回车发送：根据当前模式分流 */
async function onSend(): Promise<void> {
  const text = input.value.trim()
  if (!text || ai.thinking || agent.running) return
  input.value = ''
  if (agent.mode === 'langgraph') {
    agent.request.query = text
    await agent.run()
  } else {
    await applyParse(text)
  }
}

/** 开始经典多准则选址 */
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

/** 启动 LangGraph 空间智能体 */
async function startAgentSelection(): Promise<void> {
  const text = input.value.trim()
  if (text) {
    agent.request.query = text
    input.value = ''
  }
  await agent.run()
  if (agent.error) ElMessage.error(agent.error)
  else ElMessage.success('LangGraph 智能体决策完成，双方案比选已展开')
}

/** 预设意图快捷填充 */
function applyPreset(query: string, hqRange: [number, number], facRange: [number, number], buffer: number): void {
  agent.request.query = query
  agent.request.hq_min_ha = hqRange[0]
  agent.request.hq_max_ha = hqRange[1]
  agent.request.factory_min_ha = facRange[0]
  agent.request.factory_max_ha = facRange[1]
  agent.request.sanitary_buffer_m = buffer
  ElMessage.info('已载入场景预设参数')
}
</script>

<template>
  <div class="chat-panel">
    <!-- 模式切换分段开关 -->
    <div class="mode-bar">
      <button
        type="button"
        class="mode-btn"
        :class="{ 'is-active': agent.mode === 'classic' }"
        @click="agent.mode = 'classic'"
      >
        🎯 规划多准则选址
      </button>
      <button
        type="button"
        class="mode-btn"
        :class="{ 'is-active': agent.mode === 'langgraph' }"
        @click="agent.mode = 'langgraph'"
      >
        🤖 LangGraph 空间智能体
      </button>
    </div>

    <!-- 1. 经典多准则选址配置区 -->
    <div v-if="agent.mode === 'classic'" class="chat-panel__config">
      <div class="chat-panel__field">
        <div class="field-label">门类选择</div>
        <ScenarioSwitcher />
      </div>
      <PreferenceTabsCard />
    </div>

    <!-- 2. LangGraph 智能体选址需求配置区 -->
    <div v-else class="chat-panel__config agent-config-panel">
      <div class="agent-chip-box">
        <div class="field-label">🎯 快捷选址意图预设</div>
        <div class="chip-group">
          <button
            type="button"
            class="chip-btn"
            @click="applyPreset(
              '拟在桂林临桂区建设大型生物医药项目，包含B2研发总部与M1洁净生产基地，要求临近高校产学研平台并靠近货运干道，需开展集中连片与分地块方案比选。',
              [1.0, 5.0],
              [5.0, 20.0],
              300
            )"
          >
            💊 研发总部 + 生产基地双方案比选
          </button>
          <button
            type="button"
            class="chip-btn"
            @click="applyPreset(
              '拟选址原料药与现代中药制剂生产基地，需严格落实500米卫生防护距离，规避居民敏感点，优先靠近污水管网与给水主管线。',
              [1.0, 4.0],
              [10.0, 25.0],
              500
            )"
          >
            🧪 原料药发酵基地 (500m强防护)
          </button>
          <button
            type="button"
            class="chip-btn"
            @click="applyPreset(
              '重点布局高端生物医药研发总部与创新孵化平台，选用B2商务用地，要求高度协同高等医学教育院校与综合医院临床试验资源。',
              [1.5, 6.0],
              [3.0, 10.0],
              300
            )"
          >
            🔬 临床医药研发中心 (高校协同)
          </button>
        </div>
      </div>

      <div class="agent-sliders">
        <div class="slider-row">
          <span class="slider-label">总部面积 (B2):</span>
          <span class="slider-val">{{ agent.request.hq_min_ha }} ~ {{ agent.request.hq_max_ha }} ha</span>
        </div>
        <div class="slider-row">
          <span class="slider-label">生产基地 (M1):</span>
          <span class="slider-val">{{ agent.request.factory_min_ha }} ~ {{ agent.request.factory_max_ha }} ha</span>
        </div>
        <div class="slider-row">
          <span class="slider-label">卫生安全隔离:</span>
          <div class="radio-row">
            <label class="radio-label">
              <input v-model="agent.request.sanitary_buffer_m" type="radio" :value="300" />
              300m (制剂厂房)
            </label>
            <label class="radio-label">
              <input v-model="agent.request.sanitary_buffer_m" type="radio" :value="500" />
              500m (发酵合成)
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- 选址助手对话卡 -->
    <div class="chat-card" :class="{ 'is-agent-card': agent.mode === 'langgraph' }">
      <div class="chat-head">
        <div class="chat-head__left">
          <AppIcon name="assistant" :size="28" />
          <span class="chat-head__name">{{ agent.mode === 'langgraph' ? 'LangGraph 选址智能体' : '选址助手' }}</span>
          <span class="chat-head__badge">{{ agent.mode === 'langgraph' ? 'StateGraph' : 'AI' }}</span>
        </div>
        <div class="chat-head__online">
          <i class="dot-on" />
          {{ agent.mode === 'langgraph' ? 'PostGIS 在线' : '在线' }}
        </div>
      </div>

      <div ref="messagesEl" class="chat-body">
        <ChatMessage v-for="m in ai.messages" :key="m.id" :msg="m" />
        <div v-if="ai.thinking || agent.running" class="chat-panel__thinking">
          <span class="dot" /><span class="dot" /><span class="dot" />
          {{ agent.running ? '智能体正在执行 6 阶段循环决策流…' : '正在解析…' }}
        </div>
        <div class="chat-hint">
          {{ agent.mode === 'langgraph' ? '例：临桂区选址生物医药研发基地，需兼顾高校产学研协同与500m卫生防护。' : '例：临桂区找 20 公顷连片工业用地。' }}
        </div>
      </div>

      <div class="chat-input">
        <input
          v-model="input"
          class="chat-input__field"
          type="text"
          :placeholder="agent.mode === 'langgraph' ? '输入医药选址诉求，回车由智能体决策…' : '描述选址需求，回车发送…'"
          @keydown.enter="onSend"
        />
      </div>
    </div>

    <!-- 主行动按钮 -->
    <button
      v-if="agent.mode === 'classic'"
      class="cta"
      type="button"
      :disabled="result.running || ai.thinking"
      @click="startSelection"
    >
      <AppIcon name="play" :size="16" />
      <span>{{ result.running ? '选址计算中…' : '开始选址' }}</span>
    </button>
    <button
      v-else
      class="cta cta--agent"
      type="button"
      :disabled="agent.running"
      @click="startAgentSelection"
    >
      <span class="cta-icon">🚀</span>
      <span>{{ agent.running ? '智能体 6 阶段决策中…' : '启动 LangGraph 选址智能体' }}</span>
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

/* 顶部模式切换栏 */
.mode-bar {
  display: flex;
  background: #E5E7EB;
  padding: 3px;
  border-radius: 8px;
  margin: var(--panel-pad-left) var(--panel-pad-left) 8px;
  gap: 2px;
}
.mode-btn {
  flex: 1;
  padding: 6px 4px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #4B5563;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  white-space: nowrap;
}
.mode-btn:hover {
  color: #111827;
}
.mode-btn.is-active {
  background: #FFFFFF;
  color: #1C7D8C;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* 配置区 */
.chat-panel__config {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 0 var(--panel-pad-left) 12px;
}
.chat-panel__field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.field-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}

/* LangGraph 专属配置小卡片 */
.agent-config-panel {
  gap: 10px;
}
.agent-chip-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chip-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.chip-btn {
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 11px;
  color: #374151;
  text-align: left;
  cursor: pointer;
  line-height: 1.35;
  transition: all 0.15s;
}
.chip-btn:hover {
  background: #F0FDFA;
  border-color: #14B8A6;
  color: #0F766E;
}
.agent-sliders {
  background: #FFFFFF;
  border: 1px solid var(--border-lighter);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
}
.slider-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.slider-label {
  color: #6B7280;
  font-weight: 500;
}
.slider-val {
  color: #111827;
  font-weight: 700;
}
.radio-row {
  display: flex;
  gap: 8px;
}
.radio-label {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  cursor: pointer;
  color: #374151;
}

/* 对话卡 */
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
  transition: border-color 0.2s;
}
.chat-card.is-agent-card {
  border-color: #14B8A6;
  box-shadow: 0 0 0 1px rgba(20, 184, 166, 0.15);
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
  background: #1C7D8C;
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

/* 主行动按钮 */
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
.cta--agent {
  background: #1C7D8C;
  box-shadow: 0 6px 18px rgba(28, 125, 140, 0.28);
}
.cta--agent:hover:not(:disabled) {
  background: #0F4C55;
  box-shadow: 0 10px 24px rgba(28, 125, 140, 0.34);
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
