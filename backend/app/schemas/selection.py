from pydantic import BaseModel, Field
from typing import Any


class SelectionRequest(BaseModel):
    """选址分析请求。AOI 为 GeoJSON 几何对象，坐标系 EPSG:4490。"""
    scenario_id: str = Field(default="S1", description="场景模板 ID，见 docs/SCENARIOS.md")
    aoi: dict[str, Any] = Field(..., description="研究区 GeoJSON Geometry (Polygon)")
    grid_size_m: int = Field(default=30, ge=5, le=500)
    min_area_ha: float = Field(default=1.0, ge=0.1)
    top_n: int = Field(default=5, ge=1, le=50)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0,
                         description="AHP 主观权重占比；1-α 为熵权法客观权重占比")
    weights_override: dict[str, float] | None = Field(
        default=None, description="前端手动调权，键为因子 ID")


class CandidateParcel(BaseModel):
    rank: int
    score: float
    area_ha: float
    geometry: dict[str, Any]
    factors: dict[str, float] = {}
    notes: str = ""


class SelectionResponse(BaseModel):
    task_id: str
    scenario_id: str
    grid_size_m: int
    total_cells: int
    available_cells: int
    candidates: list[CandidateParcel] = []
    message: str = ""
