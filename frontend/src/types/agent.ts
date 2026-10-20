/**
 * LangGraph 选址智能体与 PostGIS 空间数据类型定义
 */
export interface PharmaAgentRequest {
  query: string
  hq_min_ha: number
  hq_max_ha: number
  factory_min_ha: number
  factory_max_ha: number
  sanitary_buffer_m: number
}

export interface PharmaAgentCandidate {
  id: number | string
  role: 'hq' | 'factory' | 'unified'
  area_ha: number
  centroid_lon: number
  centroid_lat: number
  scores: {
    total: number
    urban_planning: number
    transport: number
    industry: number
    infrastructure: number
    cost: number
  }
  geometry: any
  features?: Record<string, number>
  advantages: string[]
  disadvantages: string[]
}

export interface SchemeComparison {
  unified_scheme: {
    parcel_id: string
    area_ha: number
    scores: Record<string, number>
    advantages: string[]
    disadvantages: string[]
    suitable_scenario: string
  }
  dual_site_scheme: {
    hq_parcel_id: string
    hq_area_ha: number
    factory_parcel_id: string
    factory_area_ha: number
    commute_dist_km: number
    commute_car_min: number
    hq_scores: Record<string, number>
    factory_scores: Record<string, number>
    advantages: string[]
    disadvantages: string[]
    suitable_scenario: string
  }
  overall_recommendation: string
}

export interface PharmaAgentResponse {
  status: string
  project_profile: Record<string, any>
  scheme_comparison: SchemeComparison
  top_candidates: {
    hq: PharmaAgentCandidate[]
    factory: PharmaAgentCandidate[]
    unified: PharmaAgentCandidate[]
  }
  opinion_report: string
  logs: string[]
}

export interface PostgisHealth {
  status: string
  host?: string
  database?: string
  total_tuban?: number
}
