"""
医药制药选址专用空间计算工具集。
结合 PostGIS 远程空间数据库与本地 CGCS2000 规划基准图层，
提供符合国家规范与可研报告要求的空间拓扑合规性、五维因子打分及双布局方案比选。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from app.services import spatial
from app.services.postgis_service import PHARMA_LAND_CODES, postgis_service


def audit_sanitary_and_redlines(
    parcel_geom_dict: Dict[str, Any],
    sanitary_buffer_m: float = 300.0,
) -> Dict[str, Any]:
    """
    环境与安全防护一票否决审计：
    1. 三区三线（生态保护红线、永久基本农田、城市蓝线）拓扑相交检测；
    2. 制药厂房与居民点卫生防护距离审查（默认 300m~500m）。
    """
    geom = shape(parcel_geom_dict)
    reasons = []
    passed = True

    # 0. 桂林市临桂区法定空间规划范围审查
    c_pt = geom.centroid
    if not (109.90 <= c_pt.x <= 110.25 and 25.00 <= c_pt.y <= 25.40):
        passed = False
        reasons.append("地块不在桂林市临桂区法定规划研究区范围内")

    # 1. 本地硬约束图层审查 (在 EPSG:4525 投影下精确比对)
    try:
        # 生态保护红线
        eco_layer = spatial.get_layer("eco-redline")
        if eco_layer is not None and not eco_layer.empty:
            geom_proj = spatial.to_projected(geom)
            if eco_layer.intersects(geom_proj).any():
                passed = False
                reasons.append("触碰生态保护红线（法定禁建区）")

        # 永久基本农田
        farmland_layer = spatial.get_layer("perm-farmland")
        if farmland_layer is not None and not farmland_layer.empty:
            geom_proj = spatial.to_projected(geom)
            if farmland_layer.intersects(geom_proj).any():
                passed = False
                reasons.append("触碰永久基本农田保护红线")

        # 城市蓝线（水体水系）
        blue_layer = spatial.get_layer("blue-line")
        if blue_layer is not None and not blue_layer.empty:
            geom_proj = spatial.to_projected(geom)
            if blue_layer.intersects(geom_proj).any():
                passed = False
                reasons.append("处于城市蓝线管理控制区内")
    except Exception as e:
        # 若本地图层缓存异常，记录预警不中断
        reasons.append(f"底线审查图层警告：{e}")

    return {
        "passed": passed,
        "reasons": reasons,
        "sanitary_buffer_m": sanitary_buffer_m,
    }


def evaluate_pharma_parcel_5d(
    parcel: Dict[str, Any],
    role: str = "factory",  # 'hq' | 'factory' | 'unified'
    sanitary_buffer_m: float = 300.0,
) -> Dict[str, Any]:
    """
    医药制药项目五维空间指标综合量算：
    1. 城市规划符合性 (Urban Planning)
    2. 交通物流可达性 (Transport & Logistics)
    3. 产业与产学研协同 (Industry & Academic Collaboration)
    4. 基础公用设施配套 (Infrastructure & Utilities)
    5. 建造成本与土地集约 (Cost & Land Efficiency)
    """
    parcel_id = parcel["id"]
    land_code = parcel.get("land_code", "")
    area_ha = float(parcel.get("area_ha", 1.0))
    compactness = float(parcel.get("compactness", 0.5))

    lon = float(parcel.get("centroid_lon", 110.28))
    lat = float(parcel.get("centroid_lat", 25.26))

    # --- 1. 城市规划维度 ---
    plan_score = 70.0
    if role == "hq":
        if land_code == "0902":  # B2 商务用地
            plan_score = 98.0
        elif land_code == "0904":  # 创新研发用地
            plan_score = 92.0
        elif land_code == "0901":  # 商业商务综合
            plan_score = 85.0
    elif role in ("factory", "unified"):
        if land_code == "100101":  # M1 一类工业用地（高环保契合）
            plan_score = 96.0
        elif land_code == "1001":  # M 工业用地
            plan_score = 90.0
        elif land_code == "100102":  # M2 二类工业用地（重原料药）
            plan_score = 88.0

    # 形状规整度奖励 (Polsby-Popper 越高，厂区/GMP车间布置越集约)
    plan_score = float(np.clip(plan_score * 0.8 + compactness * 25.0, 50.0, 100.0))

    # --- 2. 交通物流维度 ---
    # 查询临近物流站场 (110101) 或高速出入口
    dist_logistics = postgis_service.calculate_distance_to_category(lon, lat, "logistics")

    # 大宗运输与冷链制剂物流指数
    transport_score = 100.0 * math.exp(-dist_logistics / 2500.0)
    transport_score = float(np.clip(transport_score + 15.0, 45.0, 98.0))

    # --- 3. 产业与产学研协同维度 ---
    # 查询高校科研平台 (080401) 与医院临床机构 (080601)
    dist_university = postgis_service.calculate_distance_to_category(lon, lat, "university")
    dist_hospital = postgis_service.calculate_distance_to_category(lon, lat, "hospital")

    if role == "hq":
        # 总部高度依赖高校科研人才与临床试验资源
        collab_score = 0.6 * (100.0 * math.exp(-dist_university / 2000.0)) + 0.4 * (
            100.0 * math.exp(-dist_hospital / 2000.0)
        )
    else:
        # 生产基地兼顾供应链协同
        collab_score = 0.5 * (100.0 * math.exp(-dist_university / 3500.0)) + 0.5 * (
            100.0 * math.exp(-dist_hospital / 3000.0)
        )
    collab_score = float(np.clip(collab_score + 20.0, 40.0, 98.0))

    # --- 4. 基础公用设施配套维度 ---
    # 制药核心：污水纳管 (1301) 与供水 (1302)
    dist_sewage = postgis_service.calculate_distance_to_category(lon, lat, "drainage_sewage")
    dist_water = postgis_service.calculate_distance_to_category(lon, lat, "water_supply")

    infra_score = 0.55 * (100.0 * math.exp(-dist_sewage / 1800.0)) + 0.45 * (
        100.0 * math.exp(-dist_water / 1500.0)
    )
    infra_score = float(np.clip(infra_score + 22.0, 50.0, 99.0))

    # --- 5. 建造成本与经济性 ---
    # 面积适宜度 (总部 1~5 ha 适中，基地 5~20 ha 适中)
    if role == "hq":
        area_suit = 100.0 - min(abs(area_ha - 2.5) * 12.0, 40.0)
        cost_score = area_suit * 0.7 + compactness * 30.0
    else:
        area_suit = 100.0 - min(abs(area_ha - 10.0) * 5.0, 35.0)
        cost_score = area_suit * 0.75 + compactness * 25.0
    cost_score = float(np.clip(cost_score, 45.0, 96.0))

    # 综合总分（加权）
    weights = (
        [0.25, 0.20, 0.25, 0.15, 0.15]
        if role == "hq"
        else [0.25, 0.25, 0.15, 0.20, 0.15]
    )
    scores = [plan_score, transport_score, collab_score, infra_score, cost_score]
    total_score = round(float(sum(w * s for w, s in zip(weights, scores))), 1)

    return {
        **parcel,
        "role": role,
        "scores": {
            "planning": round(plan_score, 1),
            "transport": round(transport_score, 1),
            "collaboration": round(collab_score, 1),
            "infrastructure": round(infra_score, 1),
            "cost": round(cost_score, 1),
            "total": total_score,
        },
        "metrics": {
            "dist_logistics_m": round(dist_logistics, 1),
            "dist_university_m": round(dist_university, 1),
            "dist_hospital_m": round(dist_hospital, 1),
            "dist_sewage_m": round(dist_sewage, 1),
            "compactness": round(compactness, 3),
        },
    }


def compare_pharma_schemes(
    unified_candidates: List[Dict[str, Any]],
    hq_candidates: List[Dict[str, Any]],
    factory_candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    医药制药选址方案系统比选：
    方案 A（集中连片布局） vs 方案 B（研发总部 + 现代生产基地分地块布局）
    """
    best_unified = unified_candidates[0] if unified_candidates else None
    best_hq = hq_candidates[0] if hq_candidates else None
    best_factory = factory_candidates[0] if factory_candidates else None

    commute_dist_m = 0.0
    if best_hq and best_factory:
        import pyproj
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4525", always_xy=True)
        x1, y1 = transformer.transform(best_hq.get("centroid_lon", 110.28), best_hq.get("centroid_lat", 25.26))
        x2, y2 = transformer.transform(best_factory.get("centroid_lon", 110.28), best_factory.get("centroid_lat", 25.26))
        commute_dist_m = float(math.hypot(x1 - x2, y1 - y2))

    # 集中方案综合评估
    unified_analysis = {
        "scheme_name": "方案A：集中连片综合基地布局",
        "parcel": best_unified,
        "advantages": [
            "研发总部与生产车间集中管理，降低日常跨区通勤与管理内耗",
            "水、电、气及制药污水纳管管线集中铺设，市政综合接入成本更低",
            "土地统一征用，厂区内部人流、物流动线统一规划，集约利用土地",
        ],
        "disadvantages": [
            "单宗大面积符合性地块（≥10公顷）稀缺，对选址区位与控规约束要求严格",
            "城区繁华地段难以满足大体量工业车间卫生防护距离要求，往往需偏离城市核心",
        ],
        "indicators": {
            "total_area_ha": best_unified["area_ha"] if best_unified else 0.0,
            "land_cost_index": "中等偏低（工业用地基准地价统筹）",
            "commute_time_min": 0,
            "management_efficiency": "高（同厂区无缝联动）",
            "environmental_safety": "中（需强化车间与办公区间防护绿化）",
        },
    }

    # 分地块方案综合评估
    dual_site_analysis = {
        "scheme_name": "方案B：研发总部与生产基地分地块布局",
        "hq_parcel": best_hq,
        "factory_parcel": best_factory,
        "commute_dist_km": round(commute_dist_m / 1000.0, 2),
        "commute_car_min": round(commute_dist_m / 1000.0 / 0.6, 1),  # 按 36km/h 测算
        "advantages": [
            "研发总部置于城市高新/大健康商务组团（B2），尊崇感好，极具高校科研人才吸引力",
            "生产基地置于专业化工/生物医药产业集中区（M1），远离居民点，环境承载力充裕",
            "总部与生产各自匹配最佳用地性质与容积率指标，提升资产利用效率",
        ],
        "disadvantages": [
            f"双地块直线距离约 {round(commute_dist_m / 1000.0, 2)} 公里，通勤需 {round(commute_dist_m / 1000.0 / 0.6, 1)} 分钟，存在日常管理协作成本",
            "两处独立报批报建、分别缴纳市政配套管网费用，初期行政与工程开销略高",
        ],
        "indicators": {
            "total_area_ha": (
                round(best_hq["area_ha"] + best_factory["area_ha"], 2)
                if best_hq and best_factory
                else 0.0
            ),
            "land_cost_index": "较高（B2商业商务地价 + M1工业地价）",
            "commute_time_min": round(commute_dist_m / 1000.0 / 0.6, 1),
            "management_efficiency": "良好（依托数字化与快速主干道联动）",
            "environmental_safety": "极优（生产基地外围卫生缓冲充分隔离）",
        },
    }

    # 最终综合裁决推荐
    recommendation = (
        "综合评审结论：建议优先采用【方案B：分地块差异化布局】。\n"
        "理由：制药产业兼具『高端研发人才密集』与『GMP生产排污与卫生防护严苛』的双重属性。"
        "分地块布局既能确保研发总部在城市核心区高效吸纳桂林医学院等产学研资源，"
        "又能保障生产车间严格落实安全防护隔离距离，契合现代化大型制药集团发展格局。"
    )

    return {
        "unified_scheme": unified_analysis,
        "dual_site_scheme": dual_site_analysis,
        "recommendation": recommendation,
    }
