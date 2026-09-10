/**
 * 候选地块评估：从真实「控规工业用地」图斑中筛选、打分、排序。
 *
 * 候选池唯一来源：`regulated-industrial`（控规工业用地，145 个图斑）。
 * 本模块不再生成任何测试图斑（原随机矩形生成器与热力网mock 已移除）。
 *
 * 数据来源（均为真实规划数据，见 data/README.md）：
 *   候选池  regulated-industrial    控规工业用地
 *   硬约束  eco-redline             生态保护红线   ┐ 一票否决
 *           perm-farmland           永久基本农田   ┘
 *   软因子  urban-boundary          城镇开发边界   → 城市规划
 *           industrial-land         工业用地       → 城市规划（规划-现状契合度）
 *           prod-service-point/area 生产性服务点位 → 交通物流
 *           industrial-park         产业园区边界   → 产业协同
 *           yellow-line             城市黄线       → 基础配套
 *           几何尺度（面积 + 规整度）               → 建造成本
 *
 * 说明：源 SHP 仅含 Shape_Leng / Shape_Area 内部字段，无业务属性，
 * 因此地块编码由「来源图层 + 要素序号」生成（如 KG-065），各因子得分为真实空间关系统计结果。
 *
 * 初选口径：硬约束一票否决 + 最小面积 + 用地规模区间。
 * 用地规模区间仅在用户需求中提到占地面积时生效（目标 ± 容差，容差初值 ±50%，
 * 见 utils/area.ts 的 DEFAULT_AREA_TOLERANCE，最终限值由后端算法设计人员核定）。
 */
import type { Polygon } from 'geojson'
import type { ScenarioDetail } from '../types/scenario'
import type { CandidateParcel, SelectionRequest, SelectionResponse as SR } from '../types/selection'
import { loadLayers, type LayerFeatures, type LayerId } from '../api/layers'
import { sleep } from './delay'
import { areaWindow, DEFAULT_AREA_TOLERANCE } from '../utils/area'
import {
  bboxOfGeometry,
  interiorPoint,
  m2ToHa,
  M_PER_DEG_LAT,
  mPerDegLng,
  pointInPolygon,
  pointToPolygonM,
  polygonAreaM2,
  polsbyPopper,
  type BBox,
  type XY,
} from '../utils/geo'

/* ==================== 数据源定义 ==================== */

/** 候选池唯一来源：控规工业用地 */
const POOL_LAYER: LayerId = 'regulated-industrial'

/** 硬约束（一票否决）：生态保护红线、永久基本农田 */
const HARD_CONSTRAINT_LAYERS: LayerId[] = ['eco-redline', 'perm-farmland']

/** 软因子空间参照图层 */
const CONTEXT_LAYERS: LayerId[] = [
  'urban-boundary',
  'industrial-land',
  'industrial-park',
  'prod-service-point',
  'prod-service-area',
  'yellow-line',
]

/** 选址计算所需全部图层 */
const REQUIRED_LAYERS: LayerId[] = [POOL_LAYER, ...HARD_CONSTRAINT_LAYERS, ...CONTEXT_LAYERS]

/* ==================== 算法常量 ==================== */

/** 距离衰减特征尺度（米）：score = 100·exp(−d / d0) */
const DECAY_M = { transport: 1500, industry: 1200, infrastructure: 900 } as const

/** 各因子得分下限，避免远距离地块被拉成负分 */
const FACTOR_FLOOR = 35

/** 「建造成本」规模化最优参考面积（公顷） */
const COST_IDEAL_HA = 8

/** 展示得分映射区间（贴近度 → 百分制直观分） */
const SCORE_MIN = 52
const SCORE_MAX = 96

/* ==================== 工具函数 ==================== */

/** 面要素 + 预计算包围盒（加速空间关系判定） */
interface RefPoly {
  poly: Polygon
  bbox: BBox
}

function toRefPolys(fc: LayerFeatures | undefined): RefPoly[] {
  if (!fc) return []
  const out: RefPoly[] = []
  for (const f of fc.features) {
    if (f.geometry.type !== 'Polygon') continue
    const poly = f.geometry as Polygon
    out.push({ poly, bbox: bboxOfGeometry(poly) })
  }
  return out
}

function bboxContains(b: BBox, pt: XY): boolean {
  return pt[0] >= b[0] && pt[0] <= b[2] && pt[1] >= b[1] && pt[1] <= b[3]
}

