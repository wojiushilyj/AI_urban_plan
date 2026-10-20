"""
国土AI竞赛 · LangGraph + PostGIS 医药制药选址智能体自动化验证套件
"""
import sys
from pathlib import Path

# 添加 backend 到系统路径
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.agent.langgraph_agent import pharma_site_agent
from app.agent.spatial_tools import audit_sanitary_and_redlines, evaluate_pharma_parcel_5d
from app.services.postgis_service import postgis_service


def test_postgis_connectivity():
    print("[1/4] 测试 PostGIS 数据库连接与图斑状态...")
    health = postgis_service.health_check()
    print("  PostGIS 状态:", health)
    assert health["status"] == "connected", "PostGIS 连接失败"
    assert health["total_tuban"] > 0, "PostGIS 缺少图斑数据"
    print("  -> PostGIS 校验通过！")


def test_spatial_query_and_scoring():
    print("\n[2/4] 测试 PostGIS 医药地块空间检索与五维指标量算...")
    hq_cands = postgis_service.fetch_pharma_candidates(role="hq", min_ha=0.5, max_ha=10.0, limit=5)
    factory_cands = postgis_service.fetch_pharma_candidates(role="factory", min_ha=2.0, max_ha=30.0, limit=5)

    assert len(hq_cands) > 0, "未查询到 B2 研发总部候选地块"
    assert len(factory_cands) > 0, "未查询到 M1 生产基地候选地块"

    hq_eval = evaluate_pharma_parcel_5d(hq_cands[0], role="hq")
    factory_eval = evaluate_pharma_parcel_5d(factory_cands[0], role="factory")

    print(f"  HQ 地块 #{hq_eval['id']} 得分:", hq_eval["scores"])
    print(f"  生产基地 #{factory_eval['id']} 得分:", factory_eval["scores"])

    for dim in ["planning", "transport", "collaboration", "infrastructure", "cost", "total"]:
        assert dim in hq_eval["scores"], f"缺少评分维度: {dim}"
        assert 0 <= hq_eval["scores"][dim] <= 100, f"评分越界: {dim}"
    print("  -> 空间量算与五维评分校验通过！")


def test_langgraph_agent_workflow():
    print("\n[3/4] 测试 LangGraph 状态图决策流端到端执行...")
    query = (
        "拟在临桂区投资建设生物医药产业综合基地，包含创新药研发总部（B2）与GMP洁净车间生产基地（M1），"
        "要求落实 500 米卫生防护距离，临近高校产学研平台与高速物流通道，开展集中连片与分地块方案比选。"
    )

    init_state = {
        "user_query": query,
        "project_profile": {},
        "raw_candidates": {},
        "audited_candidates": {},
        "evaluated_candidates": {},
        "scheme_comparison": {},
        "opinion_report": "",
        "logs": [],
        "error": None,
    }

    final_state = pharma_site_agent.invoke(init_state)

    # 校验各节点执行结果
    assert len(final_state["logs"]) >= 6, "日志步数不足"
    assert "scheme_comparison" in final_state, "缺少方案比选结果"
    comp = final_state["scheme_comparison"]
    assert "unified_scheme" in comp, "缺少方案A"
    assert "dual_site_scheme" in comp, "缺少方案B"
    assert "recommendation" in comp, "缺少最终裁决建议"
    assert len(final_state["opinion_report"]) > 200, "论证报告长度异常"

    print("  执行日志条数:", len(final_state["logs"]))
    print("  方案比选结论:", comp["recommendation"][:80], "...")
    print("  -> LangGraph 状态流校验通过！")


def test_fastapi_endpoints():
    print("\n[4/4] 测试 FastAPI 路由导入与接口规范...")
    from main import app
    paths = app.openapi()["paths"].keys()
    assert "/api/agent/pharma/run" in paths, "缺少 /api/agent/pharma/run 路由"
    assert "/api/agent/pharma/postgis/health" in paths, "缺少 /api/agent/pharma/postgis/health 路由"
    assert "/api/agent/pharma/postgis/candidates" in paths, "缺少 /api/agent/pharma/postgis/candidates 路由"
    print("  FastAPI 注册路由正常，包含:", [r for r in paths if "pharma" in r])
    print("  -> FastAPI 接口挂载校验通过！")


if __name__ == "__main__":
    print("=" * 60)
    print(" 国土AI · LangGraph + PostGIS 医药选址决策体系自动化验证")
    print("=" * 60)
    test_postgis_connectivity()
    test_spatial_query_and_scoring()
    test_langgraph_agent_workflow()
    test_fastapi_endpoints()
    print("\n" + "=" * 60)
    print(" 全部 4 大测试环节测试通过！(100% PASS)")
    print("=" * 60)
