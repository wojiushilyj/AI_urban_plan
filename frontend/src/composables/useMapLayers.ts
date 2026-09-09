/**
 * 结果图层渲染（模块 5.3 / 5.2）：
 * - 适宜度热力图（网格质心点 heatmap，浅黄→橙→红）
 * - 候选地块矢量（fill 按 score 分级 + line 边界）
 * - AOI 边界、业务示意图层（三区三线等，mock 随机几何）
 * 底图 style 切换后由调用方 reapplyAll 重挂全部图层。
 */
import type { Map as MlMap } from 'maplibre-gl'
import type { Feature, FeatureCollection, Point, Polygon } from 'geojson'
import type { CandidateParcel, SelectionResponse } from '../types/selection'
import type { BusinessLayer } from '../store/map'

export interface LayerHooks {
  onParcelClick?: (parcel: CandidateParcel, lngLat: { lng: number; lat: number }) => void
}

/** 质心 */
function centroid(poly: Polygon): [number, number] {
  const ring = poly.coordinates[0]
  let x = 0
  let y = 0
  for (let i = 0; i < ring.length - 1; i++) {
    x += ring[i][0]
    y += ring[i][1]
  }
  const n = ring.length - 1
  return [x / n, y / n]
}

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

  /** 热力图（模块 5.3）：网格质心点集 → heatmap */
  function renderHeat(grid: FeatureCollection<Polygon, { weight: number }>, visible: boolean): void {
    const m = getMap()
    if (!m) return
    const pointFeatures = grid.features.map(
      (f): Feature<Point, { weight: number }> => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: centroid(f.geometry) },
        properties: { weight: f.properties.weight },
      })
    )
    addSource('heat-src', { type: 'FeatureCollection', features: pointFeatures })
    removeLayers(['heat-layer'])
    m.addLayer({
      id: 'heat-layer',
      type: 'heatmap',
      source: 'heat-src',
      layout: { visibility: visible ? 'visible' : 'none' },
      paint: {
        'heatmap-weight': ['interpolate', ['linear'], ['get', 'weight'], 0, 0, 60, 0.5, 100, 1],
        'heatmap-intensity': 1.1,
        'heatmap-radius': 26,
        'heatmap-opacity': 0.75,
        'heatmap-color': [
          'interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(235, 244, 245, 0)',
          0.2, '#FDF3C7',
          0.4, '#F8D477',
          0.6, '#F5A623',
          0.8, '#E8743B',
          1, '#D64545',
        ],
      },
    })
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

  /** 业务示意图层（模块 5.2）：mock 半透明色块 */
  function renderBusinessLayers(defs: BusinessLayer[]): void {
    const m = getMap()
    if (!m) return
    const styleMap: Record<string, { color: string; opacity: number }> = {
      'ly-prime-farmland': { color: '#F59E0B', opacity: 0.15 },
      'ly-eco-redline': { color: '#EF4444', opacity: 0.15 },
      'ly-river': { color: '#60A5FA', opacity: 0.2 },
      'ly-road': { color: '#8A94A6', opacity: 0.35 },
      'ly-udb': { color: '#10B981', opacity: 0.12 },
    }
    for (const def of defs) {
      const style = styleMap[def.id]
      if (!style) continue
      const srcId = `${def.id}-src`
      const layerId = `${def.id}-layer`
      if (!m.getSource(srcId)) {
        m.addSource(srcId, { type: 'geojson', data: makeSampleGeometry(def.id) })
        if (def.id === 'ly-road') {
          m.addLayer({
            id: layerId,
            type: 'line',
            source: srcId,
            layout: { visibility: 'none' },
            paint: { 'line-color': style.color, 'line-width': 1.5, 'line-opacity': 0.8 },
          })
        } else {
          m.addLayer({
            id: layerId,
            type: 'fill',
            source: srcId,
            layout: { visibility: 'none' },
            paint: { 'fill-color': style.color, 'fill-opacity': style.opacity },
          })
        }
      }
      if (m.getLayer(layerId)) {
        m.setLayoutProperty(layerId, 'visibility', def.visible ? 'visible' : 'none')
      }
    }
  }

  return { renderHeat, renderCandidates, renderAoi, renderBusinessLayers, removeLayers }
}

/** 确定性伪随机：同 id 生成同样的示意几何 */
function makeSampleGeometry(id: string): FeatureCollection<Polygon, { name: string }> {
  let seed = 0
  for (const ch of id) seed = (seed * 31 + ch.charCodeAt(0)) % 997
  const rnd = () => {
    seed = (seed * 137 + 71) % 997
    return seed / 997
  }
  const features: Feature<Polygon, { name: string }>[] = []
  const n = id === 'ly-road' ? 8 : 4
  for (let i = 0; i < n; i++) {
    const cx = 108.0 + rnd() * 0.8
    const cy = 22.6 + rnd() * 0.6
    const s = 0.05 + rnd() * 0.08
    features.push({
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [[[cx, cy], [cx + s, cy + rnd() * 0.05], [cx + s * 0.8, cy + s], [cx - s * 0.2, cy + s * 0.7], [cx, cy]]],
      },
      properties: { name: id },
    })
  }
  return { type: 'FeatureCollection', features }
}
