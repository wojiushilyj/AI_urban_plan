/** GeoJSON 工具 */
import type { Polygon } from 'geojson'

/** 计算多边形近似面积（平方米，纬度修正） */
export function polygonAreaM2(poly: Polygon): number {
  const ring = poly.coordinates[0]
  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    sum += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
  }
  const lat = ring.reduce((a, p) => a + p[1], 0) / ring.length
  return Math.abs(sum) * 0.5 * 111000 * 111000 * Math.cos((lat * Math.PI) / 180)
}

/** 质心 */
export function centroid(poly: Polygon): [number, number] {
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
