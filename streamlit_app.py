"""
国土AI竞赛｜医药制药多场景智慧选址系统 (Streamlit + Folium + LangGraph + PostGIS)

技术栈架构：
  - 智能体框架：LangGraph (StateGraph 多步骤循环决策流)
  - 空间数据库：PostgreSQL 15 + PostGIS 3.4 (117.72.210.60:5432/onemap_db)
  - 空间数据计算：GeoPandas + Shapely + PyProj + Rasterio (EPSG:4525 投影高精度量算)
  - 地图可视化：Streamlit + Folium + branca (图斑高亮、卫生防护圈、通勤连线)
  - 大模型底座：DeepSeek / OpenAI 兼容接口 + 注册规划师规则引擎降级

启动方式：
  streamlit run streamlit_app.py
"""
import json
import math
import sys
from pathlib import Path

import folium
import streamlit as st
from folium import plugins
from streamlit_folium import st_folium

# 引入 backend 模块路径
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.agent.langgraph_agent import pharma_site_agent
from app.services.postgis_service import PHARMA_LAND_CODES, postgis_service

# --------------------------------------------------------------------------- #
# 本地 GeoJSON 业务图层高速缓存加载器
# --------------------------------------------------------------------------- #
@st.cache_data
def get_geojson_layer_data(layer_id: str):
    """缓存加载本地已处理好的 18 个法定规划 GeoJSON 矢量图层。"""
    p = ROOT_DIR / "data" / "processed" / "geojson" / f"{layer_id}.geojson"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


