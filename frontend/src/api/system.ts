/**
 * 系统运行状态（顶栏状态灯）：
 * - 前端编译期 mock 标志（USE_MOCK）决定「演示模式」还是「真实模式」；
 * - 真实模式下探测后端 /health，区分「算法在线 / 算法离线」。
 * 状态每 30s 轮询一次，页面多组件共用同一份响应式状态。
 */
import { ref, watchEffect } from 'vue'
import { USE_MOCK } from './client'

export type RunStatusKind = 'mock' | 'online' | 'offline'

export interface RunStatus {
  kind: RunStatusKind
  /** 状态灯文案 */
  label: string
  /** 悬停提示（说明数据与算法来源） */
  tip: string
}

const POLL_MS = 30_000

/** 后端健康检查是否通过（mock 模式下恒为 false） */
const backendOnline = ref(false)
/** 已完成过至少一次探测（避免初始闪红灯） */
const probed = ref(false)

/** 模块级单例轮询定时器（多组件 import 也只起一个） */
let timer: ReturnType<typeof setInterval> | null = null

async function probe(): Promise<void> {
  if (USE_MOCK) {
    backendOnline.value = false
    probed.value = true
    return
  }
  try {
    const r = await fetch('/health', { cache: 'no-store' })
    backendOnline.value = r.ok
  } catch {
    backendOnline.value = false
  }
  probed.value = true
}

/** 启动轮询（幂等；在顶栏挂载时调用） */
export function startStatusPolling(): void {
  if (timer) return
  void probe()
  timer = setInterval(() => void probe(), POLL_MS)
}

/** 当前运行状态（响应式，供状态灯渲染） */
export const runStatus = ref<RunStatus>({ kind: 'mock', label: '演示模式', tip: '' })

// 状态推导：probed 前真实模式显示「检测中」，避免误报离线
watchEffect(() => {
  if (USE_MOCK) {
    runStatus.value = {
      kind: 'mock',
      label: '演示模式',
      tip: '当前为前端演示模式：数据与计算均在浏览器内模拟，未接入后台算法。将 .env 中 VITE_USE_MOCK 设为 false 并启动后端即可切换。',
    }
  } else if (!probed.value) {
    runStatus.value = { kind: 'offline', label: '检测中…', tip: '正在探测后台算法服务状态' }
  } else if (backendOnline.value) {
    runStatus.value = {
      kind: 'online',
      label: '算法后台·在线',
      tip: '已接入真实选址算法：AI 解析、熵权-TopSIS 计算与模型指标均由后端实时计算返回。',
    }
  } else {
    runStatus.value = {
      kind: 'offline',
      label: '算法后台·离线',
      tip: '前端为真实模式，但后端服务（127.0.0.1:8000）未响应。请启动后端：backend 目录下 .venv\\Scripts\\python -m uvicorn main:app --port 8000',
    }
  }
})
