"""
医药制药选址智能体与 PostGIS 空间数据 API 路由。
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.langgraph_agent import pharma_site_agent
from app.services.postgis_service import postgis_service

router = APIRouter(prefix="/agent/pharma", tags=["医药选址智能体 (LangGraph & PostGIS)"])


class PharmaAgentRequest(BaseModel):
    query: str = Field(
        default="桂林临桂区建设现代生物制药项目，包括研发总部和生产基地，需进行集中连片与分地块方案比选",
        description="自然语言选址诉求与功能说明",
    )
    hq_min_ha: float = Field(default=0.5, ge=0.1, description="研发总部最小用地 (公顷)")
    hq_max_ha: float = Field(default=8.0, le=50.0, description="研发总部最大用地 (公顷)")
    factory_min_ha: float = Field(default=2.0, ge=0.5, description="生产基地最小用地 (公顷)")
    factory_max_ha: float = Field(default=30.0, le=100.0, description="生产基地最大用地 (公顷)")
    sanitary_buffer_m: float = Field(default=300.0, description="卫生防护隔离距离 (米)")


@router.post("/run")
def api_run_pharma_agent(req: PharmaAgentRequest) -> Dict[str, Any]:
    """
    启动 LangGraph 医药选址决策智能体：
    意图解析 -> PostGIS 检索 -> 底线审查 -> 五维打分 -> 双方案比选 -> 报告生成。
    """
    try:
        init_state = {
            "user_query": req.query,
            "project_profile": {
                "hq_min_ha": req.hq_min_ha,
                "hq_max_ha": req.hq_max_ha,
                "factory_min_ha": req.factory_min_ha,
                "factory_max_ha": req.factory_max_ha,
                "sanitary_buffer_m": req.sanitary_buffer_m,
            },
            "raw_candidates": {},
            "audited_candidates": {},
            "evaluated_candidates": {},
            "scheme_comparison": {},
            "opinion_report": "",
            "logs": [],
            "error": None,
        }
        final_state = pharma_site_agent.invoke(init_state)
        return {
            "status": "success",
            "project_profile": final_state.get("project_profile", {}),
            "scheme_comparison": final_state.get("scheme_comparison", {}),
            "top_candidates": {
                "hq": final_state.get("evaluated_candidates", {}).get("hq", [])[:5],
                "factory": final_state.get("evaluated_candidates", {}).get("factory", [])[:5],
                "unified": final_state.get("evaluated_candidates", {}).get("unified", [])[:3],
            },
            "opinion_report": final_state.get("opinion_report", ""),
            "logs": final_state.get("logs", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能体执行异常: {e}")


@router.get("/postgis/health")
def api_postgis_health():
    """检测 PostGIS 远程空间数据库连接状态与图斑统计。"""
    return postgis_service.health_check()


@router.get("/postgis/candidates")
def api_get_postgis_candidates(role: str = "factory", min_ha: float = 1.0, max_ha: float = 20.0, limit: int = 20):
    """直接按角色检索 PostGIS 候选空间图斑（GeoJSON 格式）。"""
    return postgis_service.fetch_pharma_candidates(role=role, min_ha=min_ha, max_ha=max_ha, limit=limit)
