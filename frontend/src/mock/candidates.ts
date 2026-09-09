/**
 * 候选地块 + 适宜度网格 mock 生成器。
 * 以临桂区 [110.2, 25.24] 为基准随机生成，几何为 WGS84 近似 CGCS2000（EPSG:4490），演示用。
 */
import type { Feature, FeatureCollection, Polygon } from 'geojson'
import type { ScenarioDetail } from '../types/scenario'
import type { CandidateParcel, SelectionRequest, SelectionResponse as SR } from '../types/selection'
import { sleep } from './delay'

const CENTER: [number, number] = [110.2, 25.24]

/** 0.0001° 纬度 ≈ 11.1m；用于把米换算为度数 */
const M2DEG_LAT = 1 / 111100
/** 0.0001° 经度在临桂区纬度 ≈ 11.1 × cos(25.24°) ≈ 10.05m */
const M2DEG_LNG = 1 / 100500

function rand(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

/** 生成近矩形随机多边形（4-6 顶点），边长 spanMeters 米 */
function randomPolygon(center: [number, number], spanMeters: number): Polygon {
  const halfLng = (spanMeters / 2) * M2DEG_LNG
  const halfLat = (spanMeters / 2) * M2DEG_LAT
  const jitter = () => rand(-0.15, 0.15)
  const ring: number[][] = [
    [center[0] - halfLng, center[1] - halfLat],
    [center[0] + halfLng * rand(0.8, 1.1), center[1] - halfLat * rand(0.8, 1.1)],
    [center[0] + halfLng * rand(0.9, 1.15), center[1] + halfLat * rand(0.85, 1.05)],
    [center[0] + halfLng * jitter() * 0.4, center[1] + halfLat * rand(0.95, 1.2)],
    [center[0] - halfLng * rand(0.85, 1.1), center[1] + halfLat * rand(0.9, 1.1)],
    [center[0] - halfLng * rand(0.9, 1.05), center[1] - halfLat * rand(0.9, 1.0)],
  ]
  ring.push([...ring[0]]) // 闭合
  return { type: 'Polygon', coordinates: [ring] }
}

/** shoelace 面积（平方米，纬度尺度近似） */
function polygonAreaM2(poly: Polygon): number {
  const ring = poly.coordinates[0]
  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i]
    const [x2, y2] = ring[i + 1]
    sum += x1 * y2 - x2 * y1
  }
  return Math.abs(sum) * 0.5 * 111100 * 111100 * Math.cos((CENTER[1] * Math.PI) / 180)
}

/** 按因子方向生成合理 mock 值（已标准化到 0-100 语义） */
function factorMockValue(direction: 1 | -1 | 2): number {
  if (direction === 1) return rand(62, 96)
  if (direction === -1) return rand(55, 92)
  return rand(50, 85) // 区间型
}

const NOTES = [
  '全部硬约束通过，区位条件良好',
  '全部硬约束通过，周边配套较完善',
  '全部硬约束通过，地形平缓利于开发',
  '全部硬约束通过，市政设施接入便利',
  '全部硬约束通过，连片程度高',
  '硬约束通过，邻避因素较少',
]

/** 生成 top_n 个候选地块 */
function generateCandidates(scenario: ScenarioDetail, topN: number): CandidateParcel[] {
  const list: CandidateParcel[] = []
  for (let i = 0; i < topN; i++) {
    // 在中心 ±0.06° 内散布，避免重叠
    const cx = CENTER[0] + rand(-0.06, 0.06)
    const cy = CENTER[1] + rand(-0.05, 0.05)
    const span = rand(220, 520) // 米
    const geometry = randomPolygon([cx, cy], span)
    const factors: Record<string, number> = {}
    for (const f of scenario.factors) {
      factors[f.id] = Math.round(factorMockValue(f.direction) * 10) / 10
    }
    const scoreBase = 92 - i * rand(3, 6)
    list.push({
      rank: i + 1,
      score: Math.round(Math.max(55, scoreBase) * 10) / 10,
      area_ha: Math.round((polygonAreaM2(geometry) / 10000) * 100) / 100,
      geometry,
      factors,
      notes: NOTES[i % NOTES.length],
      cluster: i % 3,
    })
  }
  return list
}

/** 生成适宜度网格（GeoJSON FeatureCollection，weight 0-100，中心高边缘低） */
export function generateHeatGrid(aoi?: Polygon): FeatureCollection<Polygon, { weight: number }> {
  // AOI 中心或默认中心
  let cx = CENTER[0]
  let cy = CENTER[1]
  let halfLng = 0.07
  let halfLat = 0.06
  if (aoi) {
    const ring = aoi.coordinates[0]
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    for (const [x, y] of ring) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x)
      minY = Math.min(minY, y); maxY = Math.max(maxY, y)
    }
    cx = (minX + maxX) / 2
    cy = (minY + maxY) / 2
    halfLng = (maxX - minX) / 2
    halfLat = (maxY - minY) / 2
  }
  const features: Feature<Polygon, { weight: number }>[] = []
  const cols = 16
  const rows = 14
  const cellLng = (halfLng * 2) / cols
  const cellLat = (halfLat * 2) / rows
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x0 = cx - halfLng + c * cellLng
      const y0 = cy - halfLat + r * cellLat
      // 高斯场：越靠中心权重越高
      const dx = (x0 + cellLng / 2 - cx) / halfLng
      const dy = (y0 + cellLat / 2 - cy) / halfLat
      const dist2 = dx * dx + dy * dy
      const base = Math.exp(-dist2 * 2.2) * 88
      const weight = Math.round(Math.min(100, Math.max(4, base + rand(-8, 10))))
      features.push({
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [x0, y0],
            [x0 + cellLng, y0],
            [x0 + cellLng, y0 + cellLat],
            [x0, y0 + cellLat],
            [x0, y0],
          ]],
        },
        properties: { weight },
      })
    }
  }
  return { type: 'FeatureCollection', features }
}

/** mock：POST /api/selection/run */
export async function mockRunSelection(
  req: SelectionRequest,
  scenario: ScenarioDetail,
  onProgress?: (p: { percent: number; log: string }) => void
): Promise<SR> {
  await sleep(250)
  const totalCells = Math.round(rand(18000, 32000))
  const availableCells = Math.round(totalCells * rand(0.18, 0.32))
  const candidates = generateCandidates(scenario, req.top_n)
  const algoLabel = req.algorithm === 'topsis' ? 'TOPSIS' : req.algorithm === 'regression' ? '多元回归' : req.algorithm === 'kmeans' ? 'K-Means 聚类' : '组合赋权'
  return {
    task_id: `task-${Date.now().toString(36)}`,
    scenario_id: req.scenario_id,
    grid_size_m: req.grid_size_m,
    total_cells: totalCells,
    available_cells: availableCells,
    candidates,
    message: `（样例数据）${algoLabel}计算完成：研究区网格化后共 ${totalCells} 个单元，硬约束过滤后剩 ${availableCells} 个可利用单元，输出 Top-${req.top_n} 候选地块。`,
  }
}
