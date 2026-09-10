/** AI 交互状态：对话历史、解析结果、模板（模块 2） */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage, ParseResult } from '../types/ai'
import { parseRequirement, sendChat } from '../api/ai'
import { TEMPLATES } from '../mock/aiChat'
import { useConfigStore, DEFAULT_AREA_TOLERANCE, FACTOR_DEFS } from './config'
import { areaWindow } from '../utils/area'

let seq = 0
function nextId(): string {
  seq += 1
  return `msg-${Date.now()}-${seq}`
}

/**
 * 拼接 AI 分析过程 + 权重数值。
 * 演示口径：权重由「选址偏好」三档归一化计算（等同后台计算结果的展示）。
 */
function buildAnalysis(r: ParseResult, weights: Record<string, number>): string {
  const kw = r.matchedKeywords.length ? `（命中关键词：${r.matchedKeywords.join('、')}）` : ''
  const rows = FACTOR_DEFS.map(
    (f) => `   · ${f.name} ${((weights[f.id] ?? 0) * 100).toFixed(1)}%`
  )
  // 用地规模约束：仅当需求里提到占地面积时输出
  const areaLine =
    r.targetAreaHa === undefined
      ? '   · 未指定用地规模，按最小面积约束筛选'
      : (() => {
          const w = areaWindow(r.targetAreaHa, DEFAULT_AREA_TOLERANCE)
          return (
            `   · 目标 ${r.targetAreaHa} 公顷（原表述「${r.targetAreaText ?? ''}」），` +
            `允许上下浮动 ${DEFAULT_AREA_TOLERANCE * 100}% → ${w.lo}–${w.hi} 公顷`
          )
        })()
  return [
    '【AI 分析过程】',
    `1. 需求识别：解析您描述的选址需求，匹配到行业门类「${r.scenarioName}」${kw}。`,
    `2. 约束判定：该门类下建议启用 ${r.constraints.length} 项硬约束，命中禁区即一票否决。`,
    '3. 用地规模：',
    areaLine,
    '4. 权重计算：结合您在「选址偏好」中的在意程度，归一化后得到各维度权重：',
    ...rows,
    '5. 结论：以上约束与权重已同步用于选址计算，可直接点击「开始选址」。',
  ].join('\n')
}

export const useAiStore = defineStore('ai', () => {
  const messages = ref<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '您好，我是选址助手。请先在上方选择行业门类、在「选址偏好」中设置各维度的在意程度，也可用一句话描述需求（如"为装备制造项目选址"），我会给出分析过程与权重数值。',
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    },
  ])
  const thinking = ref(false)
  const parseResult = ref<ParseResult | null>(null)
  const templates = ref(TEMPLATES)

  /** 解析需求：输出分析过程 + 权重数值（以对话消息呈现，不弹卡片） */
  async function parse(text: string): Promise<ParseResult | null> {
    push('user', text)
    thinking.value = true
    try {
      const r = await parseRequirement(text)
      parseResult.value = r
      const config = useConfigStore()
      push('assistant', buildAnalysis(r, config.computeWeights()))
      return r
    } finally {
      thinking.value = false
    }
  }

  /** 普通对话 */
  async function chat(text: string): Promise<void> {
    push('user', text)
    thinking.value = true
    try {
      const reply = await sendChat(messages.value, text)
      push('assistant', reply)
    } finally {
      thinking.value = false
    }
  }

  function push(role: 'user' | 'assistant', content: string): void {
    messages.value.push({
      id: nextId(),
      role,
      content,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    })
  }

  /** 推送计算进度（开始选址时逐阶段显示在聊天框，作为助手消息） */
  function pushProgress(label: string): void {
    push('assistant', `▸ ${label}`)
  }

  function clearParse(): void {
    parseResult.value = null
  }

  return { messages, thinking, parseResult, templates, parse, chat, pushProgress, clearParse }
})
