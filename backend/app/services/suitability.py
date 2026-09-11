"""
选址核心引擎。

流程：
  候选池 → 硬约束一票否决（含缓冲）→ 面积筛选（最小面积 + 用地规模区间）
  → 五维因子量测 → 组合赋权 → 排序（TOPSIS/回归/K-Means）
  → Top-N 输出 + 因子贡献分解（可解释）+ 权重扰动稳健性（蒙特卡洛）

因子与特征口径全部来自 `features.py`，与 `ai_model.py` 的偏好学习模型共用，
保证「学到的权重」与「打分的因子」严格对齐。

数据来源（均为真实规划数据，见 data/README.md）：
  候选池  regulated-industrial   控规工业用地
  硬约束  eco-redline / perm-farmland / blue-line / road-network / green-line / cultural-relic
  软因子  见 features.py CityContext.factors()

口径说明：
  - 距离与面积一律在 EPSG:4525（CGCS2000 3度带 zone 37 / CM 111E）下量算。
  - 输出几何为 EPSG:4490 经纬度，与前端 MapLibre 展示一致。
  - 场景模板中无对应图层的约束会被**如实跳过**并在 message 中列明，不静默忽略。
"""
from __future__ import annotations

import math
import uuid
from typing import Any

import numpy as np
from shapely.geometry import mapping, shape

from app.config import settings
from app.schemas.selection import CandidateParcel, SelectionRequest, SelectionResponse
from app.services import ai_model, spatial
from app.services import scenarios as scenario_service
from app.services.features import (
    FACTOR_IDS,
    city_context,
    clamp100,
    fmt_dist,
    polsby_popper,
    round1,
)

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

SCORE_MIN, SCORE_MAX = 52.0, 96.0
MC_SAMPLES = 200            # 蒙特卡洛扰动次数
MC_CONCENTRATION = 25.0     # Dirichlet 集中度参数：越大扰动越小（25 ≈ 权重 CV 20%）


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


