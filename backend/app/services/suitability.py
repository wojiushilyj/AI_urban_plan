"""
选址核心引擎。

流程（详见 docs/SCENARIOS.md 一、统一选址流程）：
  网格化 → 硬约束过滤 → 因子标准化 → AHP+熵权组合赋权 → 打分
  → 连通聚类生成候选地块 → 面积/形状筛选 → Top-N

TODO(09-09 交付)：
  1. grid()        —— AOI 按 grid_size_m 在研究投影坐标系下网格化
  2. filter_hard() —— 约束图层叠加（GeoPandas sjoin / unary_union + buffer）
  3. normalize()   —— 正向/负向/区间型因子 → 0–100
  4. weight()      —— AHP（含 CR<0.1 一致性检验）+ 熵权，按 alpha 组合
  5. cluster()     —— 邻接网格聚类成地块，算面积(shape 在 EPSG:4525 下)与规整度
  6. sensitivity() —— 权重 ±20% 扰动，检验 Top-N 排序稳定性
"""
import uuid

from app.schemas.selection import SelectionRequest, SelectionResponse


def run_selection(req: SelectionRequest) -> SelectionResponse:
    raise NotImplementedError(
        "选址引擎尚未实现，计划 09-09 交付（见 docs/PROGRESS.md 倒排排期）。"
        "实现入口：backend/app/services/suitability.py"
    )


def _new_task_id() -> str:
    return uuid.uuid4().hex[:12]
