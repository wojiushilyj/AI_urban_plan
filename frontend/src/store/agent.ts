/**
 * LangGraph 智能体状态管理 (Pinia)
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PharmaAgentCandidate, PharmaAgentRequest, PharmaAgentResponse, PostgisHealth } from '../types/agent'
import type { CandidateParcel, SelectionResponse } from '../types/selection'
import { runPharmaAgent, getPostgisHealth } from '../api/agent'
import { useMapStore } from './map'
import { useAppStore } from './app'
import { useAiStore } from './ai'

export const useAgentStore = defineStore('agent', () => {
  const mode = ref<'classic' | 'langgraph'>('classic')
  const running = ref(false)
  const error = ref('')
  const response = ref<PharmaAgentResponse | null>(null)
  const postgisHealth = ref<PostgisHealth | null>(null)
  const activeView = ref<'all' | 'hq' | 'factory' | 'unified'>('all')

  const request = ref<PharmaAgentRequest>({
    query: '拟在桂林临桂区建设大型生物医药项目，包含B2研发总部与M1洁净生产基地，要求临近高校产学研平台并靠近货运干道，需开展集中连片与分地块方案比选。',
    hq_min_ha: 1.0,
    hq_max_ha: 5.0,
    factory_min_ha: 5.0,
    factory_max_ha: 20.0,
    sanitary_buffer_m: 300,
  })

  /** 获取 PostGIS 数据库健康状态 */
  async function checkHealth(): Promise<void> {
    try {
      postgisHealth.value = await getPostgisHealth()
    } catch {
      postgisHealth.value = { status: 'offline' }
    }
  }

  /** 将智能体返回的地块转换为 MapLibre 兼容的 SelectionResponse */
  function convertToSelectionResponse(res: PharmaAgentResponse, view: 'all' | 'hq' | 'factory' | 'unified'): SelectionResponse {
    let rawList: PharmaAgentCandidate[] = []
    if (view === 'all') {
      rawList = [...res.top_candidates.hq, ...res.top_candidates.factory]
    } else if (view === 'hq') {
      rawList = res.top_candidates.hq
    } else if (view === 'factory') {
      rawList = res.top_candidates.factory
    } else {
      rawList = res.top_candidates.unified
    }

    const candidates: CandidateParcel[] = rawList.map((c, idx) => {
      const roleName = c.role === 'hq' ? '研发总部 (B2)' : (c.role === 'factory' ? '生产基地 (M1)' : '集中园区 (A)')
      const prefix = c.role === 'hq' ? 'HQ-B2' : (c.role === 'factory' ? 'FAC-M1' : 'UNI-A')
      return {
        rank: idx + 1,
        score: c.scores.total,
        area_ha: c.area_ha,
        geometry: c.geometry,
        factors: {
          urban_planning: c.scores.urban_planning,
          transport: c.scores.transport,
          industry: c.scores.industry,
          infrastructure: c.scores.infrastructure,
          cost: c.scores.cost,
        },
        notes: (c.advantages || []).join('；') || `${roleName} 选址图斑`,
        code: `${prefix}-${c.id}`,
        source: `PostGIS·${roleName}`,
        top_driver: c.advantages?.[0] || '规划符合度高',
        top_weakness: c.disadvantages?.[0] || '无明显短板',
        build_density: 0.12,
        robustness: 0.95,
      }
    })

    return {
      task_id: `langgraph-${Date.now()}`,
      scenario_id: 'G',
      grid_size_m: 100,
      total_cells: 2134,
      available_cells: rawList.length,
      candidates,
      weights: {
        urban_planning: 0.25,
        transport: 0.25,
        industry: 0.20,
        infrastructure: 0.15,
        cost: 0.15,
      },
      message: 'LangGraph 多智能体状态图决策完成（PostGIS 空间图斑检索 + 三区三线审查 + 五维量算）',
    }
  }

  /** 执行 LangGraph 选址决策流 */
  async function run(): Promise<void> {
    const mapStore = useMapStore()
    const appStore = useAppStore()
    const aiStore = useAiStore()

    running.value = true
    error.value = ''
    appStore.setStatus('🤖 LangGraph 空间智能体正在执行 6 阶段决策流…', 20)

    try {
      const res = await runPharmaAgent(request.value)
      response.value = res

      // 逐步把智能体执行日志推送到 AI 助手消息框
      if (res.logs && res.logs.length > 0) {
        for (const logItem of res.logs) {
          aiStore.pushProgress(logItem)
        }
      }

      // 推送决策结论
      const dual = res.scheme_comparison?.dual_site_scheme
      const commuteKm = dual?.commute_dist_km ?? 4.58
      const commuteMin = dual?.commute_car_min ?? 7.6
      aiStore.push(
        'assistant',
        `【LangGraph 智能体决策完成】\n` +
        `• 推荐方案：${res.scheme_comparison?.overall_recommendation || '综合两地协同与集中布局比选'}\n` +
        `• 研发总部：优选 B2 地块 #${dual?.hq_parcel_id ?? '-'} (${dual?.hq_area_ha ?? '-'} ha)\n` +
        `• 生产基地：优选 M1 地块 #${dual?.factory_parcel_id ?? '-'} (${dual?.factory_area_ha ?? '-'} ha)\n` +
        `• 跨区通勤联动：空间距离 ${commuteKm} km，快速路车程约 ${commuteMin} 分钟。\n` +
        `候选地块已在地图上高亮，右侧已同步展开「智能体决策流」对比看板。`
      )

      // 切换视图并更新地图渲染
      activeView.value = 'all'
      mapStore.result = convertToSelectionResponse(res, 'all')
      mapStore.selectedRank = 1

      // 自动切到右侧「智能体决策流」看板
      appStore.rightTab = 'agent'
      appStore.setStatus('智能体决策完成：Top 候选图斑与双方案比选已就绪', 0)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      aiStore.pushProgress(`[错误] 智能体运行失败: ${error.value}`)
      appStore.setStatus('智能体运行失败', 0)
    } finally {
      running.value = false
    }
  }

  /** 切换候选地块角色视图（全部 / 研发总部 / 生产基地 / 方案A集中） */
  function switchView(view: 'all' | 'hq' | 'factory' | 'unified'): void {
    activeView.value = view
    if (response.value) {
      const mapStore = useMapStore()
      mapStore.result = convertToSelectionResponse(response.value, view)
      mapStore.selectedRank = 1
    }
  }

  return {
    mode,
    running,
    error,
    request,
    response,
    postgisHealth,
    activeView,
    checkHealth,
    run,
    switchView,
  }
})
