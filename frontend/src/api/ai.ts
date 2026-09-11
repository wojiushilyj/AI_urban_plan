/** AI 需求解析 / 偏好学习模型接口（模块 8.1） */
import type { ChatMessage, ParseResult } from '../types/ai'
import { get, post } from './client'
import { mockChat, mockParseRequirement } from '../mock/aiChat'

export async function parseRequirement(text: string): Promise<ParseResult> {
  return post<ParseResult>('/api/ai/parse', { text }, () => mockParseRequirement(text))
}

export async function sendChat(history: ChatMessage[], text: string): Promise<string> {
  return post<string>('/api/ai/chat', { history, text }, () => mockChat(history, text))
}

/* ============ 偏好学习模型（AI 能力的对外呈现） ============ */

export interface AiModelMetrics {
  auc_mean: number
  auc_std: number
  acc_mean: number
  folds: number[]
}

export interface AiModelAblation {
  n_features: number
  features: string[]
  auc: number
  auc_std: number
  acc: number
}

export interface AiModelInfo {
  available: boolean
  reason?: string
  algo?: string
  task?: string
  samples?: number
  positives?: number
  negatives?: number
  positive_rate?: number
  features?: string[]
  feature_labels?: Record<string, string>
  coefficients?: Record<string, number>
  metrics?: AiModelMetrics
  ablation?: Record<string, AiModelAblation>
  univariate_auc?: Record<string, number>
  /** 学习到的 5 维权重，可直接作为选址权重 */
  learned_weights?: Record<string, number>
  /** 数据泄漏规避说明 */
  leakage_note?: string
  group_contrast?: Record<string, {
    label: string
    developed_mean: number
    undeveloped_mean: number
    diff: number
  }>
}

/**
 * 拉取偏好学习模型的指标与学习权重。
 * mock 模式下返回 `available: false`，前端据此优雅降级（不展示 AI 面板）。
 */
export async function getAiModel(): Promise<AiModelInfo> {
  return get<AiModelInfo>('/api/ai/model', () => ({ available: false, reason: 'mock 模式' }))
}
