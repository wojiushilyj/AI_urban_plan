/** AI 需求解析接口（模块 8.1） */
import type { ChatMessage, ParseResult } from '../types/ai'
import { post } from './client'
import { mockChat, mockParseRequirement } from '../mock/aiChat'

export async function parseRequirement(text: string): Promise<ParseResult> {
  return post<ParseResult>('/api/ai/parse', { text }, () => mockParseRequirement(text))
}

export async function sendChat(history: ChatMessage[], text: string): Promise<string> {
  return post<string>('/api/ai/chat', { history, text }, () => mockChat(history, text))
}
