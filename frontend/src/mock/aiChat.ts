/**
 * AI 需求解析 / 对话 mock（模块 2）。
 * 按关键词匹配行业门类 → 输出约束子集 + 初始权重。
 */
import type { ChatMessage, ParseResult, RequirementTemplate } from '../types/ai'
import { SCENARIOS } from './scenarios'
import { sleep } from './delay'

/** 关键词 → 行业门类匹配规则（顺序即优先级，具体词在前） */
const KEYWORD_MAP: { keywords: string[]; scenarioId: string }[] = [
  { keywords: ['矿', '采矿', '砂石', '石料', '矿权', '采石'], scenarioId: 'B' },
  { keywords: ['消费品', '食品', '纺织', '服装', '家具', '家电', '轻工', '日用'], scenarioId: 'C1' },
  { keywords: ['原材料', '钢铁', '化工', '建材', '造纸', '石化', '有色', '水泥', '中间品'], scenarioId: 'C2' },
  { keywords: ['装备', '机械', '汽车', '电子', '船舶', '航空航天', '设备', '制造'], scenarioId: 'C3' },
  { keywords: ['电力', '热力', '燃气', '供水', '电厂', '电站', '变电站', '能源', '水生产'], scenarioId: 'D' },
  { keywords: ['建筑', '施工', '搅拌站', '预制', '构件', '混凝土'], scenarioId: 'E' },
  { keywords: ['物流', '仓储', '货运', '快递', '邮政', '枢纽', '分拨', '交通运输'], scenarioId: 'G' },
  { keywords: ['信息', '软件', '数据', '互联网', '通信', '数据中心', '云计算'], scenarioId: 'I' },
  { keywords: ['科研', '科学', '研究', '实验室', '检验', '检测', '研发'], scenarioId: 'M' },
  { keywords: ['水利', '环保', '污水', '垃圾', '固废', '环卫', '公共设施', '环境'], scenarioId: 'N' },
]

export const TEMPLATES: RequirementTemplate[] = [
  {
    id: 't-mining',
    label: '⛏️ 采矿业',
    text: '为砂石土矿开发寻找矿业权区块，资源潜力大、覆盖层薄、运输距离短，避开生态红线与饮用水源保护区。',
    scenarioId: 'B',
  },
  {
    id: 't-consumer',
    label: '🏭 消费品制造',
    text: '为食品加工项目寻找地块，劳动力充足、贴近城镇市场、交通便利、地块规整。',
    scenarioId: 'C1',
  },
  {
    id: 't-material',
    label: '🏗️ 原材料制造',
    text: '为建材（水泥/混凝土）项目选址，远离居民点、临近原料地、地势平坦、运输方便。',
    scenarioId: 'C2',
  },
  {
    id: 't-equipment',
    label: '⚙️ 装备制造',
    text: '为装备制造项目寻找连片用地，用地规模大、物流便利、产业配套好、拆迁量小。',
    scenarioId: 'C3',
  },
  {
    id: 't-energy',
    label: '🔌 能源公用',
    text: '为变电站/供水设施选址，远离居民点、临近水源或并网点、避开行洪区与机场限高区。',
    scenarioId: 'D',
  },
  {
    id: 't-logistics',
    label: '🚚 物流仓储',
    text: '为物流园区选址，紧邻高速出入口、地块规整连片、地势平坦。',
    scenarioId: 'G',
  },
  {
    id: 't-it',
    label: '💻 信息技术服务',
    text: '为数据中心选址，电力保障充足、网络基础设施好、远离地质灾害高易发区。',
    scenarioId: 'I',
  },
  {
    id: 't-env',
    label: '♻️ 环境设施',
    text: '为污水处理厂选址，远离居民点与饮用水源、地质条件适宜、便于管网接入。',
    scenarioId: 'N',
  },
]

/** mock：POST /api/ai/parse */
export async function mockParseRequirement(text: string): Promise<ParseResult> {
  await sleep(900) // 模拟 LLM 思考

  const hit = KEYWORD_MAP.find((m) => m.keywords.some((k) => text.includes(k)))
  const scenarioId = hit?.scenarioId ?? 'B'
  const scenario = SCENARIOS[scenarioId]

  // 初始权重 = AHP 模板权重轻微扰动后归一化
  const weights: Record<string, number> = {}
  let sum = 0
  for (const [k, v] of Object.entries(scenario.weights_ahp)) {
    const w = Math.max(0.05, v * (1 + (Math.random() - 0.5) * 0.24))
    weights[k] = w
    sum += w
  }
  for (const k of Object.keys(weights)) weights[k] = Math.round((weights[k] / sum) * 100) / 100

  // 约束：required 全选 + 非必选按语义随机启用
  const matchedKeywords = KEYWORD_MAP.flatMap((m) => m.keywords.filter((k) => text.includes(k)))
  const constraints = scenario.constraints
    .filter((c) => c.required || Math.random() > 0.5)
    .map((c) => c.id)

  return {
    scenarioId,
    scenarioName: scenario.name,
    matchedKeywords,
    constraints,
    weights,
    explanation: `已解析您的选址需求：识别到行业门类「${scenario.name}」${
      matchedKeywords.length ? `（命中关键词：${matchedKeywords.join('、')}）` : ''
    }；建议启用 ${constraints.length} 项硬约束，权重可在上方「选址偏好」中设置。`,
  }
}

/** mock：对话回复 */
export async function mockChat(history: ChatMessage[], userText: string): Promise<string> {
  await sleep(700)
  const last = history[history.length - 1]
  const q = userText || last?.content || ''
  if (q.includes('权重') || q.includes('偏好')) {
    return '指标权重由上方「选址偏好」的三档（在意/一般/不在意）决定，系统自动归一化为 5 个维度（城市规划/交通物流/产业协同/基础配套/建造成本）的权重。您可以随时调整各维度的在意程度。'
  }
  if (q.includes('约束') || q.includes('红线') || q.includes('农田')) {
    return '硬约束为布尔一票否决项：永久基本农田、生态保护红线等命中即剔除。带缓冲距离的约束（如河湖管理范围 30m）会自动应用，命中禁区即从候选地块中剔除。'
  }
  if (q.includes('算法') || q.includes('TOPSIS') || q.includes('聚类')) {
    return '当前支持三种算法：TOPSIS（逼近理想解排序，适合综合评价）、多元回归（拟合历史选址偏好）、K-Means 聚类（按因子特征自动分组）。竞赛演示推荐 TOPSIS。'
  }
  if (q.includes('导出') || q.includes('报告')) {
    return '计算完成后，可在右侧「报告导出」页一键生成选址报告，支持 PDF（打印）、Excel（权重与候选表）、图纸图片三种格式导出。'
  }
  return `收到您的需求。我可以帮您：① 解析自然语言选址需求，自动匹配行业门类并给出约束建议；② 解释任意指标含义；③ 介绍算法选型。当前为样例数据演示模式。`
}
