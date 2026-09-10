"""
选址核心引擎（真实空间计算版）。

流程：
  候选池 → 硬约束一票否决（含缓冲）→ 面积筛选（最小面积 + 用地规模区间）
  → 五维因子量测（真实空间关系）→ 组合赋权（AHP + 熵权）→ 排序（TOPSIS/回归/K-Means）
  → Top-N 输出 + 权重敏感性分析

数据来源（均为真实规划数据，见 data/README.md）：
  候选池  regulated-industrial   控规工业用地
  硬约束  eco-redline            生态保护红线   ┐ 一票否决
          perm-farmland          永久基本农田   ┘
          blue-line              城市蓝线（代河湖管理范围）
          road-network           道路路网（代高速/铁路安全保护距离）
          green-line             城市绿线
          cultural-relic         文物保护区
  软因子  urban-boundary         城镇开发边界      → 城市规划
          prod-service-point/area 生产性服务点位   ┐
          highway-interchange    高速出入口        ├ → 交通物流
          freight-station        货运站            ┘
          industrial-land        总规工业用地      ┐ → 产业协同
          industrial-park        产业园区边界      ┘
          yellow-line            城市黄线          → 基础配套
          几何尺度（面积 + 规整度）                 → 建造成本

口径说明：
  - 距离衰减 score = 100·exp(−d/d0)，d0 为各因子特征尺度（米），并设得分下限避免远距离地块被拉成负分。
  - 距离与面积一律在 EPSG:4525（CGCS2000 3度带 zone 37 / CM 111E）下量算。
  - 输出几何为 EPSG:4490 经纬度，与前端 MapLibre 展示一致。
  - 场景模板中无对应图层的约束（居民点、饮用水源、地质灾害、行洪区、机场净空、污染源）
    会被**如实跳过**并在 message 中列明，不静默忽略。
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Iterable

import numpy as np
from shapely.geometry import Point, mapping, shape
from shapely.strtree import STRtree

from app.config import settings
from app.schemas.selection import CandidateParcel, SelectionRequest, SelectionResponse
from app.services import scenarios as scenario_service
from app.services import spatial

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #

POOL_LAYER = "regulated-industrial"

CONSTRAINT_LAYER: dict[str, str | None] = {
    "eco_redline": "eco-redline",
    "prime_farmland": "perm-farmland",
    "river_range": "blue-line",          # 城市蓝线 ≈ 河湖水域，代理河湖管理范围
    "road_protect": "road-network",      # 道路路网 + 缓冲 = 安全保护距离
    "green_line": "green-line",
    "cultural_relic": "cultural-relic",
    "udb": None,                         # 城镇开发边界不是禁建区 → 作正向因子，不作一票否决
}

CONSTRAINT_LABEL: dict[str, str] = {
    "eco_redline": "生态保护红线",
    "prime_farmland": "永久基本农田",
    "river_range": "河湖管理范围",
    "road_protect": "高速/铁路安全保护距离",
    "green_line": "城市绿线",
    "cultural_relic": "文物保护区",
    "residential": "居民点安全距离",
    "water_source": "饮用水源保护区",
    "geohazard": "地质灾害高易发区",
    "flood_area": "行洪区",
    "airport_clear": "机场净空/限高区",
    "pollution_source": "噪声/污染源防护",
    "udb": "城镇开发边界",
}

# 因子特征尺度（米）：score = 100·exp(−d / d0)
DECAY_M = {"transport": 1500.0, "industry": 1200.0, "infrastructure": 900.0}
FACTOR_FLOOR = 35.0
COST_IDEAL_HA = 8.0
SCORE_MIN, SCORE_MAX = 52.0, 96.0
DEFAULT_DISTANCE = 5000.0   # 图层为空时的兜底距离（米）


# --------------------------------------------------------------------------- #
# 几何工具
# --------------------------------------------------------------------------- #

class RefSet:
    """投影坐标系下的参照几何集合，提供"是否相交""最近距离"查询（STRtree 加速）。"""

    __slots__ = ("geoms", "tree")

    def __init__(self, geoms: Iterable):
        self.geoms = [g for g in geoms if g is not None and not g.is_empty]
        self.tree = STRtree(self.geoms) if self.geoms else None

    def __bool__(self) -> bool:
        return bool(self.geoms)

    def intersects(self, geom) -> bool:
        if self.tree is None:
            return False
        for i in self.tree.query(geom, predicate="intersects"):
            return True
        return False

    def contains_point(self, pt: Point) -> bool:
        if self.tree is None:
            return False
        for i in self.tree.query(pt, predicate="intersects"):
            if self.geoms[int(i)].covers(pt):
                return True
        return False

    def distance(self, pt: Point) -> float:
        """点到集合内最近几何的距离（米）；集合为空或点在集合内时为 0。"""
        if self.tree is None:
            return DEFAULT_DISTANCE
        idx = self.tree.nearest(pt)
        if idx is None:
            return DEFAULT_DISTANCE
        return float(self.geoms[int(idx)].distance(pt))

    @classmethod
    def from_layer(cls, layer_id: str, buffer_m: float = 0.0) -> "RefSet":
        geoms = spatial.projected_geometries(layer_id)
        if buffer_m and buffer_m > 0:
            geoms = [g.buffer(buffer_m) for g in geoms]
        return cls(geoms)


def _decay(distance_m: float, d0: float, floor: float = FACTOR_FLOOR) -> float:
    return max(floor, 100.0 * math.exp(-distance_m / d0))


def _clamp100(x: float) -> float:
    return max(0.0, min(100.0, x))


def _round1(x: float) -> float:
    return round(x, 1)


def _fmt_dist(m: float) -> str:
    return f"{m / 1000:.1f}km" if m >= 1000 else f"{round(m)}m"


def _polsby_popper(geom) -> float:
    """形态规整度：4πA / P²，圆形=1，越接近 1 越规整。"""
    area = geom.area
    perim = geom.length
    if perim <= 0:
        return 0.0
    return float(min(1.0, 4.0 * math.pi * area / (perim * perim)))


# --------------------------------------------------------------------------- #
# 多准则决策
# --------------------------------------------------------------------------- #

def topsis_closeness(rows: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """TOPSIS 贴近度 Cᵢ = Dᵢ⁻ / (Dᵢ⁺ + Dᵢ⁻)。因子均已正向化（越大越优）。"""
    if rows.size == 0:
        return np.array([])
    denom = np.sqrt((rows ** 2).sum(axis=0))
    denom[denom == 0] = 1.0
    weighted = (rows / denom) * weights
    best = weighted.max(axis=0)
    worst = weighted.min(axis=0)
    d_plus = np.sqrt(((weighted - best) ** 2).sum(axis=1))
    d_minus = np.sqrt(((weighted - worst) ** 2).sum(axis=1))
    total = d_plus + d_minus
    total[total == 0] = 1.0
    return d_minus / total


def regression_score(rows: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """多元回归：以权重为先验系数的线性模型 Ŷ = Σ wᵢ·Xᵢ。"""
    if rows.size == 0:
        return np.array([])
    return rows @ weights


def kmeans_labels(rows: np.ndarray, k: int, max_iter: int = 30) -> np.ndarray:
    """K-Means 聚类（列 z-score 标准化，初始化取按标准化总和排序的等分位样本）。"""
    m = rows.shape[0]
    if m == 0:
        return np.array([], dtype=int)
    mean = rows.mean(axis=0)
    sd = rows.std(axis=0)
    sd[sd == 0] = 1.0
    z = (rows - mean) / sd

    kk = max(1, min(k, m))
    order = np.argsort(-z.sum(axis=1))
    centers = np.array([
        z[order[int(i * (m - 1) / max(1, kk - 1))]].copy() for i in range(kk)
    ])

    labels = np.zeros(m, dtype=int)
    for _ in range(max_iter):
        dists = ((z[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dists.argmin(axis=1)
        moved = not np.array_equal(new_labels, labels)
        labels = new_labels
        for c in range(kk):
            members = z[labels == c]
            if members.size:
                centers[c] = members.mean(axis=0)
        if not moved:
            break
    return labels


def rank_clusters(labels: np.ndarray, closeness: np.ndarray) -> dict[int, int]:
    """按类内平均贴近度降序重排类别号：0 = 优先开发类。"""
    stats: dict[int, list[float]] = {}
    for c, v in zip(labels.tolist(), closeness.tolist()):
        stats.setdefault(int(c), []).append(v)
    ordered = sorted(stats.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
    return {c: i for i, (c, _) in enumerate(ordered)}


def rescale(values: np.ndarray) -> np.ndarray:
    """线性映射到展示得分区间（52–96），避免 0/100 的绝对化表述。"""
    if values.size == 0:
        return values
    lo, hi = float(values.min()), float(values.max())
    if hi - lo < 1e-9:
        return np.full(values.shape, (SCORE_MIN + SCORE_MAX) / 2)
    return np.round(SCORE_MIN + (values - lo) / (hi - lo) * (SCORE_MAX - SCORE_MIN), 1)


# --------------------------------------------------------------------------- #
# 赋权
# --------------------------------------------------------------------------- #

def entropy_weights(rows: np.ndarray) -> np.ndarray:
    """熵权法：客观权重，反映各因子在候选集内的信息量（离散度）。"""
    m, n = rows.shape
    if m <= 1 or n == 0:
        return np.full(n, 1.0 / max(1, n))
    shifted = rows - rows.min(axis=0)          # 平移至非负，避免 log 定义域问题
    col_sum = shifted.sum(axis=0)
    col_sum[col_sum == 0] = 1.0
    p = shifted / col_sum
    with np.errstate(divide="ignore", invalid="ignore"):
        logp = np.where(p > 0, np.log(p), 0.0)
    k = 1.0 / math.log(m)
    e = -k * (p * logp).sum(axis=0)
    d = 1.0 - e
    d[d < 0] = 0.0
    total = d.sum()
    if total <= 0:
        return np.full(n, 1.0 / n)
    return d / total


def combine_weights(
    factor_ids: list[str],
    scenario: dict,
    rows: np.ndarray,
    req: SelectionRequest,
) -> tuple[np.ndarray, str]:
    """组合赋权：前端指定 > AHP×α + 熵权×(1−α)。返回 (权重, 来源说明)。"""
    n = len(factor_ids)
    override = req.weights_override or {}
    if any(override.get(fid, 0) > 0 for fid in factor_ids):
        w = np.array([max(0.0, float(override.get(fid, 0.0))) for fid in factor_ids])
        if w.sum() > 0:
            return w / w.sum(), "前端偏好权重"

    ahp = np.array([float(scenario["weights_ahp"].get(fid, 1.0 / n)) for fid in factor_ids])
    ahp = ahp / ahp.sum()
    ent = entropy_weights(rows)
    alpha = float(req.alpha)
    w = alpha * ahp + (1.0 - alpha) * ent
    if w.sum() <= 0:
        w = np.full(n, 1.0 / n)
    return w / w.sum(), f"AHP×{alpha:.2f} + 熵权×{1 - alpha:.2f}"


def sensitivity_topn(
    rows: np.ndarray,
    weights: np.ndarray,
    top_n: int,
    algo: str,
    factor_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    权重 ±20% 扰动下的 Top-N 稳定性：返回最低重合率与最敏感因子。

    说明：敏感性一律基于**打分向量**（TOPSIS 贴近度 / 回归质量）评估。
    K-Means 模式下排序另含聚类优先级，此处不重复聚类，属有意简化。
    """
    base = score_vector(rows, weights, algo)
    base_top = set(np.argsort(-base)[:top_n].tolist())
    if not base_top:
        return {}

    worst = 1.0
    worst_index = 0
    for j in range(len(weights)):
        for sign in (1.2, 0.8):
            w = weights.copy()
            w[j] *= sign
            if w.sum() <= 0:
                continue
            w = w / w.sum()
            alt_top = set(np.argsort(-score_vector(rows, w, algo))[:top_n].tolist())
            overlap = len(base_top & alt_top) / len(base_top)
            if overlap < worst:
                worst, worst_index = overlap, j
    ids = factor_ids or []
    return {
        "min_topn_overlap": round(worst, 3),
        "most_sensitive_factor": ids[worst_index] if ids and worst < 1.0 else "",
    }


