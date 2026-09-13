/**
 * Mock 层统一注册。
 * 由 api/client.ts 按 VITE_USE_MOCK 开关调用，切换真实接口仅需修改 .env。
 */
export { mockListScenarios, mockGetScenario, SCENARIOS } from './scenarios'
export { mockRunSelection, preloadSelectionLayers } from './candidates'
export { mockParseRequirement, mockChat, TEMPLATES } from './aiChat'
export { mockGetAiModel } from './aiModel'
export { mockGenerateReport } from './report'
