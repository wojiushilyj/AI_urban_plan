from typing import Any, Literal

from pydantic import BaseModel, Field


class SelectionRequest(BaseModel):
    """选址分析请求。AOI 为 GeoJSON 几何对象，坐标系 EPSG:4490。"""
    scenario_id: str = Field(default="B", description="行业门类模板 ID，见 docs/SCENARIOS.md")
    aoi: dict[str, Any] = Field(..., description="研究区 GeoJSON Geometry (Polygon)，EPSG:4490")
    grid_size_m: int = Field(default=30, ge=5, le=500)
    min_area_ha: float = Field(default=1.0, ge=0.1)
    top_n: int = Field(default=5, ge=1, le=50)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0,
                         description="AHP 主观权重占比；1-α 为熵权法客观权重占比")
    weights_override: dict[str, float] | None = Field(
        default=None, description="前端偏好权重，键为因子 ID；提供时优先于其它赋权方式")

    # ---- 权重来源（AI 能力的接入点）----
    weight_mode: Literal["expert", "learned", "blended"] = Field(
        default="expert",
        description=("expert=AHP+熵权（默认，专家知识主导）；"
                     "learned=AI 从真实开发事实学到的权重；"
                     "blended=两者各半"))

    # ---- 硬约束启用集合 ----
    constraints: list[str] | None = Field(
        default=None,
        description=("显式启用的硬约束 id 列表。为空时默认只启用模板中标为 required 的约束；"
                     "required=False 的约束（如高速保护距离）需显式传入才参与一票否决，"
                     "避免「一刀切」式过度剔除候选地块"))

    # ---- 多准则算法选型（模块清单 4.5）----
    algorithm: Literal["topsis", "regression", "kmeans"] = Field(
        default="topsis",
        description="topsis=逼近理想解排序 / regression=多元回归 / kmeans=K-Means 聚类优先")

    # ---- 用地规模约束（用户需求中提到占地面积时生效）----
    target_area_ha: float | None = Field(
        default=None, ge=0.0,
        description="目标用地规模（公顷），由 AI 需求解析得到；为空则不做规模匹配")
    area_tolerance: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description=("用地规模容差（±比例）。候选地块面积须落在 "
                     "[目标×(1−容差), 目标×(1+容差)] 内。"
                     "0.5（±50%）为初期限定，最终限值由算法设计人员按行业门类核定"))


class CandidateParcel(BaseModel):
    rank: int
    score: float
    area_ha: float
    geometry: dict[str, Any] = Field(description="EPSG:4490 经纬度 GeoJSON 几何")
    factors: dict[str, float] = {}
    notes: str = ""
    cluster: int | None = Field(default=None, description="聚类分组，仅 algorithm=kmeans 时返回")
    code: str | None = Field(default=None, description="地块编码，由来源图层 + 要素序号生成")
    source: str | None = Field(default=None, description="来源图层名称")

    # ---- 可解释 AI：因子贡献分解（留一法）----
    contributions: dict[str, float] = Field(
        default={},
        description=("各因子对该地块排序分的边际贡献（留一法：把该因子替换为全域均值后重算）。"
                     "正值 = 该因子把地块往上拉（优势）；负值 = 往下压（短板）。"))
    top_driver: str = Field(default="", description="贡献最大的**正**项（主导优势），无正项时为空")
    top_weakness: str = Field(default="", description="贡献最小的负项（主要短板），无负项时为空")
    build_density: float = Field(default=0.0, description="地块内现状建筑占地率（拆迁量代理）")

    # ---- 稳健性：该地块进入 Top-N 的蒙特卡洛概率 ----
    robustness: float | None = Field(
        default=None, description="权重扰动下该地块保持在 Top-N 的概率（0–1）")


class SelectionResponse(BaseModel):
    task_id: str
    scenario_id: str
    grid_size_m: int
    total_cells: int
    available_cells: int
    candidates: list[CandidateParcel] = []
    message: str = ""

    # ---- 权重来源（便于前端展示与复核）----
    weights: dict[str, float] = Field(default={}, description="本次实际生效的组合权重")
    expert_weights: dict[str, float] = Field(
        default={}, description="对照用的 AHP+熵权专家权重，便于与 AI 学习权重对比")
    weight_mode: str = Field(default="expert", description="本次使用的权重来源")
    weight_source: str = Field(default="", description="权重来源的中文说明")

    # ---- 引擎诊断（前端可选使用）----
    sensitivity: dict[str, float] = Field(
        default={}, description="各因子的全局平均边际贡献（留一法）")
    robustness: dict[str, Any] = Field(
        default={}, description="蒙特卡洛稳健性摘要：Top-N 入选概率与平均稳定性")
