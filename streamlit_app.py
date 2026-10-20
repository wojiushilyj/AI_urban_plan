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

    # 绘制推荐地块图层
    hq_fg = folium.FeatureGroup(name="🏢 研发总部推荐地块 (B2)", show=True)
    fac_fg = folium.FeatureGroup(name="🏭 生产基地推荐地块 (M1)", show=True)
    uni_fg = folium.FeatureGroup(name="🌿 集中连片综合基地 (方案A)", show=True)
    buffer_fg = folium.FeatureGroup(name="⚠️ 卫生防护隔离距离圈 (300m/500m)", show=True)
    commute_fg = folium.FeatureGroup(name="↔️ 研发-生产跨区通勤连线", show=True)

    # 1. 渲染研发总部地块
    if best_hq and best_hq.get("geometry"):
        folium.GeoJson(
            best_hq["geometry"],
            style_function=lambda x: {
                "fillColor": "#1C7D8C",
                "color": "#0F4C55",
                "weight": 3,
                "fillOpacity": 0.65,
            },
            tooltip=f"<b>【研发总部Top1】地块 #{best_hq['id']}</b><br>面积: {best_hq['area_ha']} ha<br>综合评分: {best_hq['scores']['total']} 分<br>代码: {best_hq['land_code']}",
        ).add_to(hq_fg)

        folium.Marker(
            [best_hq["centroid_lat"], best_hq["centroid_lon"]],
            popup=f"研发总部 #{best_hq['id']}",
            icon=folium.Icon(color="blue", icon="briefcase", prefix="fa"),
        ).add_to(hq_fg)

    # 2. 渲染生产基地地块及卫生隔离圈
    if best_fac and best_fac.get("geometry"):
        folium.GeoJson(
            best_fac["geometry"],
            style_function=lambda x: {
                "fillColor": "#E67E22",
                "color": "#B95C00",
                "weight": 3,
                "fillOpacity": 0.65,
            },
            tooltip=f"<b>【生产基地Top1】地块 #{best_fac['id']}</b><br>面积: {best_fac['area_ha']} ha<br>综合评分: {best_fac['scores']['total']} 分<br>代码: {best_fac['land_code']}",
        ).add_to(fac_fg)

        folium.Marker(
            [best_fac["centroid_lat"], best_fac["centroid_lon"]],
            popup=f"生产基地 #{best_fac['id']}",
            icon=folium.Icon(color="orange", icon="cogs", prefix="fa"),
        ).add_to(fac_fg)

        # 卫生隔离缓冲圈 (半透明红色圆)
        folium.Circle(
            radius=float(sanitary_buffer),
            location=[best_fac["centroid_lat"], best_fac["centroid_lon"]],
            color="#E5484D",
            fill=True,
            fill_color="#E5484D",
            fill_opacity=0.15,
            weight=1.5,
            dash_array="5, 5",
            tooltip=f"GMP制药卫生防护隔离圈：{sanitary_buffer} 米",
        ).add_to(buffer_fg)

    # 3. 渲染集中连片地块 (方案A)
    if best_uni and best_uni.get("geometry"):
        folium.GeoJson(
            best_uni["geometry"],
            style_function=lambda x: {
                "fillColor": "#27AE60",
                "color": "#196F3D",
                "weight": 2.5,
                "fillOpacity": 0.45,
            },
            tooltip=f"<b>【集中连片方案A】地块 #{best_uni['id']}</b><br>面积: {best_uni['area_ha']} ha<br>综合评分: {best_uni['scores']['total']} 分",
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
