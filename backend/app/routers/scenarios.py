"""选址场景（行业门类）模板接口。模板定义见 app/services/scenarios.py 与 docs/SCENARIOS.md。"""
from fastapi import APIRouter

from app.services.scenarios import get_scenario, list_scenarios

router = APIRouter(tags=["行业门类模板"])


@router.get("/scenarios")
def api_list_scenarios():
    """列出全部行业门类模板（概要）。"""
    return {"items": list_scenarios()}


@router.get("/scenarios/{scenario_id}")
def api_get_scenario(scenario_id: str):
    """获取单个行业门类模板详情（硬约束 + 五维因子 + AHP 权重）。"""
    return get_scenario(scenario_id)
