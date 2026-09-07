"""选址主流程接口。TODO(09-10)：接 services/suitability.py 的真实计算。"""
from fastapi import APIRouter, HTTPException

from app.schemas.selection import SelectionRequest, SelectionResponse
from app.services.suitability import run_selection

router = APIRouter(tags=["选址分析"])


@router.post("/selection/run", response_model=SelectionResponse)
def api_run_selection(req: SelectionRequest):
    """执行一次选址分析：约束过滤 → 适宜性打分 → 候选地块生成。"""
    try:
        return run_selection(req)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
