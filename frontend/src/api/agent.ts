/**
 * LangGraph 智能体与 PostGIS 空间数据 API 客户端
 */
import { post, get } from './client'
import type { PharmaAgentRequest, PharmaAgentResponse, PostgisHealth } from '../types/agent'

/** 启动 LangGraph 医药选址决策智能体 */
export async function runPharmaAgent(req: PharmaAgentRequest): Promise<PharmaAgentResponse> {
  return post<PharmaAgentResponse>('/api/agent/pharma/run', req)
}

/** 获取 PostGIS 空间数据库健康状态 */
export async function getPostgisHealth(): Promise<PostgisHealth> {
  return get<PostgisHealth>('/api/agent/pharma/postgis/health')
}