def score_vector(rows: np.ndarray, weights: np.ndarray, algo: str) -> np.ndarray:
    """
    展示得分向量（0 前为原始贴近度/质量，后续统一 rescale 到 52–96）。

    - regression → 线性加权质量
    - topsis / kmeans → TOPSIS 贴近度（K-Means 的聚类只影响**排序**，不污染**得分**，
      否则组间量级差会把得分压成清一色的 96 分，失去区分度）
    """
    if rows.size == 0:
        return np.array([])
    if algo == "regression":
        return regression_score(rows, weights)
    return topsis_closeness(rows, weights)


def order_indices(scores: np.ndarray, algo: str, cluster_of: np.ndarray) -> np.ndarray:
    """排序：K-Means 为「聚类优先 + 类内按得分降序」，其余按得分降序。"""
    if scores.size == 0:
        return np.array([], dtype=int)
    if algo == "kmeans" and cluster_of.size == scores.size:
        return np.lexsort((-scores, cluster_of))
    return np.argsort(-scores)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

class _Parcel:
    __slots__ = ("code", "geometry", "geometry_proj", "pt", "area_ha", "regularity")

    def __init__(self, code: str, geometry, geometry_proj):
        self.code = code
        self.geometry = geometry              # EPSG:4490，用于输出
        self.geometry_proj = geometry_proj    # EPSG:4525，用于量算
        self.pt = geometry_proj.representative_point()
        self.area_ha = geometry_proj.area / 10000.0
        self.regularity = _polsby_popper(geometry_proj)


