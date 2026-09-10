/** AI 需求交互类型（模块 2） */

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  time: string
}

/** AI 解析结果：输出约束 + 初始权重（模块 2.4） */
export interface ParseResult {
  scenarioId: string
  scenarioName: string
  matchedKeywords: string[]
  /** 建议启用的约束 id 集合 */
  constraints: string[]
  /** 建议初始权重（已归一化） */
  weights: Record<string, number>
  /** 解析说明 */
  explanation: string
  /** 用户提到的用地规模目标（公顷）；未提及则为 undefined，此时不施加面积约束 */
  targetAreaHa?: number
  /** 用地规模的原始表述（如「500亩」），用于对话回显 */
  targetAreaText?: string
}

export interface RequirementTemplate {
  id: string
  label: string
  text: string
  scenarioId: string
}
