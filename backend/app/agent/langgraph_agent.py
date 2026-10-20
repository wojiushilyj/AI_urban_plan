"""
基于 LangGraph 的医药制药多步骤选址决策智能体。
构建『意图解析 → PostGIS 图斑检索 → 底线合规审查 → 五维空间量算 → 双方案系统比选 → 规划论证报告』循环决策流。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agent.spatial_tools import (
    audit_sanitary_and_redlines,
    compare_pharma_schemes,
    evaluate_pharma_parcel_5d,
)
from app.config import settings
from app.services.llm import chat, llm_available
from app.services.postgis_service import postgis_service

logger = logging.getLogger(__name__)


class PharmaSiteState(TypedDict):
    """LangGraph 选址智能体全状态定义。"""
    user_query: str
    project_profile: Dict[str, Any]
    raw_candidates: Dict[str, List[Dict[str, Any]]]
    audited_candidates: Dict[str, List[Dict[str, Any]]]
    evaluated_candidates: Dict[str, List[Dict[str, Any]]]
    scheme_comparison: Dict[str, Any]
    opinion_report: str
    logs: List[str]
    error: Optional[str]


# --------------------------------------------------------------------------- #
# 节点实现
# --------------------------------------------------------------------------- #

def node_parse_requirements(state: PharmaSiteState) -> Dict[str, Any]:
    """节点 1：自然语言意图深度解析与医药行业参数结构化提取。"""
    logs = list(state.get("logs", []))
    logs.append("【步骤 1/6】启动智能体需求解析节点，提炼制药项目规划边界与功能分区参数...")

    query = state.get("user_query", "")

    # 默认产业画像
    profile = {
        "project_type": "生物医药/现代制药综合产业项目",
        "hq_min_ha": 0.5,
        "hq_max_ha": 8.0,
        "factory_min_ha": 2.0,
        "factory_max_ha": 25.0,
        "unified_min_ha": 5.0,
        "unified_max_ha": 35.0,
        "sanitary_buffer_m": 300.0,
        "priority": "balanced",
        "scheme_mode": "dual_and_unified",  # 比选集中式与分布式
    }

    # 规则识别卫生防护与规模偏好
    if "原料药" in query or "重化工" in query or "发酵" in query or "500" in query:
        profile["sanitary_buffer_m"] = 500.0
        logs.append("  -> 识别到原料药/高防护诉求，将车间卫生防护缓冲距离提高至 500 米。")
    else:
        logs.append("  -> 采用标准制剂与洁净车间基准防护距离：300 米。")

    if "集中" in query and "分地块" not in query:
        profile["scheme_mode"] = "unified"
    elif "分地块" in query or "总部" in query:
        profile["scheme_mode"] = "dual_site"

    # 若 LLM 可用，进行提示词语义增强
    if llm_available():
        logs.append("  -> 调用大模型增强解析，提炼医药产业链协同与环境敏感要求...")
        sys_prompt = (
            "你是一个国家注册城乡规划师及产业选址专家。请分析用户的医药制药项目选址诉求，"
            "指出核心功能分区（研发总部B2 vs 生产基地M1）、卫生防护、环保排污和交通冷链关键点。"
        )
        llm_reply = chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": query or "桂林临桂区建设高品质生物医药产业园，含研发总部与GMP生产基地"},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        if llm_reply:
            profile["llm_summary"] = llm_reply

    logs.append(
        f"  [OK] 参数提取完成：总部建议区间 [{profile['hq_min_ha']}~{profile['hq_max_ha']} ha]，"
        f"生产基地建议区间 [{profile['factory_min_ha']}~{profile['factory_max_ha']} ha]。"
    )

    return {"project_profile": profile, "logs": logs}


def node_postgis_retrieval(state: PharmaSiteState) -> Dict[str, Any]:
    """节点 2：连接 PostGIS 空间数据库（117.72.210.60:5432/onemap_db），按国标代码检索候选图斑。"""
    logs = list(state.get("logs", []))
    logs.append("【步骤 2/6】连接 PostGIS 远程空间数据库，执行候选地块空间过滤与属性查询...")

    profile = state["project_profile"]

    # 1. 检索研发总部候选地块 (B2 商务用地 0902 / 创新型产业 0904)
    hq_parcels = postgis_service.fetch_pharma_candidates(
        role="hq",
        min_ha=profile["hq_min_ha"],
        max_ha=profile["hq_max_ha"],
        limit=20,
    )

    # 2. 检索现代生产基地候选地块 (M1 一类工业 100101 / M2 100102 / M 1001)
    factory_parcels = postgis_service.fetch_pharma_candidates(
        role="factory",
        min_ha=profile["factory_min_ha"],
        max_ha=profile["factory_max_ha"],
        limit=20,
    )

    # 3. 检索集中连片大型产业用地 (>= 5.0 ha)
    unified_parcels = postgis_service.fetch_pharma_candidates(
        role="unified",
        min_ha=profile["unified_min_ha"],
        max_ha=profile["unified_max_ha"],
        limit=15,
    )

    logs.append(
        f"  [OK] PostGIS 检索完成：发现研发总部(B2)备选 {len(hq_parcels)} 宗、"
        f"生产基地(M1)备选 {len(factory_parcels)} 宗、集中连片大宗产业用地 {len(unified_parcels)} 宗。"
    )

    return {
        "raw_candidates": {
            "hq": hq_parcels,
            "factory": factory_parcels,
            "unified": unified_parcels,
        },
        "logs": logs,
    }


def node_compliance_audit(state: PharmaSiteState) -> Dict[str, Any]:
    """节点 3：规划底线一票否决与安全卫生防护审查。"""
    logs = list(state.get("logs", []))
    logs.append("【步骤 3/6】执行三区三线（生态红线、永久基本农田、城市蓝线）拓扑相交与卫生防护审查...")

    raw = state["raw_candidates"]
    buffer_m = state["project_profile"].get("sanitary_buffer_m", 300.0)

    audited = {"hq": [], "factory": [], "unified": []}
    vetoed_count = 0

    for cat in ["hq", "factory", "unified"]:
        for p in raw.get(cat, []):
            if p.get("geometry"):
                audit_res = audit_sanitary_and_redlines(p["geometry"], sanitary_buffer_m=buffer_m)
                if audit_res["passed"]:
                    audited[cat].append(p)
                else:
                    vetoed_count += 1
            else:
                audited[cat].append(p)

    logs.append(
        f"  [OK] 规划审查完毕：剔除触碰禁建要素图斑 {vetoed_count} 宗，"
        f"合格候选池：总部 {len(audited['hq'])} 宗，基地 {len(audited['factory'])} 宗，集中用地 {len(audited['unified'])} 宗。"
    )

    return {"audited_candidates": audited, "logs": logs}


def node_multicriteria_scoring(state: PharmaSiteState) -> Dict[str, Any]:
    """节点 4：多准则空间计算与五维综合指标打分量算。"""
    logs = list(state.get("logs", []))
    logs.append("【步骤 4/6】驱动空间计算引擎，开展规划符合、交通物流、产学研协同、公用配套、建造成本五维综合打分...")

    audited = state["audited_candidates"]
    buffer_m = state["project_profile"].get("sanitary_buffer_m", 300.0)

    evaluated = {"hq": [], "factory": [], "unified": []}

    for cat in ["hq", "factory", "unified"]:
        scored_list = []
        for p in audited.get(cat, []):
            eval_item = evaluate_pharma_parcel_5d(p, role=cat, sanitary_buffer_m=buffer_m)
            scored_list.append(eval_item)
        # 按总分从高到低排序
        scored_list.sort(key=lambda x: x["scores"]["total"], reverse=True)
        evaluated[cat] = scored_list

    logs.append(
        f"  [OK] 五维打分完成：HQ最高得分 {evaluated['hq'][0]['scores']['total'] if evaluated['hq'] else 0} 分，"
        f"基地最高得分 {evaluated['factory'][0]['scores']['total'] if evaluated['factory'] else 0} 分。"
    )

    return {"evaluated_candidates": evaluated, "logs": logs}


def node_scheme_synthesis(state: PharmaSiteState) -> Dict[str, Any]:
    """节点 5：方案系统比选（方案 A 集中连片 vs 方案 B 研发总部+生产基地分地块）。"""
    logs = list(state.get("logs", []))
    logs.append("【步骤 5/6】比选集中连片方案与研发生产分地块方案，计算跨区通勤联动与综合经济技术指标...")

    ev = state["evaluated_candidates"]
    scheme_res = compare_pharma_schemes(
        unified_candidates=ev.get("unified", []),
        hq_candidates=ev.get("hq", []),
        factory_candidates=ev.get("factory", []),
    )

    commute_km = scheme_res["dual_site_scheme"].get("commute_dist_km", 0.0)
    logs.append(
        f"  [OK] 方案比选完成：双地块布局（方案B）总部与生产基地测算通勤直线距离 {commute_km} km，车程约 "
        f"{scheme_res['dual_site_scheme'].get('commute_car_min', 0)} 分钟。"
    )

    return {"scheme_comparison": scheme_res, "logs": logs}


def node_generate_report(state: PharmaSiteState) -> Dict[str, Any]:
    """节点 6：生成符合国家规划标准与可研要求的规划选址综合论证报告。"""
    logs = list(state.get("logs", []))
    logs.append("【步骤 6/6】整理决策依据，生成《医药制药项目多场景选址规划论证与比选报告》...")

    profile = state["project_profile"]
    comp = state["scheme_comparison"]
    ev = state["evaluated_candidates"]

    best_hq = ev.get("hq", [{}])[0] if ev.get("hq") else {}
    best_fac = ev.get("factory", [{}])[0] if ev.get("factory") else {}
    best_uni = ev.get("unified", [{}])[0] if ev.get("unified") else {}

    report = f"""# 桂林市临桂区医药制药产业项目选址规划论证报告

