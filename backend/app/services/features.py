"""
空间特征工程：选址因子与模型特征的**唯一**计算口径。

设计动机：选址引擎（suitability）与偏好学习模型（ai_model）必须用完全相同的
因子定义，否则「学到的权重」与「打分的因子」对不上，模型结论无效。
故把 RefSet、衰减函数、因子公式、建筑密度、邻域特征全部收敛到本模块。

坐标系：所有距离/面积一律在 EPSG:4525（CGCS2000 3度带 zone 37 / CM 111E）下量算。
严禁在 EPSG:4490（度）下直接计算距离或面积。
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from shapely.geometry import Point
from shapely.strtree import STRtree

from app.services import spatial

# --------------------------------------------------------------------------- #
# 常量（改动会影响全部因子与模型，谨慎）
# --------------------------------------------------------------------------- #

DECAY_M = {"transport": 1500.0, "industry": 1200.0, "infrastructure": 900.0}
FACTOR_FLOOR = 35.0          # 因子得分下限，避免远距离地块被拉成负分
COST_IDEAL_HA = 8.0          # 规模化最优参考面积（公顷）
DEFAULT_DISTANCE = 5000.0    # 参照图层为空时的兜底距离（米）
DEMOLITION_WEIGHT = 55.0     # 拆迁成本权重：建筑占地率对建造成本的最大惩罚

FACTOR_IDS = ["urban_planning", "transport", "industry", "infrastructure", "cost"]


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #

class RefSet:
    """投影坐标系下的参照几何集合，提供「是否相交」「最近距离」「是否覆盖」查询。"""

    __slots__ = ("geoms", "tree")

    def __init__(self, geoms):
        self.geoms = [g for g in geoms if g is not None and not g.is_empty]
        self.tree = STRtree(self.geoms) if self.geoms else None

    def __bool__(self) -> bool:
        return bool(self.geoms)

    def intersects(self, geom) -> bool:
        if self.tree is None:
            return False
        for _ in self.tree.query(geom, predicate="intersects"):
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
        """点到集合内最近几何的距离（米）。集合为空时返回兜底距离。"""
        if self.tree is None:
            return DEFAULT_DISTANCE
        idx = self.tree.nearest(pt)
        if idx is None:
            return DEFAULT_DISTANCE
        return float(self.geoms[int(idx)].distance(pt))

    def covered_area(self, geom) -> float:
        """geom 落在集合内的面积（m²）。用于建筑占地率等覆盖率指标。"""
        if self.tree is None:
            return 0.0
        total = 0.0
        for i in self.tree.query(geom, predicate="intersects"):
            try:
                total += geom.intersection(self.geoms[int(i)]).area
            except Exception:      # 个别几何存在拓扑缺陷，跳过而非中断
                continue
        return total

    @classmethod
    def from_layer(cls, layer_id: str, buffer_m: float = 0.0) -> "RefSet":
        if layer_id not in spatial.available_layer_ids():
            return cls([])
        geoms = spatial.projected_geometries(layer_id)
        if buffer_m and buffer_m > 0:
            geoms = [g.buffer(buffer_m) for g in geoms]
        return cls([g.buffer(0) for g in geoms])


def decay(distance_m: float, d0: float, floor: float = FACTOR_FLOOR) -> float:
    """距离衰减得分：100·exp(−d/d0)，下限 floor，上限 100。"""
    return max(floor, 100.0 * math.exp(-distance_m / d0))


def clamp100(x: float) -> float:
    return max(0.0, min(100.0, x))


def round1(x: float) -> float:
    return round(x, 1)


def fmt_dist(m: float) -> str:
    return f"{m / 1000:.1f}km" if m >= 1000 else f"{round(m)}m"


def polsby_popper(geom) -> float:
    """形态规整度 4πA/P²，圆形=1。"""
    perim = geom.length
    if perim <= 0:
        return 0.0
    return float(min(1.0, 4.0 * math.pi * geom.area / (perim * perim)))


# --------------------------------------------------------------------------- #
# 城市上下文（参照图层集合，构建一次全局复用）
# --------------------------------------------------------------------------- #

class CityContext:
    """
    一次构建、全局复用的空间参照集合。

    说明：图层数据是静态的，STRtree 构建成本远高于查询，故按进程缓存。
    若数据文件更新（重新跑 preprocess.py），需重启后端进程。
    """

    __slots__ = ("udb", "yellow", "agglomeration", "parks", "transport",
                 "buildings", "constraint_cache")

    def __init__(self) -> None:
        self.udb = RefSet.from_layer("urban-boundary")
        self.yellow = RefSet.from_layer("yellow-line")
        # ⚠️ 产业协同的集聚度参照**必须用总规工业用地（industrial-land）**，不能用现状工业用地
        # （current-industrial-land）。原因见 ai_model.py 顶部说明：现状工业用地正是
        # 「已开发」标签的来源图层，用它算距离等于把标签当特征喂进模型 —— 数据泄漏。
        # 总规工业用地是规划层，与现状层的空间重叠仅 28%，不构成泄漏。
        self.agglomeration = RefSet.from_layer("industrial-land")
        self.parks = RefSet.from_layer("industrial-park")
        self.buildings = RefSet.from_layer("current-building")

        nodes = []
        for lid in ("prod-service-point", "prod-service-area",
                    "highway-interchange", "freight-station"):
            if lid in spatial.available_layer_ids():
                nodes.extend(spatial.projected_geometries(lid))
        self.transport = RefSet(nodes)

        self.constraint_cache: dict[str, RefSet] = {}

    def constraint(self, layer_id: str, buffer_m: float = 0.0) -> RefSet:
        key = f"{layer_id}@{buffer_m}"
        if key not in self.constraint_cache:
            self.constraint_cache[key] = RefSet.from_layer(layer_id, buffer_m)
        return self.constraint_cache[key]

    # ---------------- 因子计算 ---------------- #

    def building_density(self, geom_proj) -> float:
        """地块内现状建筑占地率（0–1）。作为建造成本的**拆迁量**代理指标。"""
        if not self.buildings or geom_proj.area <= 0:
            return 0.0
        return min(1.0, self.buildings.covered_area(geom_proj) / geom_proj.area)

    def neighborhood_density(self, geom_proj, radius_m: float = 500.0) -> float:
        """
        邻域建筑密度：地块**外围环形缓冲**内的建筑占地率（0–1）。

        ⚠️ 必须扣除地块自身 —— 用 `buffer.difference(地块)` 取环带，而不是直接 buffer。
        否则地块自己的建筑会被算进环带，对「该地块是否已开发」构成定义性泄漏
        （见 ai_model.py 的泄漏审计说明）。
        环带面积过小时返回 0。
        """
        if not self.buildings:
            return 0.0
        try:
            ring = geom_proj.buffer(radius_m).difference(geom_proj)
        except Exception:
            return 0.0
        if ring.is_empty or ring.area <= 0:
            return 0.0
        return min(1.0, self.buildings.covered_area(ring) / ring.area)

    def factors(self, geom_proj, pt: Point, area_ha: float, regularity: float) -> dict[str, float]:
        """
        计算五维因子得分（0–100，全部已正向化：越大越优）。

        urban_planning   城市规划：开发边界内 60 基准 + 形态规模分；边界外按 55% 折减
        transport        交通物流：到最近交通节点（服务点/高速口/货运站）的衰减
        industry         产业协同：园区平台覆盖 50% + 与现状工业集聚度 50%
        infrastructure   基础配套：到城市黄线的衰减
        cost             建造成本：规模效应 + 形态规整 − 拆迁惩罚（现状建筑占地率）
        """
        inside_udb = self.udb.contains_point(pt)
        d_udb = 0.0 if inside_udb else self.udb.distance(pt)

        in_park = self.parks.contains_point(pt)
        d_park = 0.0 if in_park else self.parks.distance(pt)
        d_agg = self.agglomeration.distance(pt)
        d_service = self.transport.distance(pt)
        d_yellow = self.yellow.distance(pt)
        density = self.building_density(geom_proj)

        # 城市规划：严格保证边界外上限低于边界内基准，杜绝「离边界越近分越高」的逻辑倒挂
        base = regularity * 25.0 + min(1.0, area_ha / 10.0) * 15.0      # 0–40
        urban_planning = (60.0 + base) if inside_udb else base * 0.55

        industry = 0.5 * (100.0 if in_park else decay(d_park, DECAY_M["industry"], 20.0)) \
            + 0.5 * decay(d_agg, 600.0, 0.0)

        base_cost = 8.0 + 45.0 * regularity + 45.0 * min(area_ha / COST_IDEAL_HA, 1.0)
        cost = base_cost - DEMOLITION_WEIGHT * density

        return {
            "urban_planning": round1(clamp100(urban_planning)),
            "transport": round1(decay(d_service, DECAY_M["transport"])),
            "industry": round1(clamp100(industry)),
            "infrastructure": round1(decay(d_yellow, DECAY_M["infrastructure"])),
            "cost": round1(clamp100(cost)),
            "_debug": {                      # 供说明文案使用，不参与打分
                "inside_udb": inside_udb, "in_park": in_park,
                "d_park": d_park, "d_agg": d_agg, "d_service": d_service,
                "d_udb": d_udb, "density": density, "base_cost": base_cost,
            },
        }


@lru_cache(maxsize=1)
def city_context() -> CityContext:
    return CityContext()


# --------------------------------------------------------------------------- #
# 邻域特征（空间滞后项）
# --------------------------------------------------------------------------- #

def neighborhood_score(
    factor_matrix: np.ndarray,
    centroids: np.ndarray,
    k: int = 5,
) -> np.ndarray:
    """
    空间邻域特征：每块地取其 **k 个最近邻**（按质心距离）的因子均值。

    这是地理学第一定律（Tobler）在模型中的体现 —— 地块的开发可能性受相邻地块影响。
    不含任何标签信息，故不存在泄漏风险。
    """
    n = factor_matrix.shape[0]
    if n <= 1:
        return factor_matrix.mean(axis=1) if n else np.array([])

    kk = max(1, min(k, n - 1))
    diff = centroids[:, None, :] - centroids[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    np.fill_diagonal(dist, np.inf)          # 排除自身

    out = np.empty(n)
    for i in range(n):
        idx = np.argpartition(dist[i], kk)[:kk]
        out[i] = factor_matrix[idx].mean()
    return out
