/**
 * GeoJSON 几何工具（零依赖）。
 *
 * 尺度假设：面向桂林临桂区这类城市尺度，采用「局部等距平面近似」——
 * 纬度 1° ≈ 111132 m，经度 1° ≈ 111320·cos(φ) m。误差在百米级距离上可忽略，
 * 不适用于跨省、全球尺度的精确量算。
 */
import type { Feature, Geometry, Point, Polygon, Position } from 'geojson'

export type XY = [number, number]
export type BBox = [number, number, number, number]

/** 纬度方向 1° 的米数（WGS84 子午线弧长均值） */
export const M_PER_DEG_LAT = 111132

/** 经度方向 1° 的米数（随纬度收缩） */
export function mPerDegLng(lat: number): number {
  return 111320 * Math.cos((lat * Math.PI) / 180)
}

/** 保证环闭合（首尾点一致） */
function closedRing(ring: Position[]): Position[] {
  if (ring.length < 3) return ring
  const a = ring[0]
  const b = ring[ring.length - 1]
  return a[0] === b[0] && a[1] === b[1] ? ring : [...ring, a]
}

/** 环的面积（平方米，绝对值） */
export function ringAreaM2(ring: Position[]): number {
  const r = closedRing(ring)
  const lat = r[0][1]
  const kx = mPerDegLng(lat)
  let sum = 0
  for (let i = 0; i < r.length - 1; i++) {
    const x1 = r[i][0] * kx
    const y1 = r[i][1] * M_PER_DEG_LAT
    const x2 = r[i + 1][0] * kx
    const y2 = r[i + 1][1] * M_PER_DEG_LAT
    sum += x1 * y2 - x2 * y1
  }
  return Math.abs(sum) * 0.5
}

/** 环的周长（米） */
export function ringPerimeterM(ring: Position[]): number {
  const r = closedRing(ring)
  const lat = r[0][1]
  const kx = mPerDegLng(lat)
  let d = 0
  for (let i = 0; i < r.length - 1; i++) {
    const dx = (r[i + 1][0] - r[i][0]) * kx
    const dy = (r[i + 1][1] - r[i][1]) * M_PER_DEG_LAT
    d += Math.hypot(dx, dy)
  }
  return d
}

/** 多边形近似面积（平方米，外环减内环） */
export function polygonAreaM2(poly: Polygon): number {
  const rings = poly.coordinates
  let area = ringAreaM2(rings[0])
  for (let i = 1; i < rings.length; i++) area -= ringAreaM2(rings[i])
  return Math.max(0, area)
}

/** 多边形周长（米，含内环） */
export function polygonPerimeterM(poly: Polygon): number {
  return poly.coordinates.reduce((sum, r) => sum + ringPerimeterM(r), 0)
}

/** 面积加权质心（退化时回退到首顶点） */
export function centroid(poly: Polygon): XY {
  const r = closedRing(poly.coordinates[0])
  const kx = mPerDegLng(r[0][1])
  let a = 0
  let cx = 0
  let cy = 0
  for (let i = 0; i < r.length - 1; i++) {
    const x1 = r[i][0] * kx
    const y1 = r[i][1] * M_PER_DEG_LAT
    const x2 = r[i + 1][0] * kx
    const y2 = r[i + 1][1] * M_PER_DEG_LAT
    const cross = x1 * y2 - x2 * y1
    a += cross
    cx += (x1 + x2) * cross
    cy += (y1 + y2) * cross
  }
  if (!a) return [r[0][0], r[0][1]]
  const area = a * 0.5
  return [cx / (6 * area) / kx, cy / (6 * area) / M_PER_DEG_LAT]
}

/** 规整度 Polsby-Popper：4πA/P²，1 = 正圆，越接近 1 越规整 */
export function polsbyPopper(poly: Polygon): number {
  const area = polygonAreaM2(poly)
  const perimeter = polygonPerimeterM(poly)
  if (!perimeter) return 0
  return Math.min(1, (4 * Math.PI * area) / (perimeter * perimeter))
}

/** 几何包围盒 [minX, minY, maxX, maxY] */
export function bboxOfGeometry(g: Geometry): BBox {
  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  const visit = (p: Position): void => {
    if (p[0] < minX) minX = p[0]
    if (p[0] > maxX) maxX = p[0]
    if (p[1] < minY) minY = p[1]
    if (p[1] > maxY) maxY = p[1]
  }
  const walk = (node: Position | Position[] | Position[][] | Position[][][]): void => {
    if (typeof node[0] === 'number') visit(node as Position)
    else (node as unknown[]).forEach((n) => walk(n as never))
  }
  walk(g.type === 'Point' ? g.coordinates : (g as Polygon).coordinates as never)
  return [minX, minY, maxX, maxY]
}