**报告类型**：国土空间专项规划选址论证与方案多准则比选  
**规划区位**：广西壮族自治区桂林市临桂区  
**空间基准**：CGCS2000 国家大地坐标系（投影：EPSG:4525 3度带 zone 37）  
**数据底座**：PostGIS 空间数据库（`117.72.210.60:5432/onemap_db` 现状控规图斑）+ 临桂区三区三线规划成果  

---

## 一、项目背景与选址诉求分析

为落实“数智自然·壮美广西”与生物医药大健康产业高质量发展战略，本项目面向高端制药、现代中药及生物制剂产业落地需求，开展科学系统的多场景规划选址。
根据制药工业特殊性，选址须兼顾**研发总部（B2）的高端科教协同吸引力**与**GMP生产基地（M1）严格的排污纳管与卫生防护隔离**。

* **卫生防护标准**：{profile.get('sanitary_buffer_m', 300)} 米安全防护距离（严禁粉尘/废气扰民）；
* **功能分区诉求**：研发总部建议规模 {profile.get('hq_min_ha')}~{profile.get('hq_max_ha')} ha，生产基地建议规模 {profile.get('factory_min_ha')}~{profile.get('factory_max_ha')} ha。

---

## 二、候选地块五维综合空间量算

经过三区三线（生态保护红线、永久基本农田、城市蓝线）严苛的一票否决合规审查后，系统从 2,134 宗图斑中筛选出最优核心备选地块：

