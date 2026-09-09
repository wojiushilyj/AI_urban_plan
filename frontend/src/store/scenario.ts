/** 场景状态：列表、当前场景（模块 1.1 场景切换） */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { ScenarioDetail, ScenarioSummary } from '../types/scenario'
import { getScenarioDetail, getScenarios } from '../api/scenario'

export const useScenarioStore = defineStore('scenario', () => {
  const list = ref<ScenarioSummary[]>([])
  const currentId = ref<string>('B')
  const detail = ref<ScenarioDetail | null>(null)
  const loading = ref(false)

  const current = computed(() =>
    list.value.find((s) => s.id === currentId.value) ?? null
  )

  async function fetchList(): Promise<void> {
    loading.value = true
    try {
      list.value = await getScenarios()
    } finally {
      loading.value = false
    }
  }

  async function switchScenario(id: string): Promise<ScenarioDetail> {
    currentId.value = id
    detail.value = await getScenarioDetail(id)
    return detail.value
  }

  return { list, currentId, detail, current, loading, fetchList, switchScenario }
})