/** 包围盒相交（含相切） */
export function bboxIntersects(a: BBox, b: BBox): boolean {
  return a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1]
}

/** 射线法判断点是否在外环内（不含内环） */
export function pointInRing(pt: XY, ring: Position[]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0]
    const yi = ring[i][1]
    const xj = ring[j][0]
    const yj = ring[j][1]
    const hit = yi > pt[1] !== yj > pt[1] && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi
    if (hit) inside = !inside
  }
  return inside
}

/** 点是否落在多边形内（考虑内环挖空） */
export function pointInPolygon(pt: XY, poly: Polygon): boolean {
  if (!pointInRing(pt, poly.coordinates[0])) return false
  for (let i = 1; i < poly.coordinates.length; i++) {
    if (pointInRing(pt, poly.coordinates[i])) return false
  }
  return true
}

/** 点到线段的最短距离（米） */
function pointToSegmentM(pt: XY, a: Position, b: Position): number {
  const ky = M_PER_DEG_LAT
  const kx = mPerDegLng(pt[1])
  const px = pt[0] * kx
  const py = pt[1] * ky
  const ax = a[0] * kx
  const ay = a[1] * ky
  const bx = b[0] * kx
  const by = b[1] * ky
  const dx = bx - ax
  const dy = by - ay
  const len2 = dx * dx + dy * dy
  if (!len2) return Math.hypot(px - ax, py - ay)
  let t = ((px - ax) * dx + (py - ay) * dy) / len2
  t = Math.max(0, Math.min(1, t))
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
}

/** 点到多边形边界的最短距离（米），点在面内返回 0 */
export function pointToPolygonM(pt: XY, poly: Polygon): number {
  if (pointInPolygon(pt, poly)) return 0
  let best = Infinity
  for (const ring of poly.coordinates) {
    const r = closedRing(ring)
    for (let i = 0; i < r.length - 1; i++) {
      const d = pointToSegmentM(pt, r[i], r[i + 1])
      if (d < best) best = d
    }
  }
  return best
}

/** 点到任意几何的距离（米）：点要素取点距，面要素取边界距（内部为 0） */
export function pointToGeometryM(pt: XY, g: Geometry): number {
  switch (g.type) {
    case 'Point':
      return Math.hypot((pt[0] - g.coordinates[0]) * mPerDegLng(pt[1]), (pt[1] - g.coordinates[1]) * M_PER_DEG_LAT)
    case 'MultiPoint':
      return Math.min(...g.coordinates.map((p) => pointToGeometryM(pt, { type: 'Point', coordinates: p } as Point)))
    case 'Polygon':
      return pointToPolygonM(pt, g)
    case 'MultiPolygon':
      return Math.min(...g.coordinates.map((c) => pointToPolygonM(pt, { type: 'Polygon', coordinates: c })))
    default:
      return Infinity
  }
}

/** 几何的质心（面取面积加权质心，点取自身，多点取平均） */
export function geometryCentroid(g: Geometry): XY {
  switch (g.type) {
    case 'Point':
      return [g.coordinates[0], g.coordinates[1]]
    case 'MultiPoint': {
      const n = g.coordinates.length || 1
      return [
        g.coordinates.reduce((a, p) => a + p[0], 0) / n,
        g.coordinates.reduce((a, p) => a + p[1], 0) / n,
      ]
    }
    case 'Polygon':
      return centroid(g)
    case 'MultiPolygon': {
      const parts = g.coordinates.map((c) => ({ poly: { type: 'Polygon', coordinates: c } as Polygon }))
      let area = 0
      let sx = 0
      let sy = 0
      for (const { poly } of parts) {
        const a = polygonAreaM2(poly)
        const c = centroid(poly)
        area += a
        sx += c[0] * a
        sy += c[1] * a
      }
      if (!area) return centroid(parts[0].poly)
      return [sx / area, sy / area]
    }
    default:
      return [0, 0]
  }
}

/** 几何的代表性内点（用于空间关系统计，保证落在要素内部或就近） */
export function interiorPoint(g: Geometry): XY {
  if (g.type === 'Polygon') {
    const c = centroid(g)
    if (pointInPolygon(c, g)) return c
    const b = bboxOfGeometry(g)
    const bc: XY = [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
    if (pointInPolygon(bc, g)) return bc
    return [g.coordinates[0][0][0], g.coordinates[0][0][1]]
  }
  return geometryCentroid(g)
}

/** 要素的代表性内点 */
export function featurePoint(f: Feature): XY {
  return interiorPoint(f.geometry)
}

/** 面积换算：平方米 → 公顷（保留 2 位） */
export function m2ToHa(m2: number): number {
  return Math.round((m2 / 10000) * 100) / 100
}
