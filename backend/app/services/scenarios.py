"""
选址场景模板（S1–S5）。

设计原则：一套引擎，多套参数模板。新增场景 = 新增一个模板，不改算法代码。
字段说明：
  constraints : 硬约束，布尔一票否决。buffer_m 为缓冲距离（米），0 表示几何本身即为禁区。
  factors     : 软因子，direction=+1 越大越好，-1 越小越好，2 为区间型。
  weights_ahp : AHP 主观权重，同一层级内和需为 1。
"""
from fastapi import HTTPException

SCENARIOS: dict[str, dict] = {
    "S1": {
        "id": "S1",
        "name": "建设项目用地选址",
        "category": "要素保障",
        "description": "为拟建项目寻找合规、集约、低成本的可用地块。主打场景，9-15 前必须完整可跑。",
        "constraints": [
            {"id": "prime_farmland", "name": "永久基本农田", "buffer_m": 0, "required": True},
            {"id": "eco_redline", "name": "生态保护红线", "buffer_m": 0, "required": True},
            {"id": "river_range", "name": "河湖管理范围", "buffer_m": 30, "required": True},
            {"id": "geohazard", "name": "地质灾害高易发区", "buffer_m": 100, "required": True},
            {"id": "builtup", "name": "已建设用地", "buffer_m": 0, "required": True},
            {"id": "road_protect", "name": "高速/铁路安全保护距离", "buffer_m": 100, "required": False},
            {"id": "cultural_relic", "name": "文物保护单位", "buffer_m": 50, "required": False},
        ],
        "factors": [
            {"id": "slope", "name": "坡度", "direction": -1, "unit": "度"},
            {"id": "dist_road", "name": "距现状道路距离", "direction": -1, "unit": "米"},
            {"id": "in_udb", "name": "位于城镇开发边界内", "direction": 1, "unit": "0/1"},
            {"id": "parcel_shape", "name": "地块规整度", "direction": 1, "unit": "0-1"},
            {"id": "building_density", "name": "现状建筑密度（拆迁成本代理）", "direction": -1, "unit": "0-1"},
        ],
        "weights_ahp": {
            "slope": 0.25, "dist_road": 0.25, "in_udb": 0.25,
            "parcel_shape": 0.15, "building_density": 0.10,
        },
    },
    "S2": {
        "id": "S2",
        "name": "公共服务设施选址",
        "category": "格局优化",
        "description": "学校/医院/养老/消防等设施，目标为覆盖最大化与公平性，输出点位与服务范围。",
        "constraints": [
            {"id": "prime_farmland", "name": "永久基本农田", "buffer_m": 0, "required": True},
            {"id": "eco_redline", "name": "生态保护红线", "buffer_m": 0, "required": True},
            {"id": "geohazard", "name": "地质灾害高易发区", "buffer_m": 100, "required": True},
            {"id": "pollution_source", "name": "噪声/污染源", "buffer_m": 200, "required": True},
        ],
        "factors": [
            {"id": "pop_density", "name": "人口密度", "direction": 1, "unit": "人/km²"},
            {"id": "service_gap", "name": "同类设施服务缺口", "direction": 1, "unit": "0-1"},
            {"id": "accessibility", "name": "路网可达性", "direction": 1, "unit": "0-1"},
            {"id": "dist_transit", "name": "距公交站点距离", "direction": -1, "unit": "米"},
            {"id": "dist_same_type", "name": "距同类设施距离（避免过度集中）", "direction": 2, "unit": "米"},
        ],
        "weights_ahp": {
            "pop_density": 0.30, "service_gap": 0.25, "accessibility": 0.20,
            "dist_transit": 0.15, "dist_same_type": 0.10,
        },
    },
    "S3": {
        "id": "S3",
        "name": "新能源与充换电设施选址",
        "category": "格局优化",
        "description": "光伏/风电/储能/充电站落位，输出可装机容量估算。",
        "constraints": [
            {"id": "eco_redline", "name": "生态保护红线", "buffer_m": 0, "required": True},
            {"id": "prime_farmland", "name": "永久基本农田", "buffer_m": 0, "required": True},
            {"id": "flood_area", "name": "行洪区", "buffer_m": 0, "required": True},
            {"id": "airport_clear", "name": "机场净空/限高区", "buffer_m": 0, "required": True},
        ],
        "factors": [
            {"id": "solar_wind", "name": "辐射量/风功率密度", "direction": 1, "unit": "kWh/m²·a"},
            {"id": "aspect", "name": "坡向适宜性", "direction": 1, "unit": "0-1"},
            {"id": "slope", "name": "坡度", "direction": -1, "unit": "度"},
            {"id": "dist_grid", "name": "并网点距离", "direction": -1, "unit": "米"},
            {"id": "dist_road", "name": "道路可达性", "direction": -1, "unit": "米"},
        ],
        "weights_ahp": {
            "solar_wind": 0.35, "aspect": 0.15, "slope": 0.15,
            "dist_grid": 0.20, "dist_road": 0.15,
        },
    },
    "S4": {
        "id": "S4",
        "name": "矿业权/砂石土矿选址",
        "category": "矿业发展",
        "description": "资源禀赋与生态约束的平衡，输出候选区块与环境敏感点核查表。",
        "constraints": [
            {"id": "eco_redline", "name": "生态保护红线", "buffer_m": 0, "required": True},
            {"id": "prime_farmland", "name": "永久基本农田", "buffer_m": 0, "required": True},
            {"id": "udb", "name": "城镇开发边界", "buffer_m": 0, "required": True},
            {"id": "water_source", "name": "饮用水源保护区", "buffer_m": 0, "required": True},
            {"id": "residential", "name": "居民点安全距离", "buffer_m": 300, "required": True},
        ],
        "factors": [
            {"id": "resource_potential", "name": "资源潜力", "direction": 1, "unit": "0-1"},
            {"id": "overburden", "name": "覆盖层厚度", "direction": -1, "unit": "米"},
            {"id": "dist_road", "name": "运输距离", "direction": -1, "unit": "米"},
            {"id": "restore_difficulty", "name": "生态修复难度", "direction": -1, "unit": "0-1"},
        ],
        "weights_ahp": {
            "resource_potential": 0.40, "overburden": 0.15,
            "dist_road": 0.25, "restore_difficulty": 0.20,
        },
    },
    "S5": {
        "id": "S5",
        "name": "生态修复/补充耕地选址",
        "category": "生态修复/耕地保护",
        "description": "找出最值得修、最容易修、修完效益最大的地块，输出修复优先序。",
        "constraints": [
            {"id": "eco_redline_core", "name": "生态保护红线核心区", "buffer_m": 0, "required": True},
            {"id": "primary_forest", "name": "原生林草", "buffer_m": 0, "required": True},
        ],
        "factors": [
            {"id": "degradation", "name": "生态退化程度", "direction": 1, "unit": "0-1"},
            {"id": "soil_pollution", "name": "土壤污染程度", "direction": 1, "unit": "0-1"},
            {"id": "contiguity", "name": "集中连片度", "direction": 1, "unit": "0-1"},
            {"id": "slope_treatable", "name": "坡度可治理性", "direction": 1, "unit": "0-1"},
            {"id": "water_availability", "name": "水源保障", "direction": 1, "unit": "0-1"},
            {"id": "corridor_link", "name": "生态廊道连通性", "direction": 1, "unit": "0-1"},
        ],
        "weights_ahp": {
            "degradation": 0.25, "soil_pollution": 0.15, "contiguity": 0.20,
            "slope_treatable": 0.15, "water_availability": 0.10, "corridor_link": 0.15,
        },
    },
}


def list_scenarios() -> list[dict]:
    return [
        {"id": s["id"], "name": s["name"], "category": s["category"],
         "description": s["description"]}
        for s in SCENARIOS.values()
    ]


def get_scenario(scenario_id: str) -> dict:
    s = SCENARIOS.get(scenario_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"未找到场景 {scenario_id}")
    return s