# --------------------------------------------------------------------------- #
# 页面基础配置
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="国土AI·医药制药多场景智慧选址系统",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS 样式（现代简约科技风）
st.markdown(
    """
<style>
    .main-header {
        font-size: 26px;
        font-weight: 700;
        color: #16222E;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .sub-header {
        font-size: 14px;
        color: #5A6A80;
        margin-bottom: 18px;
    }
    .kpi-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 18px;
        text-align: left;
    }
    .kpi-title {
        font-size: 12px;
        color: #64748B;
        font-weight: 500;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 700;
        color: #1E293B;
        margin-top: 4px;
    }
    .kpi-tag {
        font-size: 11px;
        color: #10B981;
        font-weight: 600;
    }
    .badge-postgis {
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        color: #065F46;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        display: inline-block;
        font-weight: 600;
    }
    .stButton>button {
        background-color: #1C7D8C !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# 侧边栏配置
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### 🧬 选址决策控制台")

    # 1. 空间数据库状态监控
    pg_health = postgis_service.health_check()
    if pg_health["status"] == "connected":
        st.markdown(
            f'<div class="badge-postgis">🟢 PostGIS 在线 · {pg_health["total_tuban"]} 图斑</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"主机: `{pg_health['host']}` 库: `{pg_health['database']}`")
    else:
        st.error(f"PostGIS 连接受阻，系统已启用本地法定规划缓存降级模式。")

    st.markdown("---")

    # 2. 选址场景快捷预设
    st.markdown("#### 🎯 选址需求配置")
    preset_choice = st.selectbox(
        "快速载入预设场景：",
        [
            "【综合型】研发总部+现代制药基地（分地块与集中比选）",
            "【高环保型】原料药及发酵合成基地（500m强卫生防护）",
            "【科创型】现代生物医药临床研发中心（紧临高校医院）",
        ],
    )

    default_queries = {
        "【综合型】研发总部+现代制药基地（分地块与集中比选）": "拟在桂林临桂区建设大型生物医药项目，包含B2研发总部与M1洁净生产基地，要求临近高校产学研平台并靠近货运干道，需开展集中连片与分地块方案比选。",
        "【高环保型】原料药及发酵合成基地（500m强卫生防护）": "拟选址原料药与现代中药制剂生产基地，需严格落实500米卫生防护距离，规避居民敏感点，优先靠近污水管网与给水主管线。",
        "【科创型】现代生物医药临床研发中心（紧临高校医院）": "重点布局高端生物医药研发总部与创新孵化平台，选用B2商务用地，要求高度协同高等医学教育院校与综合医院临床试验资源。",
    }

    user_query = st.text_area(
        "自然语言选址意图：",
        value=default_queries[preset_choice],
        height=100,
    )

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        hq_size = st.slider("总部面积 (ha)", 0.5, 8.0, (1.0, 5.0), step=0.5)
    with col_h2:
        factory_size = st.slider("基地面积 (ha)", 2.0, 30.0, (5.0, 20.0), step=1.0)

    sanitary_buffer = st.radio(
        "卫生安全防护距离要求：",
        options=[300, 500],
        index=1 if "500" in preset_choice else 0,
        format_func=lambda x: f"{x} 米 ({'制剂/洁净厂房' if x==300 else '原料药/发酵车间'})",
    )

    scheme_preference = st.radio(
        "布局方案比选模式：",
        options=["全部系统比选 (方案A集中 vs 方案B分地块)", "优先方案A (集中连片布局)", "优先方案B (研发生产分地块)"],
        index=0,
    )

    run_agent_btn = st.button("🚀 启动 LangGraph 选址智能体", use_container_width=True)

    st.markdown("---")
    st.markdown(
        "<div style='font-size:12px;color:#8A94A6;'>技术标准：GB/T 50137-2011<br>空间坐标：CGCS2000 / EPSG:4525<br>主办赛题：自然资源厅·数智场景</div>",
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
# 主工作台
# --------------------------------------------------------------------------- #
st.markdown('<div class="main-header">🧬 国土AI · 医药制药多场景智慧选址系统</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">驱动 LangGraph 状态图决策流 · 融合 PostGIS 空间图斑 · 三区三线一票否决与五维空间多准则评价</div>',
    unsafe_allow_html=True,
)

# 会话状态缓存
if "agent_state" not in st.session_state:
    st.session_state["agent_state"] = None

# 执行 LangGraph 智能体
if run_agent_btn or st.session_state["agent_state"] is None:
    with st.spinner("🤖 LangGraph 空间智能体正在执行 6 阶段决策流（检索 PostGIS、底线审查、五维打分与双方案比选）..."):
        init_state = {
            "user_query": user_query,
            "project_profile": {
                "hq_min_ha": hq_size[0],
                "hq_max_ha": hq_size[1],
                "factory_min_ha": factory_size[0],
                "factory_max_ha": factory_size[1],
                "sanitary_buffer_m": float(sanitary_buffer),
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
        st.session_state["agent_state"] = final_state

agent_res = st.session_state["agent_state"]
evaluated = agent_res.get("evaluated_candidates", {})
comparison = agent_res.get("scheme_comparison", {})

best_hq = evaluated.get("hq", [{}])[0] if evaluated.get("hq") else None
best_fac = evaluated.get("factory", [{}])[0] if evaluated.get("factory") else None
best_uni = evaluated.get("unified", [{}])[0] if evaluated.get("unified") else None

# 1. 顶栏指标卡片
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-title">PostGIS 合格候选地块</div>
        <div class="kpi-value">{len(evaluated.get('hq',[])) + len(evaluated.get('factory',[]))} <span style="font-size:14px;color:#64748B;">宗</span></div>
        <div class="kpi-tag">✓ 三区三线已合规过滤</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-title">推荐研发总部 (B2商务)</div>
        <div class="kpi-value">#{best_hq.get('id', '-')} <span style="font-size:14px;color:#1C7D8C;">{best_hq.get('scores',{}).get('total', '-')} 分</span></div>
        <div class="kpi-tag">用地: {best_hq.get('area_ha', '-')} ha · 邻近高校</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-title">推荐生产基地 (M1工业)</div>
        <div class="kpi-value">#{best_fac.get('id', '-')} <span style="font-size:14px;color:#E67E22;">{best_fac.get('scores',{}).get('total', '-')} 分</span></div>
        <div class="kpi-tag">用地: {best_fac.get('area_ha', '-')} ha · 污水纳管近</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with k4:
    commute_km = comparison.get("dual_site_scheme", {}).get("commute_dist_km", 0.0)
    commute_min = comparison.get("dual_site_scheme", {}).get("commute_car_min", 0.0)
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-title">双地块通勤联动指标</div>
        <div class="kpi-value">{commute_km} <span style="font-size:14px;color:#64748B;">km</span></div>
        <div class="kpi-tag">🚗 快速路通勤约 {commute_min} 分钟</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# 2. 地图展示与决策面板
tab_map, tab_comparison, tab_report, tab_agent_log = st.tabs(
    ["🗺️ 空间选址一张图", "⚖️ 集中连片 vs 分地块方案比选", "📑 规划论证报告", "🤖 LangGraph 决策执行流"]
)

with tab_map:
    st.markdown("#### 📍 医药制药候选地块空间分布与拓扑联动")

    with st.expander("🗂️ 18个国土空间规划业务图层管理（点、线、面要素库展示说明）", expanded=False):
        st.markdown(
            "系统内置桂林临桂区全套 CGCS2000 法定规划图层（已转 EPSG:4326/4525），全部挂载至地图图层树。您可在地图右上角的 **图层控制器** 中自由勾选显示/隐藏任何图层："
        )
        c_l1, c_l2, c_l3 = st.columns(3)
        with c_l1:
            st.markdown("""
            **🛑 底线管控（面/线）**
            * 🛑 生态保护红线 (`eco-redline`, 5 宗面)
            * 🌾 永久基本农田 (`perm-farmland`, 3544 宗面)
            * 💧 城市蓝线水域 (`blue-line`, 118 处线面)
            * 🟣 城镇开发边界 (`urban-boundary`, 1 圈控制线)
            * 🌲 城市绿线 (`green-line`, 304 宗面)
            * ⚡ 城市黄线市政 (`yellow-line`, 77 宗面)
            """)
        with c_l2:
            st.markdown("""
            **🏭 产业与用地底盘（面）**
            * 🏭 控规工业用地基底 (`regulated-industrial`, 145 宗地块)
            * 🏗️ 产业园区法定范围 (`industrial-park`, 4 处范围)
            * 🏢 工业配套市政用地 (`municipal-land`, 81 宗面)
            * 📋 总规工业用地 (`industrial-land`, 215 宗面)
            """)
        with c_l3:
            st.markdown("""
            **🛣️ 交通、公服与现状建设（点/线/面）**
            * 🛣️ 道路路网拓扑 (`road-network`, 4054 条线)
            * 🚗 高速出入口 (`highway-interchange`, 7 处点)
            * 🚛 货运枢纽场站 (`freight-station`, 17 处点)
            * 💼 生产性服务点位 (`prod-service-point`, 5 处点)
            * 🏢 生产性服务业集聚区 (`prod-service-area`, 11 处面)
            * 🏛️ 文物保护单位 (`cultural-relic`, 1 处点)
            * 🏘️ 现状建筑分布 (`current-building`, 7851 栋面)
            * 🏭 现状已开发工业用地 (`current-industrial-land`, 684 宗面)
            """)

    # 构建 Folium 地图
    # 默认居中临桂区 [25.26, 110.28]
    center_lat = 25.26
    center_lon = 110.28
    if best_hq and best_hq.get("centroid_lat"):
        center_lat = float(best_hq["centroid_lat"])
        center_lon = float(best_hq["centroid_lon"])

    # 构建 Folium 地图（默认采用国内秒开的高德与 ArcGIS 镜像，彻底解决 CartoDB 境外 CDN 握手超时白屏问题）
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=None,
        control_scale=True,
    )

    # 1. 高德矢量地图（默认首选，国内直连秒级加载，地名路网清晰）
    folium.TileLayer(
        tiles="http://wprd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}",
        attr="高德地图 (AutoNavi)",
        name="高德矢量地图 (国内秒开·默认)",
        overlay=False,
        control=True,
        show=True,
    ).add_to(m)

    # 2. 高德卫星影像底图
    folium.TileLayer(
        tiles="http://wprd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=6&x={x}&y={y}&z={z}",
        attr="高德影像 (AutoNavi)",
        name="高德卫星影像",
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    # 3. ArcGIS 遥感影像
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="ArcGIS World Imagery",
        name="ArcGIS 遥感影像",
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    # 4. CartoDB Positron 浅色底图（备用）
    folium.TileLayer(
        tiles="CartoDB positron",
        attr="CartoDB",
        name="CartoDB 极简底图 (备用)",
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    # ----------------------------------------------------------------------- #
    # 挂载 18 个国土空间规划业务图层（点、线、面要素库）
    # ----------------------------------------------------------------------- #
    # 1. 底线管控图层 (红线/农田/蓝线)
    eco_data = get_geojson_layer_data("eco-redline")
    if eco_data:
        eco_fg = folium.FeatureGroup(name="🛑 [底线] 生态保护红线 (5宗·面)", show=True)
        folium.GeoJson(
            eco_data,
            style_function=lambda x: {"color": "#E5484D", "fillColor": "#E5484D", "weight": 2.5, "fillOpacity": 0.45},
            tooltip="生态保护红线 (一票否决·严禁开发)"
        ).add_to(eco_fg)
        eco_fg.add_to(m)

    blue_data = get_geojson_layer_data("blue-line")
    if blue_data:
        blue_fg = folium.FeatureGroup(name="💧 [底线] 城市蓝线水域 (118处·面)", show=True)
        folium.GeoJson(
            blue_data,
            style_function=lambda x: {"color": "#1971C2", "fillColor": "#228BE6", "weight": 1.5, "fillOpacity": 0.4},
            tooltip="城市蓝线河湖水体管控区"
        ).add_to(blue_fg)
        blue_fg.add_to(m)

    farm_data = get_geojson_layer_data("perm-farmland")
    if farm_data:
        farm_fg = folium.FeatureGroup(name="🌾 [底线] 永久基本农田 (3544宗·面)", show=False)
        folium.GeoJson(
            farm_data,
            style_function=lambda x: {"color": "#5C940D", "fillColor": "#82C91E", "weight": 1, "fillOpacity": 0.35},
            tooltip="永久基本农田保护区"
        ).add_to(farm_fg)
        farm_fg.add_to(m)

    # 2. 规划控制线图层 (开发边界/绿线/黄线)
    ub_data = get_geojson_layer_data("urban-boundary")
    if ub_data:
        ub_fg = folium.FeatureGroup(name="🟣 [控制] 城镇开发边界 (1圈·线)", show=True)
        folium.GeoJson(
            ub_data,
            style_function=lambda x: {"color": "#7950F2", "weight": 3, "fill": False, "dashArray": "6,4"},
            tooltip="城镇开发边界线"
        ).add_to(ub_fg)
        ub_fg.add_to(m)

    green_data = get_geojson_layer_data("green-line")
    if green_data:
        green_fg = folium.FeatureGroup(name="🌲 [控制] 城市绿线 (304宗·面)", show=False)
        folium.GeoJson(
            green_data,
            style_function=lambda x: {"color": "#2B8A3E", "fillColor": "#2B8A3E", "weight": 1.2, "fillOpacity": 0.3},
            tooltip="城市绿线生态公园"
        ).add_to(green_fg)
        green_fg.add_to(m)

    yellow_data = get_geojson_layer_data("yellow-line")
    if yellow_data:
        yellow_fg = folium.FeatureGroup(name="⚡ [控制] 城市黄线市政走廊 (77宗·面)", show=False)
        folium.GeoJson(
            yellow_data,
            style_function=lambda x: {"color": "#E67700", "fillColor": "#FAB005", "weight": 1.5, "fillOpacity": 0.35},
            tooltip="城市黄线市政公用设施控制线"
        ).add_to(yellow_fg)
        yellow_fg.add_to(m)

    # 3. 产业与用地底盘
    park_data = get_geojson_layer_data("industrial-park")
    if park_data:
        park_fg = folium.FeatureGroup(name="🏗️ [产业] 产业园区法定边界 (4处·面)", show=True)
        folium.GeoJson(
            park_data,
            style_function=lambda x: {"color": "#0C8599", "fillColor": "#15AABF", "weight": 2.5, "fillOpacity": 0.15, "dashArray": "5,5"},
            tooltip="重点产业园区范围"
        ).add_to(park_fg)
        park_fg.add_to(m)

    reg_data = get_geojson_layer_data("regulated-industrial")
    if reg_data:
        reg_fg = folium.FeatureGroup(name="🏭 [产业] 控规工业用地基底 (145宗·面)", show=True)
        folium.GeoJson(
            reg_data,
            style_function=lambda x: {"color": "#3B5BDB", "fillColor": "#4C6EF5", "weight": 1.2, "fillOpacity": 0.25},
            tooltip="控规工业用地基础图斑"
        ).add_to(reg_fg)
        reg_fg.add_to(m)

    mun_data = get_geojson_layer_data("municipal-land")
    if mun_data:
        mun_fg = folium.FeatureGroup(name="🏢 [产业] 工业配套市政用地 (81宗·面)", show=True)
        folium.GeoJson(
            mun_data,
            style_function=lambda x: {"color": "#862E9C", "fillColor": "#AE3EC9", "weight": 1.5, "fillOpacity": 0.35},
            tooltip="供水/供电/污水处理设施用地"
        ).add_to(mun_fg)
        mun_fg.add_to(m)

    ind_data = get_geojson_layer_data("industrial-land")
    if ind_data:
        ind_fg = folium.FeatureGroup(name="📋 [产业] 总规工业用地 (215宗·面)", show=False)
        folium.GeoJson(
            ind_data,
            style_function=lambda x: {"color": "#495057", "fillColor": "#ADB5BD", "weight": 1, "fillOpacity": 0.2},
            tooltip="总规工业用地范围"
        ).add_to(ind_fg)
        ind_fg.add_to(m)

    # 4. 交通路网与物流枢纽节点 (线/点)
    road_data = get_geojson_layer_data("road-network")
    if road_data:
        road_fg = folium.FeatureGroup(name="🛣️ [交通] 道路路网拓扑 (4054条·线)", show=True)
        folium.GeoJson(
            road_data,
            style_function=lambda x: {"color": "#475569", "weight": 1.2, "opacity": 0.75},
            tooltip="城市主次干道路网"
        ).add_to(road_fg)
        road_fg.add_to(m)

    hw_data = get_geojson_layer_data("highway-interchange")
    if hw_data:
        hw_fg = folium.FeatureGroup(name="🚗 [交通] 高速公路出入口 (7处·点)", show=True)
        for f in hw_data.get("features", []):
            geom = f.get("geometry") or {}
            c = geom.get("coordinates")
            if geom.get("type") == "Point" and isinstance(c, (list, tuple)) and len(c) >= 2:
                folium.CircleMarker(
                    location=[c[1], c[0]],
                    radius=6,
                    color="#FFFFFF",
                    fill=True,
                    fill_color="#1E40AF",
                    fill_opacity=0.95,
                    weight=2,
                    tooltip=f"高速互通立交出入口: {f.get('properties', {}).get('Name', '高速互通')}"
                ).add_to(hw_fg)
        hw_fg.add_to(m)

    fs_data = get_geojson_layer_data("freight-station")
    if fs_data:
        fs_fg = folium.FeatureGroup(name="🚛 [交通] 货运物流枢纽站场 (17处·面)", show=True)
        folium.GeoJson(
            fs_data,
            style_function=lambda x: {"color": "#B45309", "fillColor": "#F59E0B", "weight": 1.5, "fillOpacity": 0.45},
            tooltip="货运物流枢纽站场"
        ).add_to(fs_fg)
        fs_fg.add_to(m)

    # 5. 公共服务设施 (点/面)
    psp_data = get_geojson_layer_data("prod-service-point")
    if psp_data:
        psp_fg = folium.FeatureGroup(name="💼 [公服] 生产性服务点位 (5处·点)", show=True)
        for f in psp_data.get("features", []):
            geom = f.get("geometry") or {}
            c = geom.get("coordinates")
            if geom.get("type") == "Point" and isinstance(c, (list, tuple)) and len(c) >= 2:
                folium.CircleMarker(
                    location=[c[1], c[0]],
                    radius=5,
                    color="#FFFFFF",
                    fill=True,
                    fill_color="#059669",
                    fill_opacity=0.9,
                    weight=1.5,
                    tooltip=f"生产性服务点位: {f.get('properties', {}).get('Name', '生产服务')}"
                ).add_to(psp_fg)
        psp_fg.add_to(m)

    psa_data = get_geojson_layer_data("prod-service-area")
    if psa_data:
        psa_fg = folium.FeatureGroup(name="🏢 [公服] 生产性服务业集聚区 (11处·面)", show=True)
        folium.GeoJson(
            psa_data,
            style_function=lambda x: {"color": "#087F5B", "fillColor": "#12B886", "weight": 1.5, "fillOpacity": 0.3},
            tooltip="生产性服务业集聚区"
        ).add_to(psa_fg)
        psa_fg.add_to(m)

    cr_data = get_geojson_layer_data("cultural-relic")
    if cr_data:
        cr_fg = folium.FeatureGroup(name="🏛️ [公服] 文物保护单位 (1处·面)", show=True)
        folium.GeoJson(
            cr_data,
            style_function=lambda x: {"color": "#6D28D9", "fillColor": "#8B5CF6", "weight": 2, "fillOpacity": 0.4},
            tooltip="文物保护单位及建控地带"
        ).add_to(cr_fg)
        cr_fg.add_to(m)

    # 6. 现状建设图层 (面)
    bldg_data = get_geojson_layer_data("current-building")
    if bldg_data:
        bldg_fg = folium.FeatureGroup(name="🏘️ [现状] 现状建筑轮廓分布 (7851栋·面)", show=False)
        folium.GeoJson(
            bldg_data,
            style_function=lambda x: {"color": "#D97706", "fillColor": "#F59E0B", "weight": 0.6, "fillOpacity": 0.3},
            tooltip="现状建筑轮廓"
        ).add_to(bldg_fg)
        bldg_fg.add_to(m)

    cur_ind_data = get_geojson_layer_data("current-industrial-land")
    if cur_ind_data:
        cur_ind_fg = folium.FeatureGroup(name="🏭 [现状] 现状已开发工业用地 (684宗·面)", show=False)
        folium.GeoJson(
            cur_ind_data,
            style_function=lambda x: {"color": "#78350F", "fillColor": "#92400E", "weight": 1, "fillOpacity": 0.25},
            tooltip="现状已建设工业用地"
        ).add_to(cur_ind_fg)
        cur_ind_fg.add_to(m)

    # ----------------------------------------------------------------------- #
    # 智能体推荐选址结果（置顶高亮图层）
    # ----------------------------------------------------------------------- #
    hq_fg = folium.FeatureGroup(name="⭐【推荐】研发总部候选地块 (B2商务)", show=True)
    fac_fg = folium.FeatureGroup(name="⭐【推荐】生产基地候选地块 (M1工业)", show=True)
    uni_fg = folium.FeatureGroup(name="⭐【推荐】集中连片综合基地 (方案A)", show=True)
    buffer_fg = folium.FeatureGroup(name="⚠️【管控】卫生防护隔离距离圈 (300m/500m)", show=True)
    commute_fg = folium.FeatureGroup(name="↔️【联动】研发-生产跨区通勤连线", show=True)

    # 1. 渲染研发总部候选地块 (Top 1~5 阶梯展示)
    hq_list = evaluated.get("hq", [])[:5]
    for idx, p in enumerate(hq_list):
        if p.get("geometry"):
            is_top1 = (idx == 0)
            folium.GeoJson(
                p["geometry"],
                style_function=lambda x, top=is_top1: {
                    "fillColor": "#1C7D8C" if top else "#74C0FC",
                    "color": "#0F4C55" if top else "#1864AB",
                    "weight": 3.5 if top else 1.8,
                    "fillOpacity": 0.65 if top else 0.4,
                },
                tooltip=f"<b>【研发总部#{idx+1}】地块 #{p['id']}</b><br>面积: {p['area_ha']} ha<br>综合评分: {p['scores']['total']} 分<br>代码: {p['land_code']}",
            ).add_to(hq_fg)

            if is_top1 and p.get("centroid_lat"):
                folium.Marker(
                    [p["centroid_lat"], p["centroid_lon"]],
                    popup=f"研发总部最优选址 #{p['id']}",
                    icon=folium.Icon(color="blue", icon="briefcase", prefix="fa"),
                ).add_to(hq_fg)

    # 2. 渲染生产基地候选地块 (Top 1~5 阶梯展示) 及卫生隔离圈
    fac_list = evaluated.get("factory", [])[:5]
    for idx, p in enumerate(fac_list):
        if p.get("geometry"):
            is_top1 = (idx == 0)
            folium.GeoJson(
                p["geometry"],
                style_function=lambda x, top=is_top1: {
                    "fillColor": "#E67E22" if top else "#FFD43B",
                    "color": "#B95C00" if top else "#E67700",
                    "weight": 3.5 if top else 1.8,
                    "fillOpacity": 0.65 if top else 0.4,
                },
                tooltip=f"<b>【生产基地#{idx+1}】地块 #{p['id']}</b><br>面积: {p['area_ha']} ha<br>综合评分: {p['scores']['total']} 分<br>代码: {p['land_code']}",
            ).add_to(fac_fg)

            if is_top1 and p.get("centroid_lat"):
                folium.Marker(
                    [p["centroid_lat"], p["centroid_lon"]],
                    popup=f"生产基地最优选址 #{p['id']}",
                    icon=folium.Icon(color="orange", icon="cogs", prefix="fa"),
                ).add_to(fac_fg)

                # 卫生隔离缓冲圈 (半透明红色圆)
                folium.Circle(
                    radius=float(sanitary_buffer),
                    location=[p["centroid_lat"], p["centroid_lon"]],
                    color="#E5484D",
                    fill=True,
                    fill_color="#E5484D",
                    fill_opacity=0.15,
                    weight=1.5,
                    dash_array="5, 5",
                    tooltip=f"GMP制药卫生防护隔离圈：{sanitary_buffer} 米",
                ).add_to(buffer_fg)

    # 3. 渲染集中连片地块 (方案A Top 1~3)
    uni_list = evaluated.get("unified", [])[:3]
    for idx, p in enumerate(uni_list):
        if p.get("geometry"):
            is_top1 = (idx == 0)
            folium.GeoJson(
                p["geometry"],
                style_function=lambda x, top=is_top1: {
                    "fillColor": "#27AE60" if top else "#8CE99A",
                    "color": "#196F3D" if top else "#2B8A3E",
                    "weight": 3.0 if top else 1.5,
                    "fillOpacity": 0.55 if top else 0.35,
                },
                tooltip=f"<b>【集中连片方案A#{idx+1}】地块 #{p['id']}</b><br>面积: {p['area_ha']} ha<br>综合评分: {p['scores']['total']} 分",
            ).add_to(uni_fg)

    # 4. 绘制跨区通勤路线示意
    if best_hq and best_fac:
        pts = [
            [best_hq["centroid_lat"], best_hq["centroid_lon"]],
            [best_fac["centroid_lat"], best_fac["centroid_lon"]],
        ]
        folium.PolyLine(
            pts,
            color="#2E4053",
            weight=3,
            dash_array="8, 6",
            tooltip=f"双地块通勤联动测算：{commute_km} km (车程约 {commute_min} min)",
        ).add_to(commute_fg)

    # 添加至地图
    hq_fg.add_to(m)
    fac_fg.add_to(m)
    uni_fg.add_to(m)
    buffer_fg.add_to(m)
    commute_fg.add_to(m)

    folium.LayerControl(position="topright").add_to(m)
    plugins.Fullscreen().add_to(m)

    st_folium(m, width="100%", height=560)

with tab_comparison:
    st.markdown("### ⚖️ 双选址方案系统多准则比选")

    u_data = comparison.get("unified_scheme", {})
    d_data = comparison.get("dual_site_scheme", {})

    col_u, col_d = st.columns(2)

    with col_u:
        st.markdown(
            """
        <div style="background:#F0FDF4;padding:16px;border-radius:10px;border:1px solid #BBF7D0;">
            <h4 style="color:#166534;margin-top:0;">🌿 方案 A：集中连片综合基地</h4>
            <p style="font-size:13px;color:#374151;">适合追求一体化封闭式管控、减少跨地块通勤内耗的中大型药企。</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(f"**推荐地块**：#{best_uni.get('id', '-') if best_uni else '无'} ({best_uni.get('area_ha', 0)} ha)")
        st.markdown("**核心优势**：")
        for adv in u_data.get("advantages", []):
            st.markdown(f"- ✅ {adv}")
        st.markdown("**制约短板**：")
        for dis in u_data.get("disadvantages", []):
            st.markdown(f"- ⚠️ {dis}")

    with col_d:
        st.markdown(
            """
        <div style="background:#EFF6FF;padding:16px;border-radius:10px;border:1px solid #BFDBFE;">
            <h4 style="color:#1E40AF;margin-top:0;">🏢+🏭 方案 B：研发总部与生产基地分地块布局</h4>
            <p style="font-size:13px;color:#374151;">兼顾城市高品质研发形象与专业工业园充沛环境容量的现代化布局。</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**推荐组合**：总部 #{best_hq.get('id','-')} ({best_hq.get('area_ha',0)}ha) + "
            f"基地 #{best_fac.get('id','-')} ({best_fac.get('area_ha',0)}ha)"
        )
        st.markdown("**核心优势**：")
        for adv in d_data.get("advantages", []):
            st.markdown(f"- ✅ {adv}")
        st.markdown("**制约短板**：")
        for dis in d_data.get("disadvantages", []):
            st.markdown(f"- ⚠️ {dis}")

    st.markdown("---")
    st.info(f"💡 **注册规划师综合评审意见**：\n\n{comparison.get('recommendation', '')}")

with tab_report:
    st.markdown("### 📑 医药制药项目选址规划论证报告")
    st.markdown(agent_res.get("opinion_report", "暂无报告生成"))
    st.download_button(
        label="📥 下载选址论证报告 (.md)",
        data=agent_res.get("opinion_report", ""),
        file_name="临桂区医药制药项目选址规划论证报告.md",
        mime="text/markdown",
    )

with tab_agent_log:
    st.markdown("### 🤖 LangGraph 状态图决策执行日志")
    st.caption("展示智能体在 StateGraph 各节点之间的状态迁移、工具调用及数据过滤流：")
    for log_item in agent_res.get("logs", []):
        if "【步骤" in log_item:
            st.markdown(f"**{log_item}**")
        elif "[OK]" in log_item:
            st.markdown(f"<span style='color:#10B981;font-weight:600;'>{log_item}</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color:#64748B;'>{log_item}</span>", unsafe_allow_html=True)
