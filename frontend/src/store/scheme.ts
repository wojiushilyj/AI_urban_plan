/** 方案管理状态（模块 1.3）：新建、保存、加载、删除 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Polygon } from 'geojson'
import { deleteScheme, listSchemes, saveScheme, type Scheme } from '../api/scheme'
import { useConfigStore } from './config'
import { useMapStore } from './map'
import { useScenarioStore } from './scenario'

export const useSchemeStore = defineStore('scheme', () => {
  const list = ref<Scheme[]>([])
  const managerVisible = ref(false)

  function refresh(): void {
    list.value = listSchemes()
  }

  /** 保存当前配置为方案 */
  function saveCurrent(name: string): Scheme {
    const config = useConfigStore()
    const map = useMapStore()
    const scenario = useScenarioStore()
    const scheme = saveScheme({
      name,
      scenarioId: scenario.currentId,
      payload: {
        constraints: JSON.parse(JSON.stringify(config.constraints)),
        weights: { ...config.weights },
        algorithm: config.algorithm,
        alpha: config.alpha,
        topN: config.topN,
        gridSize: config.gridSize,
        aoi: map.aoi,
      },
    })
    refresh()
    return scheme
  }

  /** 加载方案：回写配置（场景切换由调用方处理） */
  function loadScheme(scheme: Scheme): void {
    const config = useConfigStore()
    const map = useMapStore()
    config.constraints = JSON.parse(JSON.stringify(scheme.payload.constraints))
    config.weights = { ...scheme.payload.weights }
    config.algorithm = scheme.payload.algorithm as typeof config.algorithm
    config.alpha = scheme.payload.alpha
    config.topN = scheme.payload.topN
    config.gridSize = scheme.payload.gridSize
    map.setAoi((scheme.payload.aoi as Polygon | null) ?? null)
  }

  function remove(id: string): void {
    deleteScheme(id)
    refresh()
  }

  return { list, managerVisible, refresh, saveCurrent, loadScheme, remove }
})
