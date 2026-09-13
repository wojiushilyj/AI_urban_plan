/**
 * 测量工具（模块 5.4）：距离（haversine）与面积（球面近似）。
 * 简化实现：点击加点 → 实时显示当前量测值 → 双击结束。
 */
import type { Map as MlMap } from 'maplibre-gl'

function haversine(a: [number, number], b: [number, number]): number {
  const R = 6371000
  const dLat = ((b[1] - a[1]) * Math.PI) / 180
  const dLng = ((b[0] - a[0]) * Math.PI) / 180
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a[1] * Math.PI) / 180) * Math.cos((b[1] * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}

function ringAreaM2(points: [number, number][]): number {
  let total = 0
  for (let i = 0; i < points.length - 1; i++) {
    const [x1, y1] = points[i]
    const [x2, y2] = points[i + 1]
    total += (((x2 - x1) * Math.PI) / 180) * (Math.sin((y2 * Math.PI) / 180) + Math.sin((y1 * Math.PI) / 180))
  }
  return (Math.abs(total) * 6371000 * 6371000) / 2
}

export interface MeasureResult {
  type: 'dist' | 'area'
  value: number
}

export function useMeasure(getMap: () => MlMap | null) {
  let active = false
  let mode: 'dist' | 'area' = 'dist'
  let points: [number, number][] = []
  let cleanup: (() => void) | null = null

  function start(m: 'dist' | 'area', onUpdate: (r: MeasureResult) => void, onDone: () => void): void {
    const map = getMap()
    if (!map || active) return
    active = true
    mode = m
    points = []
    map.getCanvas().style.cursor = 'crosshair'
    if (!map.getSource('measure-src')) {
      map.addSource('measure-src', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      map.addLayer({
        id: 'measure-line',
        type: 'line',
        source: 'measure-src',
        paint: { 'line-color': '#F59E0B', 'line-width': 2, 'line-dasharray': [3, 2] },
      })
    }

    const clickHandler = (e: maplibregl.MapMouseEvent) => {
      points.push([e.lngLat.lng, e.lngLat.lat])
      redraw()
      if (points.length >= 2) {
        onUpdate(
          mode === 'dist'
            ? { type: 'dist', value: totalDist() }
            : { type: 'area', value: ringAreaM2([...points, points[0]]) }
        )
      }
    }
    const dblclickHandler = () => {
      if (mode === 'area' && points.length >= 3) {
        onUpdate({ type: 'area', value: ringAreaM2([...points, points[0]]) })
      }
      stop()
      onDone()
    }

    map.on('click', clickHandler)
    map.on('dblclick', dblclickHandler)
    cleanup = () => {
      map.off('click', clickHandler)
      map.off('dblclick', dblclickHandler)
    }
  }

  function totalDist(): number {
    let d = 0
    for (let i = 1; i < points.length; i++) d += haversine(points[i - 1], points[i])
    return d
  }

  function redraw(): void {
    const map = getMap()
    const src = map?.getSource('measure-src') as maplibregl.GeoJSONSource | undefined
    if (!src || points.length < 2) return
    const coordinates = points.map((p) => [...p])
    if (mode === 'area') coordinates.push([...points[0]])
    src.setData({ type: 'Feature', geometry: { type: 'LineString', coordinates }, properties: {} } as never)
  }

  function stop(): void {
    const map = getMap()
    active = false
    points = []
    if (map) {
      map.getCanvas().style.cursor = ''
      cleanup?.()
      cleanup = null
      const src = map.getSource('measure-src') as maplibregl.GeoJSONSource | undefined
      src?.setData({ type: 'FeatureCollection', features: [] } as never)
    }
  }

  return { start, stop }
}