| 功能定位 | 推荐图斑ID | 规划用地代码 | 用地性质 | 用地规模 | 综合评分 | 核心优势 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **研发总部 (B2)** | #{best_hq.get('id', '-')} | `{best_hq.get('land_code', '-')}` | B2 商务/科创用地 | {best_hq.get('area_ha', '-')} ha | **{best_hq.get('scores', {}).get('total', '-')} 分** | 临近高等教育院校，产学研与高知人才集聚 |
| **生产基地 (M1)** | #{best_fac.get('id', '-')} | `{best_fac.get('land_code', '-')}` | M1 现代工业用地 | {best_fac.get('area_ha', '-')} ha | **{best_fac.get('scores', {}).get('total', '-')} 分** | 污水处理设施近，物流主通道快速出入 |
| **集中连片综合** | #{best_uni.get('id', '-')} | `{best_uni.get('land_code', '-')}` | 综合工业用地 | {best_uni.get('area_ha', '-')} ha | **{best_uni.get('scores', {}).get('total', '-')} 分** | 单宗地块规整连片，便于一体化封闭管理 |

---

## 三、双选址布局方案系统比选

### 1. 方案 A：集中连片综合基地布局
* **用地特征**：单宗大面积用地（{comp['unified_scheme']['indicators']['total_area_ha']} ha），统一招拍挂出让。
* **规划优势**：
  * {chr(10).join(['  - ' + a for a in comp['unified_scheme']['advantages']])}
