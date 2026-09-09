/**
 * 场景模板 mock：按国民经济行业门类划分（共 10 大门类）。
 * 评价维度统一为 5 项（城市规划/交通物流/产业协同/基础配套/建造成本），
 * 评分与权重均按此 5 项进行；权重由「选址偏好」三档驱动（见 store/config.ts）。
 * 与 backend/app/services/scenarios.py 保持对齐。
 */
import type { ScenarioDetail, ScenarioSummary } from '../types/scenario'

/** 统一评价维度（评分与权重均按此 5 项） */
const FACTORS: ScenarioDetail['factors'] = [
  { id: 'urban_planning', name: '城市规划', direction: 1, unit: '0-1' },
  { id: 'transport', name: '交通物流', direction: 1, unit: '0-1' },
  { id: 'industry', name: '产业协同', direction: 1, unit: '0-1' },
  { id: 'infrastructure', name: '基础配套', direction: 1, unit: '0-1' },
  { id: 'cost', name: '建造成本', direction: -1, unit: '0-1' },
]

const WEIGHTS_AHP: ScenarioDetail['weights_ahp'] = {
  urban_planning: 0.2, transport: 0.2, industry: 0.2,
  infrastructure: 0.2, cost: 0.2,
}

export const SCENARIOS: Record<string, ScenarioDetail> = {
  B: {
    id: 'B',
    name: '采矿业',
    category: '采矿业',
    description: '面向矿产资源开发（砂石土矿、金属/非金属矿）的矿业权区块选址，平衡资源禀赋与生态约束。',
    constraints: [
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'udb', name: '城镇开发边界', buffer_m: 0, required: true },
      { id: 'water_source', name: '饮用水源保护区', buffer_m: 0, required: true },
      { id: 'residential', name: '居民点安全距离', buffer_m: 300, required: true },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  C1: {
    id: 'C1',
    name: '制造业（消费品）',
    category: '制造业',
    description: '食品、纺织服装、家具、家电、文体用品等面向终端消费的轻工制造，劳动力密集、贴近市场。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'river_range', name: '河湖管理范围', buffer_m: 30, required: true },
      { id: 'road_protect', name: '高速/铁路安全保护距离', buffer_m: 100, required: false },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  C2: {
    id: 'C2',
    name: '制造业（原材料与中间品）',
    category: '制造业',
    description: '钢铁、有色、化工、建材、造纸等重化工与基础材料制造，环境敏感、需远离居民点并具备防护距离。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'residential', name: '居民点安全距离', buffer_m: 500, required: true },
      { id: 'water_source', name: '饮用水源保护区', buffer_m: 0, required: true },
      { id: 'river_range', name: '河湖管理范围', buffer_m: 50, required: true },
      { id: 'pollution_source', name: '噪声/污染源防护', buffer_m: 200, required: false },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  C3: {
    id: 'C3',
    name: '制造业（装备设备）',
    category: '制造业',
    description: '机械、汽车、电子设备、船舶、航空航天等装备制造，用地规模大、物流与产业链配套要求高。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'river_range', name: '河湖管理范围', buffer_m: 30, required: true },
      { id: 'road_protect', name: '高速/铁路安全保护距离', buffer_m: 100, required: false },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  D: {
    id: 'D',
    name: '电力、热力、燃气及水生产和供应业',
    category: '能源与公用事业',
    description: '电厂、变电站、供热/燃气设施、水厂及污水厂等公用设施，安全防护距离大、邻避效应强。',
    constraints: [
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'residential', name: '居民点安全距离', buffer_m: 500, required: true },
      { id: 'water_source', name: '饮用水源保护区', buffer_m: 0, required: true },
      { id: 'flood_area', name: '行洪区', buffer_m: 0, required: true },
      { id: 'airport_clear', name: '机场净空/限高区', buffer_m: 0, required: true },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  E: {
    id: 'E',
    name: '建筑业',
    category: '建筑业',
    description: '施工企业基地、混凝土搅拌站、预制构件厂、机械停放场等，交通便利、邻近建设热点。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'residential', name: '居民点安全距离（噪声扬尘）', buffer_m: 300, required: true },
      { id: 'pollution_source', name: '噪声/扬尘敏感区', buffer_m: 200, required: true },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  G: {
    id: 'G',
    name: '交通运输、仓储和邮政业',
    category: '交通与物流',
    description: '物流园区、仓储中心、货运枢纽、快递分拨、邮政设施，紧邻高速/铁路/港口等交通节点。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'river_range', name: '河湖管理范围', buffer_m: 30, required: true },
      { id: 'road_protect', name: '高速/铁路安全保护距离', buffer_m: 100, required: false },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  I: {
    id: 'I',
    name: '信息传输、软件和信息技术服务业',
    category: '信息技术服务',
    description: '数据中心、软件园、通信机房、云计算基地等，电力保障、网络基础设施与人才聚集为核心。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'geohazard', name: '地质灾害高易发区', buffer_m: 100, required: true },
      { id: 'flood_area', name: '行洪区', buffer_m: 0, required: true },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  M: {
    id: 'M',
    name: '科学研究和技术服务业',
    category: '科技服务',
    description: '科研院所、实验室、检验检测、技术研发机构，环境安静、人才聚集、产学研协同。',
    constraints: [
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'pollution_source', name: '噪声/污染源', buffer_m: 200, required: true },
      { id: 'geohazard', name: '地质灾害高易发区', buffer_m: 100, required: true },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
  N: {
    id: 'N',
    name: '水利、环境和公共设施管理业',
    category: '环境与公共设施',
    description: '污水处理、垃圾/固废处置、环卫、水利与园林绿化设施，邻避效应强、地质与安全防护要求高。',
    constraints: [
      { id: 'eco_redline', name: '生态保护红线', buffer_m: 0, required: true },
      { id: 'prime_farmland', name: '永久基本农田', buffer_m: 0, required: true },
      { id: 'water_source', name: '饮用水源保护区', buffer_m: 0, required: true },
      { id: 'residential', name: '居民点安全距离', buffer_m: 500, required: true },
      { id: 'flood_area', name: '行洪区', buffer_m: 0, required: true },
      { id: 'geohazard', name: '地质灾害高易发区', buffer_m: 100, required: true },
    ],
    factors: FACTORS,
    weights_ahp: WEIGHTS_AHP,
  },
}

export function mockListScenarios(): { items: ScenarioSummary[] } {
  return {
    items: Object.values(SCENARIOS).map(({ id, name, category, description }) => ({
      id, name, category, description,
    })),
  }
}

export function mockGetScenario(id: string): ScenarioDetail {
  const s = SCENARIOS[id]
  if (!s) throw new Error(`未找到场景 ${id}`)
  return s
}
