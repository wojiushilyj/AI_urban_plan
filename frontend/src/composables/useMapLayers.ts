/**
 * 结果图层渲染（模块 5.3 / 5.2）：
 * - 适宜度热力图（网格质心点 heatmap，浅黄→橙→红）
 * - 候选地块矢量（fill 按 score 分级 + line 边界）
 * - AOI 边界
 * - 真实业务图层（从 /data/layers/*.geojson 懒加载渲染，见 renderGeoLayers）
 * 底图 style 切换后由调用方 reapplyAll 重挂全部图层。
 */
import type { Map as MlMap } from 'maplibre-gl'
import type { FeatureCollection, Polygon } from 'geojson'
import type { CandidateParcel, SelectionResponse } from '../types/selection'
import type { BusinessLayer } from '../store/map'

export interface LayerHooks {
  onParcelClick?: (parcel: CandidateParcel, lngLat: { lng: number; lat: number }) => void
}

/** 真实 GeoJSON 数据缓存（避免底图切换时重复请求，尤其是大图层） */
const geoCache = new Map<string, FeatureCollection>()

export function useMapLayers(getMap: () => MlMap | null, hooks: LayerHooks = {}) {
  function addSource(id: string, data: unknown): void {
    const m = getMap()
    if (!m) return
    if (!m.getSource(id)) m.addSource(id, { type: 'geojson', data: data as never })
    else (m.getSource(id) as maplibregl.GeoJSONSource).setData(data as never)
  }

  function removeLayers(ids: string[]): void {
    const m = getMap()
    if (!m) return
    for (const id of ids) if (m.getLayer(id)) m.removeLayer(id)
  }

  /** 候选地块矢量（模块 5.3） */
  function renderCandidates(result: SelectionResponse, selectedRank: number | null, visible: boolean): void {
    const m = getMap()
    if (!m) return
    const fc: FeatureCollection<Polygon, { rank: number; score: number; parcel: string }> = {
      type: 'FeatureCollection',
      features: result.candidates.map((c) => ({
        type: 'Feature',
        geometry: c.geometry,
        properties: { rank: c.rank, score: c.score, parcel: JSON.stringify(c) },
      })),
    }
    addSource('candidates-src', fc)
    removeLayers(['candidates-line', 'candidates-fill'])
    m.addLayer({
      id: 'candidates-fill',
      type: 'fill',
      source: 'candidates-src',
      layout: { visibility: visible ? 'visible' : 'none' },
      paint: {
        'fill-color': [
          'interpolate', ['linear'], ['get', 'score'],
          55, '#BFDBFE', 70, '#60A5FA', 85, '#3B82F6', 95, '#2563EB',
        ],
        // 选中地块更实
        'fill-opacity': ['case', ['==', ['get', 'rank'], selectedRank ?? -1], 0.7, 0.5],
      },
    })
    m.addLayer({
      id: 'candidates-line',
      type: 'line',
      source: 'candidates-src',
      layout: { visibility: visible ? 'visible' : 'none' },
      paint: {
        // 选中地块：红色加粗描边
        'line-color': ['case', ['==', ['get', 'rank'], selectedRank ?? -1], '#EF4444', '#2563EB'],
        'line-width': ['case', ['==', ['get', 'rank'], selectedRank ?? -1], 5, 1.5],
      },
    })
    if (hooks.onParcelClick) {
      m.off('click', 'candidates-fill', onFillClick)
      m.on('click', 'candidates-fill', onFillClick)
    }
  }

  function onFillClick(e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }): void {
    const raw = e.features?.[0]?.properties?.['parcel']
    if (!raw || !hooks.onParcelClick) return
    const parcel = JSON.parse(String(raw)) as CandidateParcel
    hooks.onParcelClick(parcel, e.lngLat)
  }

  /** AOI 边界（模块 5.4 框选结果回显） */
  function renderAoi(aoi: Polygon | null): void {
    const m = getMap()
    if (!m || !aoi) return
    addSource('aoi-src', { type: 'Feature', geometry: aoi, properties: {} })
    removeLayers(['aoi-fill', 'aoi-line'])
    m.addLayer({
      id: 'aoi-fill',
      type: 'fill',
      source: 'aoi-src',
      paint: { 'fill-color': '#3B82F6', 'fill-opacity': 0.06 },
    })
    m.addLayer({
      id: 'aoi-line',
      type: 'line',
      source: 'aoi-src',
      paint: { 'line-color': '#3B82F6', 'line-width': 2, 'line-dasharray': [3, 2] },
    })
  }

  /** 真实业务图层（模块 5.2）：从 /data/layers/*.geojson 懒加载，首次可见时才请求数据 */
  async function renderGeoLayers(defs: BusinessLayer[]): Promise<void> {
    const m = getMap()
    if (!m) return
    // 语义配色：耕地橙黄、红线红、水系蓝、绿地绿、产业橙紫、设施青、文保深红
    const styleMap: Record<string, { color: string; opacity: number; type: 'fill' | 'circle' }> = {
      'perm-farmland': { color: '#F59E0B', opacity: 0.35, type: 'fill' },
      'eco-redline': { color: '#EF4444', opacity: 0.3, type: 'fill' },
      'urban-boundary': { color: '#8B5CF6', opacity: 0.25, type: 'fill' },
      'yellow-line': { color: '#EAB308', opacity: 0.3, type: 'fill' },
      'blue-line': { color: '#3B82F6', opacity: 0.3, type: 'fill' },
      'green-line': { color: '#22C55E', opacity: 0.3, type: 'fill' },
      'industrial-land': { color: '#D97706', opacity: 0.35, type: 'fill' },
      'regulated-industrial': { color: '#EA580C', opacity: 0.35, type: 'fill' },
      'industrial-park': { color: '#7C3AED', opacity: 0.35, type: 'fill' },
      'prod-service-point': { color: '#06B6D4', opacity: 0.9, type: 'circle' },
      'prod-service-area': { color: '#0EA5E9', opacity: 0.4, type: 'fill' },
      'cultural-relic': { color: '#DC2626', opacity: 0.5, type: 'fill' },
    }

    for (const def of defs) {
      if (def.kind !== 'geojson' || !def.sourceUrl) continue
      const style = styleMap[def.id]
      if (!style) continue
      const srcId = `${def.id}-src`
      const layerId = `${def.id}-layer`

      // 懒加载：仅当图层首次可见时才请求数据（大图层如永久基本农田 7MB 按需加载）
      if (!m.getSource(srcId) && def.visible) {
        try {
          let data = geoCache.get(def.id)
          if (!data) {
            const resp = await fetch(def.sourceUrl)
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
            data = (await resp.json()) as FeatureCollection
            geoCache.set(def.id, data)
          }
          m.addSource(srcId, { type: 'geojson', data: data as never })
          if (style.type === 'circle') {
            m.addLayer({
              id: layerId,
              type: 'circle',
              source: srcId,
              layout: { visibility: 'visible' },
              paint: {
                'circle-radius': 6,
                'circle-color': style.color,
                'circle-opacity': style.opacity,
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 1.5,
              },
            })
          } else {
            m.addLayer({
              id: layerId,
              type: 'fill',
              source: srcId,
              layout: { visibility: 'visible' },
              paint: {
                'fill-color': style.color,
                'fill-opacity': style.opacity,
                'fill-outline-color': style.color,
              },
            })
          }
        } catch (e) {
          console.warn(`[图层] ${def.id} 加载失败：`, e)
          continue
        }
      }

      // 切换可见性
      if (m.getLayer(layerId)) {
        m.setLayoutProperty(layerId, 'visibility', def.visible ? 'visible' : 'none')
      }
    }
  }

  return { renderCandidates, renderAoi, renderGeoLayers, removeLayers }
}
