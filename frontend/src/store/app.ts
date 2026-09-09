/** 全局应用状态：竞赛模式、帮助、底部状态栏（模块 1.2 / 1.4 / 9） */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { USE_MOCK } from '../api/client'

export const useAppStore = defineStore('app', () => {
  /** 竞赛演示模式：放大字号、显示一键演示 */
  const contestMode = ref(false)
  const helpVisible = ref(false)
  /** mock / real 连接状态 */
  const backendMode = ref<'mock' | 'real'>(USE_MOCK ? 'mock' : 'real')
  const backendAlive = ref(USE_MOCK)

  /** 底部状态栏消息 */
  const statusMessage = ref('就绪')
  const statusProgress = ref(0) // 0-100，>0 时显示进度条

  function setStatus(msg: string, progress = 0): void {
    statusMessage.value = msg
    statusProgress.value = progress
  }

  return {
    contestMode,
    helpVisible,
    backendMode,
    backendAlive,
    statusMessage,
    statusProgress,
    setStatus,
  }
})