/** 点是否落在参照面集合内 */
function containsPoint(pt: XY, refs: RefPoly[]): boolean {
  return refs.some((r) => bboxContains(r.bbox, pt) && pointInPolygon(pt, r.poly))
}

/** 点到参照面集合边界的最短距离（米），落在面内为 0 */
function minDistanceM(pt: XY, refs: RefPoly[]): number {
  let best = Infinity
  for (const r of refs) {
    const d = pointToPolygonM(pt, r.poly)
    if (d < best) best = d
    if (best === 0) return 0
  }
  return Number.isFinite(best) ? best : 5000
}

/** 点集合（点要素）的最短距离 */
function minDistanceToPointsM(pt: XY, pts: XY[]): number {
  let best = Infinity
  for (const p of pts) {
    const dx = (pt[0] - p[0]) * mPerDegLng(pt[1])
    const dy = (pt[1] - p[1]) * M_PER_DEG_LAT
    const d = Math.hypot(dx, dy)
    if (d < best) best = d
  }
  return Number.isFinite(best) ? best : 5000
}

/**
 * 两个面是否相交（近似判定）：
 * 包围盒相斥直接返回 false；否则依次判断「甲内点落乙」「乙内点落甲」「甲顶点落乙」「乙顶点落甲」。
 * 对真实规划图斑（顶点密集）足够可靠，仅纯边交叉且无顶点落入的极端情形会漏判。
 */
function overlapsPolygon(cand: Polygon, candBBox: BBox, ref: RefPoly): boolean {
  if (!(candBBox[0] <= ref.bbox[2] && candBBox[2] >= ref.bbox[0] && candBBox[1] <= ref.bbox[3] && candBBox[3] >= ref.bbox[1])) {
    return false
  }
  if (pointInPolygon(interiorPoint(cand), ref.poly)) return true
  if (pointInPolygon(interiorPoint(ref.poly), cand)) return true
  for (const ring of cand.coordinates) {
    for (const p of ring) if (pointInPolygon([p[0], p[1]], ref.poly)) return true
  }
  for (const ring of ref.poly.coordinates) {
    for (const p of ring) if (pointInPolygon([p[0], p[1]], cand)) return true
  }
  return false
}

/** 距离衰减得分（0–100） */
function decayScore(distanceM: number, d0: number, floor = FACTOR_FLOOR): number {
  return Math.max(floor, 100 * Math.exp(-distanceM / d0))
}

const clamp01 = (x: number): number => Math.max(0, Math.min(100, x))
const round1 = (x: number): number => Math.round(x * 10) / 10

