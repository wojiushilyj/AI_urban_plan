"""选址主流程接口。真实空间计算见 app/services/suitability.py。"""
import json

from fastapi import APIRouter, HTTPException

from app.db import get_conn
from app.schemas.selection import SelectionRequest, SelectionResponse
from app.services import spatial
from app.services.suitability import run_selection

router = APIRouter(tags=["选址分析"])


@router.post("/selection/run", response_model=SelectionResponse)
def api_run_selection(req: SelectionRequest):
    """
    执行一次选址分析：硬约束一票否决 → 面积筛选 → 五维因子量算 → 组合赋权排序 → Top-N。

    数据缺失时返回 503 并说明原因（不影响前端 mock 演示）。
    """
    try:
        result = run_selection(req)
    except spatial.LayerNotFound as e:
        raise HTTPException(status_code=503, detail=f"空间数据不可用：{e}")
    except Exception as e:  # noqa: BLE001 — 兜底，避免 500 无语义
        raise HTTPException(status_code=500, detail=f"选址计算失败：{type(e).__name__}: {e}")

    _persist_task(req, result)
    return result


@router.get("/selection/result/{task_id}")
def api_get_task(task_id: str):
    """按任务 ID 取回历史选址结果（落库于 SQLite 的 task 表）。"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, scenario_id, status, created_at, result_json FROM task WHERE id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"未找到任务 {task_id}")
    return {
        "task_id": row["id"],
        "scenario_id": row["scenario_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
    }


def _persist_task(req: SelectionRequest, result: SelectionResponse) -> None:
    """把任务与结果写入 SQLite（task 表）。失败不影响主流程。"""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO task (id, scenario_id, aoi_geojson, params_json, "
                "result_json, status) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    result.task_id,
                    result.scenario_id,
                    json.dumps(req.aoi, ensure_ascii=False),
                    json.dumps(req.model_dump(exclude={"aoi"}), ensure_ascii=False, default=str),
                    result.model_dump_json(),
                    "done",
                ),
            )
    except Exception:  # noqa: BLE001 — 落库失败不应让计算白跑
        pass