def run_selection(req: SelectionRequest) -> SelectionResponse:
    scenario = scenario_service.get_scenario(req.scenario_id)
    factor_ids = [f["id"] for f in scenario["factors"]]

    # ---- 1) 候选池：控规工业用地 ∩ 研究区 ----
    pool_gdf = spatial.load_layer_projected(POOL_LAYER)
    pool_ll = spatial.load_layer(POOL_LAYER)
    aoi = shape(req.aoi)

    pool: list[_Parcel] = []
    for i, (geom_ll, geom_proj) in enumerate(zip(pool_ll.geometry, pool_gdf.geometry), start=1):
        if geom_ll is None or geom_ll.is_empty or geom_proj is None or geom_proj.is_empty:
            continue
        if not aoi.covers(geom_ll.representative_point()):
            continue
        pool.append(_Parcel(f"KG-{i:03d}", geom_ll, geom_proj))
    total_parcels = len(pool)

    # ---- 2) 硬约束一票否决 ----
    # 默认只启用 required=True 的约束；required=False（如高速保护距离）需由调用方显式启用。
    # 理由：库里只有「道路路网」而无「高速/铁路」专层，若对所有道路一律加 100m 缓冲，
    #       会把 145 个候选图斑剔到只剩 3 个——属于把约束用错，而非地块真的不合规。
    if req.constraints is not None:
        enabled_ids = set(req.constraints)
    else:
        enabled_ids = {c["id"] for c in scenario["constraints"] if c.get("required")}

    applied: list[str] = []
    skipped: list[str] = []
    optional_off: list[str] = []
    constraint_refs: list[tuple[str, RefSet]] = []

    for c in scenario["constraints"]:
        cid = c["id"]
        layer_id = CONSTRAINT_LAYER.get(cid)
        label = CONSTRAINT_LABEL.get(cid, c["name"])

        if cid == "udb":
            skipped.append(f"{label}（非禁建区，改为正向因子）")
            continue
        if cid not in enabled_ids:
            optional_off.append(label)
            continue
        if layer_id is None or layer_id not in spatial.available_layer_ids():
            skipped.append(label)
            continue
        refs = RefSet.from_layer(layer_id, float(c.get("buffer_m", 0) or 0))
        if not refs:
            skipped.append(f"{label}（图层为空）")
            continue
        constraint_refs.append((cid, refs))
        applied.append(label)


    feasible: list[_Parcel] = []
    hit_by: dict[str, int] = {}
    for p in pool:
        blocked = False
        for cid, refs in constraint_refs:
            if refs.intersects(p.geometry_proj):
                hit_by[cid] = hit_by.get(cid, 0) + 1
                blocked = True
                break
        if not blocked:
            feasible.append(p)

    # ---- 3) 面积筛选（最小面积 + 用地规模区间）----
    tolerance = req.area_tolerance if req.area_tolerance is not None else settings.DEFAULT_AREA_TOLERANCE
    target = req.target_area_ha
    window = None
    if target:
        window = (round(target * (1 - tolerance), 2), round(target * (1 + tolerance), 2))

    def by_min_area(items: list[_Parcel]) -> list[_Parcel]:
        return [p for p in items if p.area_ha >= req.min_area_ha]

    above_min = by_min_area(feasible)
    outside_window = 0
    area_relaxed = False
    result = above_min
    if window:
        inside = [p for p in above_min if window[0] <= p.area_ha <= window[1]]
        outside_window = len(above_min) - len(inside)
        result = inside
        if not result:                       # 兜底：规模区间可能把候选清空
            result = above_min
            area_relaxed = True

    if not result:                            # 再兜底：去掉最小面积限制
        result = [p for p in pool if not any(
            refs.intersects(p.geometry_proj) for _, refs in constraint_refs
        )]
    if not result:
        result = pool

    # ---- 4) 五维因子量测（真实空间关系）----
    udb = RefSet.from_layer("urban-boundary")
    yellows = RefSet.from_layer("yellow-line")
    industrial_land = RefSet.from_layer("industrial-land")
    parks = RefSet.from_layer("industrial-park")

    transport_nodes: list = []
    for lid in ("prod-service-point", "prod-service-area", "highway-interchange", "freight-station"):
        if lid in spatial.available_layer_ids():
            transport_nodes.extend(spatial.projected_geometries(lid))
    transport = RefSet(transport_nodes)

    factor_rows: list[list[float]] = []
    factor_cache: list[dict[str, float]] = []
    context: list[dict[str, Any]] = []

    for p in result:
        d_udb = udb.distance(p.pt)
        inside_udb = d_udb == 0.0 or udb.contains_point(p.pt)
        if inside_udb:
            d_udb = 0.0

        in_park = parks.contains_point(p.pt)
        d_park = 0.0 if in_park else parks.distance(p.pt)
        d_ind = industrial_land.distance(p.pt)
        d_service = transport.distance(p.pt)
        d_yellow = yellows.distance(p.pt)

        # 城市规划：开发边界内取「60 基准 + 形态规模得分」，边界外按 55% 折减
        # （严格保证边界外得分上限低于边界内基准，避免"距边界越近分越高"的逻辑倒挂）
        base = p.regularity * 25.0 + min(1.0, p.area_ha / 10.0) * 15.0   # 0–40
        urban_planning = (60.0 + base) if inside_udb else base * 0.55

        # 产业协同：园区平台覆盖（50%）+ 与现状工业用地集聚度（50%）
        industry = 0.5 * (100.0 if in_park else _decay(d_park, DECAY_M["industry"], 20.0)) \
            + 0.5 * _decay(d_ind, 600.0, 0.0)

        # 建造成本：规模效应（面积越大单位成本越低）+ 形状规整度
        cost = 8.0 + 45.0 * p.regularity + 45.0 * min(p.area_ha / COST_IDEAL_HA, 1.0)

        values = {
            "urban_planning": _round1(_clamp100(urban_planning)),
            "transport": _round1(_decay(d_service, DECAY_M["transport"])),
            "industry": _round1(_clamp100(industry)),
            "infrastructure": _round1(_decay(d_yellow, DECAY_M["infrastructure"])),
            "cost": _round1(_clamp100(cost)),
        }
        factor_cache.append(values)
        factor_rows.append([values.get(fid, 0.0) for fid in factor_ids])
        context.append({
            "inside_udb": inside_udb, "in_park": in_park,
            "d_park": d_park, "d_ind": d_ind, "d_service": d_service,
        })

    rows = np.array(factor_rows, dtype=float) if factor_rows else np.zeros((0, len(factor_ids)))

    # ---- 5) 组合赋权 + 排序 ----
    weights, weight_source = combine_weights(factor_ids, scenario, rows, req)
    algo = req.algorithm or "topsis"

    if algo == "kmeans" and rows.size:
        labels = kmeans_labels(rows, 3)
        closeness = topsis_closeness(rows, weights)
        cluster_rank = rank_clusters(labels, closeness)
        cluster_of = np.array([cluster_rank.get(int(c), 0) for c in labels])
    else:
        cluster_of = np.zeros(len(result), dtype=int)

    ranking = score_vector(rows, weights, algo)
    scores = rescale(ranking)

    top_n = max(1, min(req.top_n, len(result)))
    order = order_indices(scores, algo, cluster_of)[:top_n]

    # ---- 6) 输出 ----
    algo_label = {"topsis": "TOPSIS", "regression": "多元回归", "kmeans": "K-Means 聚类"}.get(algo, "TOPSIS")
    candidates: list[CandidateParcel] = []
    for rank, idx in enumerate(order.tolist(), start=1):
        p = result[idx]
        ctx = context[idx]
        park_text = "园区内" if ctx["in_park"] else f"距园区{_fmt_dist(ctx['d_park'])}"
        ind_text = "现状为工业用地" if ctx["d_ind"] == 0 else f"距现状工业{_fmt_dist(ctx['d_ind'])}"
        candidates.append(CandidateParcel(
            rank=rank,
            score=float(scores[idx]),
            area_ha=round(p.area_ha, 2),
            geometry=mapping(p.geometry),
            factors={fid: factor_cache[idx].get(fid, 0.0) for fid in factor_ids},
            notes=(
                f"{'开发边界内' if ctx['inside_udb'] else '开发边界外'} · {park_text} · {ind_text} · "
                f"服务节点{_fmt_dist(ctx['d_service'])} · 规整度{p.regularity * 100:.0f}%"
            ),
            cluster=int(cluster_of[idx]) if algo == "kmeans" else None,
            code=p.code,
            source=spatial.layer_display_name(POOL_LAYER),
        ))

    # ---- 7) 说明文案 ----
    tol_pct = round(tolerance * 100)
    if target is None:
        area_seg = f"最小面积 {req.min_area_ha} 公顷"
    elif area_relaxed:
        area_seg = (f"最小面积 {req.min_area_ha} 公顷（目标 {target} 公顷 ±{tol_pct}% 即 "
                    f"{window[0]}–{window[1]} 公顷内无匹配图斑，已如实放宽规模约束）")
    else:
        area_seg = (f"用地规模 {window[0]}–{window[1]} 公顷（目标 {target} 公顷，±{tol_pct}%，"
                    f"规模不符筛除 {outside_window} 个）与最小面积 {req.min_area_ha} 公顷")

    excluded = "、".join(
        f"{CONSTRAINT_LABEL.get(k, k)} {v}" for k, v in hit_by.items()
    ) or "无冲突"

    parts = [
        f"（真实规划数据）候选池为{spatial.layer_display_name(POOL_LAYER)} {total_parcels} 个图斑，",
        f"经硬约束一票否决（{excluded}）与 {area_seg} 筛选后保留 {len(result)} 个，",
        f"以{weight_source}赋权、{algo_label} 排序输出 Top-{len(candidates)} 候选地块。",
    ]
    if skipped:
        parts.append(f"⚠ 以下约束因缺少图层数据未参与计算：{'、'.join(skipped)}。")
    if optional_off:
        parts.append(f"模板中标为非必须的约束（{'、'.join(optional_off)}）未启用，"
                     f"如需参与一票否决请在请求 constraints 中显式传入。")
    parts.append(f"已参与计算的约束：{'、'.join(applied) or '无'}。")

    sensitivity = sensitivity_topn(rows, weights, len(candidates), algo, factor_ids) if rows.size else {}

    return SelectionResponse(
        task_id=f"task-{uuid.uuid4().hex[:12]}",
        scenario_id=req.scenario_id,
        grid_size_m=req.grid_size_m,
        total_cells=total_parcels,
        available_cells=len(result),
        candidates=candidates,
        message="".join(parts),
        weights={fid: round(float(w), 4) for fid, w in zip(factor_ids, weights)},
        sensitivity=sensitivity,
    )