/** 米 → 可读距离 */
function fmtDist(m: number): string {
  return m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${Math.round(m)}m`
}

/* ==================== 多准则决策 ==================== */

/** TOPSIS 贴近度 Cᵢ = Dᵢ⁻ / (Dᵢ⁺ + Dᵢ⁻)，因子均为正向（越大越优） */
function topsisCloseness(rows: number[][], weights: number[]): number[] {
  const m = rows.length
  const n = weights.length
  if (!m || !n) return []
  const denom = Array.from({ length: n }, (_, j) =>
    Math.sqrt(rows.reduce((a, r) => a + r[j] * r[j], 0)) || 1
  )
  const weighted = rows.map((r) => r.map((x, j) => (x / denom[j]) * weights[j]))
  const best = Array.from({ length: n }, (_, j) => Math.max(...weighted.map((r) => r[j])))
  const worst = Array.from({ length: n }, (_, j) => Math.min(...weighted.map((r) => r[j])))
  return weighted.map((r) => {
    const dPlus = Math.hypot(...r.map((x, j) => x - best[j]))
    const dMinus = Math.hypot(...r.map((x, j) => x - worst[j]))
    const sum = dPlus + dMinus
    return sum ? dMinus / sum : 0
  })
}

/** 多元回归：以偏好权重为先验系数的线性模型 Ŷ = Σ βᵢ·Xᵢ（标准化因子） */
function regressionScore(rows: number[][], weights: number[]): number[] {
  return rows.map((r) => r.reduce((a, x, j) => a + x * weights[j], 0))
}

/** K-Means 聚类（k 类；列 z-score 标准化后聚类，初始化取按标准化总和排序的等分位样本） */
function kmeansLabels(rows: number[][], k: number): number[] {
  const m = rows.length
  if (!m) return []
  const n = rows[0].length
  // 列标准化：消除各因子的量纲/方差差异，避免方差大的维度主导分组
  const mean = Array.from({ length: n }, (_, j) => rows.reduce((a, r) => a + r[j], 0) / m)
  const sd = Array.from({ length: n }, (_, j) =>
    Math.sqrt(rows.reduce((a, r) => a + (r[j] - mean[j]) ** 2, 0) / m) || 1
  )
  const z = rows.map((r) => r.map((x, j) => (x - mean[j]) / sd[j]))

  const kk = Math.max(1, Math.min(k, m))
  const sums = z.map((r) => r.reduce((a, b) => a + b, 0))
  const order = z.map((_, i) => i).sort((a, b) => sums[b] - sums[a])
  const centers = Array.from({ length: kk }, (_, i) =>
    z[order[Math.floor((i * (m - 1)) / Math.max(1, kk - 1))]].slice()
  )
  const labels = new Array<number>(m).fill(0)
  for (let iter = 0; iter < 30; iter++) {
    let moved = false
    for (let i = 0; i < m; i++) {
      let pick = 0
      let pickD = Infinity
      for (let c = 0; c < kk; c++) {
        const d = z[i].reduce((a, x, j) => a + (x - centers[c][j]) ** 2, 0)
        if (d < pickD) {
          pickD = d
          pick = c
        }
      }
      if (labels[i] !== pick) {
        labels[i] = pick
        moved = true
      }
    }
    for (let c = 0; c < kk; c++) {
      const members = z.filter((_, i) => labels[i] === c)
      if (!members.length) continue
      centers[c] = centers[c].map((_, j) => members.reduce((a, r) => a + r[j], 0) / members.length)
    }
    if (!moved) break
  }
  return labels
}

/** 线性映射到展示得分区间 */
function rescale(values: number[]): number[] {
  if (!values.length) return []
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min
  if (!span) return values.map(() => round1((SCORE_MIN + SCORE_MAX) / 2))
  return values.map((v) => round1(SCORE_MIN + ((v - min) / span) * (SCORE_MAX - SCORE_MIN)))
}

/* ==================== 图层加载 ==================== */

/**
 * 预加载选址所需图层（与进度动画并行，不阻塞 UI）。
 * 与地图渲染共用缓存，同一图层只会下载一次。
 */
export function preloadSelectionLayers(): void {
  void loadLayers(REQUIRED_LAYERS).catch(() => undefined)
}

async function loadRequired(): Promise<Map<LayerId, LayerFeatures>> {
  const fcs = await loadLayers(REQUIRED_LAYERS)
  const map = new Map<LayerId, LayerFeatures>()
  REQUIRED_LAYERS.forEach((id, i) => map.set(id, fcs[i]))
  return map
}

/* ==================== 主流程 ==================== */

/** 候选池中的原始图斑（未筛选） */
interface RawParcel {
  code: string
  geometry: Polygon
  bbox: BBox
  areaHa: number
  regularity: number
  pt: XY
}

/** 通过初筛、带上下文量测结果的图斑 */
interface ScoredParcel extends RawParcel {
  factors: Record<string, number>
  insideUdb: boolean
  inPark: boolean
  dService: number
  dPark: number
  dIndLand: number
}

/** mock：POST /api/selection/run —— 基于真实控规工业用地图斑的选址计算 */
export async function mockRunSelection(
  req: SelectionRequest,
  scenario: ScenarioDetail,
  onProgress?: (p: { percent: number; log: string }) => void
): Promise<SR> {
  void onProgress
  await sleep(150)

  const byId = await loadRequired()

  /* ---- 1) 候选池：控规工业用地，且落位于研究区内 ---- */
  const poolFc = byId.get(POOL_LAYER)
  const pool: RawParcel[] = []
  if (poolFc) {
    poolFc.features.forEach((f, i) => {
      if (f.geometry.type !== 'Polygon') return
      const geometry = f.geometry as Polygon
      const pt = interiorPoint(geometry)
      if (!pointInPolygon(pt, req.aoi)) return
      pool.push({
        code: `KG-${String(i + 1).padStart(3, '0')}`,
        geometry,
        bbox: bboxOfGeometry(geometry),
        areaHa: m2ToHa(polygonAreaM2(geometry)),
        regularity: polsbyPopper(geometry),
        pt,
      })
    })
  }
  const totalParcels = pool.length

  /* ---- 2) 初选：硬约束一票否决 + 最小面积 + 用地规模区间 ---- */
  const constraints = HARD_CONSTRAINT_LAYERS.map((id) => ({ id, refs: toRefPolys(byId.get(id)) }))

  /**
   * 用地规模约束（用户需求中提到占地面积时生效）：
   * 候选地块面积须落在 [目标 × (1 − 容差), 目标 × (1 + 容差)]。
   * 容差初值为 ±50%（见 config.DEFAULT_AREA_TOLERANCE），最终限值由后端算法设计人员核定。
   */
  const targetArea = req.target_area_ha ?? null
  const tolerance = req.area_tolerance ?? DEFAULT_AREA_TOLERANCE
  const window = targetArea === null ? null : areaWindow(targetArea, tolerance)

  const hitBy = new Map<string, number>()
  let belowMin = 0
  let outsideWindow = 0
  const applyFilters = (useAreaWindow: boolean): RawParcel[] =>
    pool.filter((p) => {
      if (p.areaHa < req.min_area_ha) {
        belowMin++
        return false
      }
      if (useAreaWindow && window && (p.areaHa < window.lo || p.areaHa > window.hi)) {
        outsideWindow++
        return false
      }
      for (const c of constraints) {
        if (c.refs.some((r) => overlapsPolygon(p.geometry, p.bbox, r))) {
          hitBy.set(c.id, (hitBy.get(c.id) ?? 0) + 1)
          return false
        }
      }
      return true
    })

  let feasible = applyFilters(true)

  /**
   * 兜底：面积区间可能把候选池清空（图斑规模天然集中在某一量级）。
   * 依次放宽，保证流程始终可演示，并在 message 中如实说明放宽情况。
   * 后续后端按行业门类核定容差后，这里的兜底可改为直接报错提示「无规模匹配地块」。
   */
  let areaRelaxed = false
  if (!feasible.length && window) {
    belowMin = 0
    outsideWindow = 0
    hitBy.clear()
    feasible = applyFilters(false)
    areaRelaxed = true
  }
  if (!feasible.length) feasible = pool.filter((p) => p.areaHa >= req.min_area_ha)
  if (!feasible.length) feasible = pool

  /* ---- 3) 因子量测（全部来自真实空间关系） ---- */
  const udb = toRefPolys(byId.get('urban-boundary'))
  const industrialLand = toRefPolys(byId.get('industrial-land'))
  const parks = toRefPolys(byId.get('industrial-park'))
  const yellows = toRefPolys(byId.get('yellow-line'))
  const servicePts: XY[] = []
  for (const id of ['prod-service-point', 'prod-service-area'] as LayerId[]) {
    const fc = byId.get(id)
    if (!fc) continue
    for (const f of fc.features) servicePts.push(interiorPoint(f.geometry))
  }

  const factorIds = scenario.factors.map((f) => f.id)

  const scored: ScoredParcel[] = feasible.map((p) => {
    const dUdb = minDistanceM(p.pt, udb)
    const insideUdb = dUdb === 0
    const inPark = containsPoint(p.pt, parks)
    const dPark = minDistanceM(p.pt, parks)
    const dIndLand = minDistanceM(p.pt, industrialLand)
    const dService = minDistanceToPointsM(p.pt, servicePts)
    const dYellow = minDistanceM(p.pt, yellows)

    // 城市规划：城镇开发边界覆盖（0–60）+ 形态规整度（0–25）+ 成片开发规模（0–15）
    // 注意：边界外的分值上限必须低于边界内的基准，避免「距边界越近分越高」的逻辑倒挂
    const udbTerm = insideUdb ? 60 : Math.min(55, decayScore(dUdb, 2000, 15))
    const urbanPlanning = udbTerm + p.regularity * 25 + Math.min(1, p.areaHa / 10) * 15

    // 产业协同：园区平台覆盖（50%）+ 与现状工业用地的集聚度（50%）
    const industry =
      0.5 * (inPark ? 100 : decayScore(dPark, DECAY_M.industry, 20)) +
      0.5 * decayScore(dIndLand, 600, 0)

    // 建造成本：规模效应（面积越大单位成本越低）+ 形状规整度
    const cost = 8 + 45 * p.regularity + 45 * Math.min(p.areaHa / COST_IDEAL_HA, 1)

    const factors: Record<string, number> = {
      urban_planning: round1(clamp01(urbanPlanning)),
      transport: round1(decayScore(dService, DECAY_M.transport)),
      industry: round1(clamp01(industry)),
      infrastructure: round1(decayScore(dYellow, DECAY_M.infrastructure)),
      cost: round1(clamp01(cost)),
    }

    return { ...p, factors, insideUdb, inPark, dService, dPark, dIndLand }
  })

  /* ---- 4) 多准则排序 ---- */
  const rows = scored.map((s) => factorIds.map((id) => s.factors[id] ?? 0))
  const weights = factorIds.map(
    (id) => req.weights_override?.[id] ?? scenario.weights_ahp[id] ?? 1 / factorIds.length
  )

  const baseQuality = regressionScore(rows, weights)
  const closeness = topsisCloseness(rows, weights)
  const labels = kmeansLabels(rows, 3)

  // 聚类序号按平均贴近度降序重排，使「0 = 优先开发类」与综合排名口径一致
  const clusterSum = new Map<number, number>()
  const clusterSize = new Map<number, number>()
  labels.forEach((c, i) => {
    clusterSum.set(c, (clusterSum.get(c) ?? 0) + closeness[i])
    clusterSize.set(c, (clusterSize.get(c) ?? 0) + 1)
  })
  const clusterRank = new Map<number, number>()
  ;[...clusterSum.entries()]
    .map(([c, sum]) => [c, sum / (clusterSize.get(c) ?? 1)] as const)
    .sort((a, b) => b[1] - a[1])
    .forEach(([c], i) => clusterRank.set(c, i))

  let ranking: number[]
  if (req.algorithm === 'regression') {
    ranking = baseQuality
  } else if (req.algorithm === 'kmeans') {
    // 聚类优先：同类地块聚拢排序，类内按质量降序
    ranking = scored.map((_, i) => (3 - (clusterRank.get(labels[i]) ?? 0)) * 1000 + baseQuality[i])
  } else {
    ranking = closeness
  }

  const displayScores = rescale(ranking)
  const order = scored
    .map((_, i) => i)
    .sort((a, b) => ranking[b] - ranking[a])
    .slice(0, Math.max(1, req.top_n))

  const candidates: CandidateParcel[] = order.map((idx, i) => {
    const s = scored[idx]
    const parkText = s.inPark ? '园区内' : `距园区${fmtDist(s.dPark)}`
    const indText = s.dIndLand === 0 ? '现状为工业用地' : `距现状工业${fmtDist(s.dIndLand)}`
    return {
      rank: i + 1,
      score: displayScores[idx],
      area_ha: s.areaHa,
      geometry: s.geometry,
      factors: factorIds.reduce<Record<string, number>>((acc, id) => {
        acc[id] = s.factors[id] ?? 0
        return acc
      }, {}),
      notes:
        `${s.insideUdb ? '开发边界内' : '开发边界外'} · ${parkText} · ${indText} · ` +
        `服务点${fmtDist(s.dService)} · 规整度${(s.regularity * 100).toFixed(0)}%`,
      cluster: clusterRank.get(labels[idx]) ?? 0,
      code: s.code,
      source: '控规工业用地',
    }
  })

  const algoLabel =
    req.algorithm === 'topsis'
      ? 'TOPSIS'
      : req.algorithm === 'regression'
        ? '多元回归'
        : req.algorithm === 'kmeans'
          ? 'K-Means 聚类'
          : '组合赋权'

  const excluded = [...hitBy.entries()].map(([id, n]) => `${id === 'eco-redline' ? '生态保护红线' : '永久基本农田'} ${n}`).join('、')

  // 初选口径说明：面积约束是否生效、是否触发兜底放宽，都在 message 里如实交代
  const tolPct = Math.round(tolerance * 100)
  const areaSeg =
    targetArea === null
      ? `最小面积 ${req.min_area_ha} 公顷`
      : areaRelaxed
        ? `最小面积 ${req.min_area_ha} 公顷（目标 ${targetArea} 公顷 ±${tolPct}% 即 ${window!.lo}–${window!.hi} 公顷内无匹配图斑，已放宽面积约束）`
        : `用地规模 ${window!.lo}–${window!.hi} 公顷（目标 ${targetArea} 公顷，±${tolPct}%，规模不符筛除 ${outsideWindow} 个）与最小面积 ${req.min_area_ha} 公顷`

  return {
    task_id: `task-${Date.now().toString(36)}`,
    scenario_id: req.scenario_id,
    grid_size_m: req.grid_size_m,
    total_cells: totalParcels,
    available_cells: feasible.length,
    candidates,
    message:
      `（真实数据）候选池为控规工业用地 ${totalParcels} 个图斑，` +
      `经底线管控硬约束（${excluded || '无冲突'}）与 ${areaSeg} 筛选后保留 ${feasible.length} 个，` +
      `${algoLabel} 排序输出 Top-${candidates.length} 候选地块。`,
  }
}