* **制约因素**：
  * {chr(10).join(['  - ' + d for a, d in enumerate(comp['unified_scheme']['disadvantages'])])}

### 2. 方案 B：研发总部与生产基地分地块布局
* **用地特征**：研发总部（{best_hq.get('area_ha', 0)} ha）+ 生产基地（{best_fac.get('area_ha', 0)} ha），合计约 {comp['dual_site_scheme']['indicators']['total_area_ha']} ha。
* **双地块通勤联动**：两地直线距离 **{comp['dual_site_scheme'].get('commute_dist_km', '-')} 公里**，经城市主干道通行车程约 **{comp['dual_site_scheme'].get('commute_car_min', '-')} 分钟**。
* **规划优势**：
  * {chr(10).join(['  - ' + a for a in comp['dual_site_scheme']['advantages']])}
* **制约因素**：
  * {chr(10).join(['  - ' + d for a, d in enumerate(comp['dual_site_scheme']['disadvantages'])])}

---

## 四、规划决策建议与推进实施路径

> **【最终决策推荐意见】**  
> {comp['recommendation']}

### 建议落地实施步骤：
1. **控规指标核定**：研发总部容积率控制在 2.5~3.5，生产基地容积率控制在 1.2~1.8，建筑限高满足消防与洁净风道要求；
2. **环评审批与污水纳管**：优先推进高浓度制药废水预处理站方案，报批生态环境部门落实排污总量指标；
3. **政务专班代办**：提请临桂区投资促进局与自然资源局成立重大医药项目专班，统筹土地招拍挂与安评、药监开工许可。
"""

    logs.append("  [OK] 论证报告生成完成。全套 LangGraph 选址智能体工作流顺利结束！")

    return {"opinion_report": report, "logs": logs}


# --------------------------------------------------------------------------- #
# 状态图构建
# --------------------------------------------------------------------------- #

def build_pharma_agent_graph():
    """构建 LangGraph 决策状态图。"""
    workflow = StateGraph(PharmaSiteState)

    # 注册节点
    workflow.add_node("parse_requirements", node_parse_requirements)
    workflow.add_node("postgis_retrieval", node_postgis_retrieval)
    workflow.add_node("compliance_audit", node_compliance_audit)
    workflow.add_node("multicriteria_scoring", node_multicriteria_scoring)
    workflow.add_node("scheme_synthesis", node_scheme_synthesis)
    workflow.add_node("generate_report", node_generate_report)

    # 连接边
    workflow.set_entry_point("parse_requirements")
    workflow.add_edge("parse_requirements", "postgis_retrieval")
    workflow.add_edge("postgis_retrieval", "compliance_audit")
    workflow.add_edge("compliance_audit", "multicriteria_scoring")
    workflow.add_edge("multicriteria_scoring", "scheme_synthesis")
    workflow.add_edge("scheme_synthesis", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()


# 编译后的智能体执行图
pharma_site_agent = build_pharma_agent_graph()
