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
        default=None, description="前端偏好权重，键为因子 ID；提供时优先于 AHP+熵权组合")

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


class SelectionResponse(BaseModel):
    task_id: str
    scenario_id: str
    grid_size_m: int
    total_cells: int
    available_cells: int
    candidates: list[CandidateParcel] = []
    message: str = ""
    # ---- 引擎诊断（前端可选使用，不影响既有契约）----
    weights: dict[str, float] = Field(default={}, description="本次实际生效的组合权重")
    sensitivity: dict[str, Any] = Field(
        default={}, description="权重 ±20% 扰动下的 Top-N 稳定性诊断")