def score_vector(rows: np.ndarray, weights: np.ndarray, algo: str) -> np.ndarray:
    """
    展示得分向量（后续统一 rescale 到 52–96）。

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
# 赋权
# --------------------------------------------------------------------------- #

def entropy_weights(rows: np.ndarray) -> np.ndarray:
    """熵权法：客观权重，反映各因子在候选集内的信息量（离散度）。"""
    m, n = rows.shape
    if m <= 1 or n == 0:
        return np.full(n, 1.0 / max(1, n))
    shifted = rows - rows.min(axis=0)
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


def _align(weights: dict[str, float], factor_ids: list[str]) -> np.ndarray:
    """把权重字典对齐到因子顺序并归一化。缺失项按均分补齐。"""
    n = len(factor_ids)
    w = np.array([max(0.0, float(weights.get(fid, 1.0 / n))) for fid in factor_ids])
    s = w.sum()
    return w / s if s > 0 else np.full(n, 1.0 / n)


def combine_weights(
    factor_ids: list[str], scenario: dict, rows: np.ndarray, req: SelectionRequest,
) -> tuple[np.ndarray, str, dict[str, float]]:
    """
    组合赋权，返回 (权重向量, 来源说明, 专家权重字典)。

    优先级：前端偏好权重 > weight_mode 指定的来源。
    weight_mode:
      expert  = AHP×α + 熵权×(1−α)         （默认，专家知识主导）
      learned = AI 从真实开发事实学到的权重   （数据驱动）
      blended = 两者各半
    """
    n = len(factor_ids)
    override = req.weights_override or {}
    if any(override.get(fid, 0) > 0 for fid in factor_ids):
        return _align(override, factor_ids), "前端偏好权重", dict(override)

    ahp = np.array([float(scenario["weights_ahp"].get(fid, 1.0 / n)) for fid in factor_ids])
    ahp = ahp / ahp.sum()
    ent = entropy_weights(rows)
    alpha = float(req.alpha)
    expert = alpha * ahp + (1.0 - alpha) * ent
    expert = expert / expert.sum()
    expert_map = {fid: round(float(v), 4) for fid, v in zip(factor_ids, expert)}

    mode = req.weight_mode or "expert"
    if mode == "expert":
        return expert, f"AHP×{alpha:.2f} + 熵权×{1 - alpha:.2f}", expert_map

    model = ai_model.learn_preference_weights()
    if not model.get("available"):
        return expert, f"AHP×{alpha:.2f} + 熵权×{1 - alpha:.2f}（AI 模型不可用，已回退）", expert_map

    learned_map = model["learned_weights"]
    learned = _align(learned_map, factor_ids)
    if mode == "learned":
        return learned, "AI 学习权重（逻辑回归，基于真实开发事实）", expert_map

    w = 0.5 * expert + 0.5 * learned
    w = w / w.sum()
    return w, "专家权重与 AI 学习权重各半（blended）", expert_map


# --------------------------------------------------------------------------- #
# 可解释性与稳健性
# --------------------------------------------------------------------------- #

def factor_contributions(
    rows: np.ndarray, weights: np.ndarray, algo: str, factor_ids: list[str],
) -> tuple[np.ndarray, dict[str, float]]:
    """
    因子贡献分解（留一法 / Leave-One-Out），模型无关的可解释方法。

    做法：把第 j 个因子整体替换为其均值（「该维度失去区分度」），重算排序分，
    `原分 − 扰动后分` 即该因子的边际贡献：

      正值 = 该因子把这块地**往上拉**（相对候选集平均水平有优势）
      负值 = 该因子把这块地**往下压**（是短板）

    对 TOPSIS 这类非线性排序同样适用 —— 比直接看加权值更严谨。

    返回 (贡献矩阵 m×n，各因子全局平均绝对贡献)。
    注意：全局均值恒为 0（正负抵消），故用「平均绝对贡献」衡量因子整体影响力。
    """
    m, n = rows.shape
    base = score_vector(rows, weights, algo)
    contrib = np.zeros((m, n))
    for j in range(n):
        perturbed = rows.copy()
        perturbed[:, j] = rows[:, j].mean()
        contrib[:, j] = base - score_vector(perturbed, weights, algo)
    avg = {fid: round(float(np.abs(contrib[:, j]).mean()), 4) for j, fid in enumerate(factor_ids)}
    return contrib, avg


def monte_carlo_robustness(
    rows: np.ndarray, weights: np.ndarray, top_n: int, seed: int = 7,
) -> dict[str, Any]:
    """
    蒙特卡洛稳健性：对权重施加随机扰动，统计各候选地块的入选频率。

    扰动方式：以当前权重为期望的 Dirichlet 分布采样（集中度 MC_CONCENTRATION），
    等价于权重在 ±20% 量级内随机波动 —— 模拟专家打分的不确定性。
    每次都按 TOPSIS 贴近度重排（与灵敏度分析口径一致，不重复聚类）。

    输出 `prob_top_n` 即「该地块进入 Top-N 的概率」，比单一确定性排名更能支撑决策。
    """
    m = rows.shape[0]
    if m == 0:
        return {}
    rng = np.random.default_rng(seed)
    k = max(1, min(top_n, m))
    counts = np.zeros(m)
    base = topsis_closeness(rows, weights)
    base_top = np.argsort(-base)[:k]

    for _ in range(MC_SAMPLES):
        w = rng.dirichlet(np.maximum(weights, 1e-6) * MC_CONCENTRATION)
        top = np.argsort(-topsis_closeness(rows, w))[:k]
        counts[top] += 1

    prob = counts / MC_SAMPLES
    return {
        "samples": MC_SAMPLES,
        "top_n": k,
        "prob_top_n": [round(float(prob[i]), 3) for i in base_top],
        "mean_stability": round(float(prob[base_top].mean()), 3),
    }


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
        self.regularity = polsby_popper(geometry_proj)


def run_selection(req: SelectionRequest) -> SelectionResponse:
    scenario = scenario_service.get_scenario(req.scenario_id)
    factor_ids = [f["id"] for f in scenario["factors"]]
    ctx = city_context()

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
        pool.append(_Parcel(f"KG-{i:03d}", geom_ll, geom_proj.buffer(0)))
    total_parcels = len(pool)

    # ---- 2) 硬约束一票否决 ----
    # 默认只启用 required=True 的约束；required=False（如高速保护距离）需由调用方显式启用。
    # 理由：库里只有「道路路网」而无「高速/铁路」专层，若对所有道路一律加 100m 缓冲，
    #       会把 145 个候选图斑剔到只剩 3 个 —— 属于把约束用错，而非地块真的不合规。
    if req.constraints is not None:
        enabled_ids = set(req.constraints)
    else:
        enabled_ids = {c["id"] for c in scenario["constraints"] if c.get("required")}

    applied: list[str] = []
    skipped: list[str] = []
    optional_off: list[str] = []
    constraint_refs: list[tuple[str, Any]] = []

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
        refs = ctx.constraint(layer_id, float(c.get("buffer_m", 0) or 0))
        if not refs:
            skipped.append(f"{label}（图层为空）")
            continue
        constraint_refs.append((cid, refs))
        applied.append(label)

    feasible: list[_Parcel] = []
    hit_by: dict[str, int] = {}
    for p in pool:
        for cid, refs in constraint_refs:
            if refs.intersects(p.geometry_proj):
                hit_by[cid] = hit_by.get(cid, 0) + 1
                break
        else:
            feasible.append(p)

    # ---- 3) 面积筛选（最小面积 + 用地规模区间）----
    tolerance = req.area_tolerance if req.area_tolerance is not None else settings.DEFAULT_AREA_TOLERANCE
    target = req.target_area_ha
    window = None
    if target:
        window = (round(target * (1 - tolerance), 2), round(target * (1 + tolerance), 2))

    above_min = [p for p in feasible if p.area_ha >= req.min_area_ha]
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

    if not result:                           # 再兜底：去掉最小面积限制
        result = [p for p in pool if not any(
            refs.intersects(p.geometry_proj) for _, refs in constraint_refs
        )]
    if not result:
        result = pool

    # ---- 4) 五维因子量测（真实空间关系，口径见 features.py）----
    factor_rows: list[list[float]] = []
    factor_cache: list[dict[str, float]] = []
    context: list[dict[str, Any]] = []

    for p in result:
        f = ctx.factors(p.geometry_proj, p.pt, p.area_ha, p.regularity)
        factor_cache.append(f)
        factor_rows.append([f.get(fid, 0.0) for fid in factor_ids])
        context.append(f["_debug"])

    rows = np.array(factor_rows, dtype=float) if factor_rows else np.zeros((0, len(factor_ids)))

    # ---- 5) 组合赋权 + 排序 ----
    weights, weight_source, expert_weights = combine_weights(factor_ids, scenario, rows, req)
    algo = req.algorithm or "topsis"

    if algo == "kmeans" and rows.size:
        labels = kmeans_labels(rows, 3)
        closeness = topsis_closeness(rows, weights)
        cluster_rank = rank_clusters(labels, closeness)
        cluster_of = np.array([cluster_rank.get(int(c), 0) for c in labels])
    else:
        cluster_of = np.zeros(len(result), dtype=int)

    scores = rescale(score_vector(rows, weights, algo))
    top_n = max(1, min(req.top_n, len(result)))
    order = order_indices(scores, algo, cluster_of)[:top_n]

    # ---- 6) 可解释性与稳健性（仅对 Top-N 展开贡献）----
    contrib_matrix, contrib_avg = (np.zeros((0, len(factor_ids))), {})
    if rows.size:
        contrib_matrix, contrib_avg = factor_contributions(rows, weights, algo, factor_ids)
    robustness = monte_carlo_robustness(rows, weights, top_n) if rows.size else {}

    # robustness.prob_top_n 的顺序 = 按 TOPSIS 贴近度的基准 Top-N 下标顺序，此处建立 下标→概率 映射
    prob_by_index: dict[int, float] = {}
    if rows.size and robustness:
        base_top_order = np.argsort(-topsis_closeness(rows, weights))[:top_n]
        prob_by_index = {
            int(i): p for i, p in zip(base_top_order, robustness.get("prob_top_n", []))
        }

    # ---- 7) 输出 ----
    algo_label = {"topsis": "TOPSIS", "regression": "多元回归", "kmeans": "K-Means 聚类"}.get(algo, "TOPSIS")
    candidates: list[CandidateParcel] = []
    for rank, idx in enumerate(order.tolist(), start=1):
        p = result[idx]
        c = context[idx]
        park_text = "园区内" if c["in_park"] else f"距园区{fmt_dist(c['d_park'])}"
        agg_text = "紧邻现状工业" if c["d_agg"] == 0 else f"距现状工业{fmt_dist(c['d_agg'])}"

        row = contrib_matrix[idx] if contrib_matrix.size else np.zeros(len(factor_ids))
        contrib = {fid: round(float(row[j]), 4) for j, fid in enumerate(factor_ids)}
        # 主导优势：贡献最大的**正**项；短板：贡献最小的负项。两者都只有存在时才给值。
        positives = {k: v for k, v in contrib.items() if v > 0}
        top_driver = max(positives.items(), key=lambda kv: kv[1])[0] if positives else ""
        worst = min(contrib.items(), key=lambda kv: kv[1])[0] if contrib else ""
        top_weakness = worst if contrib.get(worst, 0) < 0 else ""

        candidates.append(CandidateParcel(
            rank=rank,
            score=float(scores[idx]),
            area_ha=round(p.area_ha, 2),
            geometry=mapping(p.geometry),
            factors={fid: factor_cache[idx].get(fid, 0.0) for fid in factor_ids},
            notes=(
                f"{'开发边界内' if c['inside_udb'] else '开发边界外'} · {park_text} · {agg_text} · "
                f"服务节点{fmt_dist(c['d_service'])} · 规整度{p.regularity * 100:.0f}% · "
                f"现状建筑占地{c['density'] * 100:.0f}%"
            ),
            cluster=int(cluster_of[idx]) if algo == "kmeans" else None,
            code=p.code,
            source=spatial.layer_display_name(POOL_LAYER),
            contributions=contrib,
            top_driver=top_driver,
            top_weakness=top_weakness,
            build_density=round(float(c["density"]), 3),
            robustness=prob_by_index.get(idx),
        ))

    # ---- 8) 说明文案 ----
    tol_pct = round(tolerance * 100)
    if target is None:
        area_seg = f"最小面积 {req.min_area_ha} 公顷"
    elif area_relaxed:
        area_seg = (f"最小面积 {req.min_area_ha} 公顷（目标 {target} 公顷 ±{tol_pct}% 即 "
                    f"{window[0]}–{window[1]} 公顷内无匹配图斑，已如实放宽规模约束）")
    else:
        area_seg = (f"用地规模 {window[0]}–{window[1]} 公顷（目标 {target} 公顷，±{tol_pct}%，"
                    f"规模不符筛除 {outside_window} 个）与最小面积 {req.min_area_ha} 公顷")

    excluded = "、".join(f"{CONSTRAINT_LABEL.get(k, k)} {v}" for k, v in hit_by.items()) or "无冲突"

    parts = [
        f"（真实规划数据）候选池为{spatial.layer_display_name(POOL_LAYER)} {total_parcels} 个图斑，",
        f"经硬约束一票否决（{excluded}）与 {area_seg} 筛选后保留 {len(result)} 个，",
        f"以{weight_source}赋权、{algo_label} 排序输出 Top-{len(candidates)} 候选地块。",
    ]
    if robustness:
        parts.append(f"蒙特卡洛扰动（{robustness['samples']} 次）下 Top-{top_n} 平均入选概率 "
                     f"{robustness['mean_stability']:.0%}。")
    if skipped:
        parts.append(f"⚠ 以下约束因缺少图层数据未参与计算：{'、'.join(skipped)}。")
    if optional_off:
        parts.append(f"模板中标为非必须的约束（{'、'.join(optional_off)}）未启用，"
                     f"如需参与一票否决请在请求 constraints 中显式传入。")
    parts.append(f"已参与计算的约束：{'、'.join(applied) or '无'}。")

    return SelectionResponse(
        task_id=f"task-{uuid.uuid4().hex[:12]}",
        scenario_id=req.scenario_id,
        grid_size_m=req.grid_size_m,
        total_cells=total_parcels,
        available_cells=len(result),
        candidates=candidates,
        message="".join(parts),
        weights={fid: round(float(w), 4) for fid, w in zip(factor_ids, weights)},
        expert_weights=expert_weights,
        weight_mode=req.weight_mode or "expert",
        weight_source=weight_source,
        sensitivity=contrib_avg,
        robustness=robustness,
    )
