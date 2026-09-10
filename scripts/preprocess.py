"""
数据预处理：真实规划 SHP → GeoPackage（SQLite）+ GeoJSON。

- 读取原始 shp（UTF-8 编码），支持传入多个源目录（分批交付的数据）
- 缺 .prj 的图层补 CRS = EPSG:4525（CGCS2000 3度带 zone 37，CM 111E，桂林临桂区）
- 统一转 EPSG:4490（CGCS2000 地理坐标）写入 GeoPackage `data/processed/layers.gpkg`
- 转 EPSG:4326（WGS84）输出 GeoJSON，供前端 MapLibre 直接加载
- 属性裁剪：按白名单保留业务字段，剔除 ArcGIS 内部字段与全空列，缩小体积
- 坐标网格取整到 1e-6 度（约 0.11 m，远小于出图分辨率），显著压缩 GeoJSON

用法：
    python scripts/preprocess.py --input-dir "C:/Users/bin/Desktop/基础数据0910/基础数据0910" \
                                 --input-dir "C:/Users/bin/Desktop/工业0910/工业0910"
"""
import argparse
import json
import os

import geopandas as gpd
import numpy as np
import shapely

# 源投影（缺失 .prj 时补此 CRS）与存储投影
SRC_CRS = "EPSG:4525"    # CGCS2000 / 3-degree Gauss-Kruger zone 37（CM 111E，带号坐标）
STORE_CRS = "EPSG:4490"  # CGCS2000 地理坐标（README 存储规范）
WEB_CRS = "EPSG:4326"    # WGS84（GeoJSON 规范，前端 MapLibre 原生）

# 坐标取整精度（度）。1e-6 ≈ 0.11 m，远细于屏幕像素，仅用于压缩体积。
COORD_PRECISION = 6

# 无业务含义的 ArcGIS 内部字段，入库/出图前剔除
DROP_COLS = ["Shape_Leng", "Shape_Area", "Shape_Le_1", "SHAPE_Leng", "SHAPE_Area"]

# 图层登记表。
#   id/name/shp/group 必填；keep=属性白名单（None 表示全保留）；rename=字段重命名。
LAYERS = [
    # ---- 底线管控 ----
    {"id": "perm-farmland", "name": "永久基本农田", "shp": "永久基本农田", "group": "baseline"},
    {"id": "eco-redline", "name": "生态保护红线", "shp": "生态保护红线", "group": "baseline"},
    {"id": "urban-boundary", "name": "城镇开发边界", "shp": "城镇开发边界", "group": "baseline"},
    # ---- 城市控制线 ----
    {"id": "yellow-line", "name": "城市黄线", "shp": "城市黄线", "group": "control-line"},
    {"id": "blue-line", "name": "城市蓝线", "shp": "城市蓝线", "group": "control-line"},
    {"id": "green-line", "name": "城市绿线", "shp": "城市绿线", "group": "control-line"},
    # ---- 产业用地 ----
    # 总规工业用地（原图层，215 图斑，源 SHP 无业务属性）
    {"id": "industrial-land", "name": "总规工业用地", "shp": "工业用地", "group": "industry"},
    # 临桂现状工业用地：2026-09-10 新增，684 图斑，覆盖临桂全区，
    # 三调地类 + 企业/行业/产值属性。与 industrial-land 并存，不替换。
    {
        "id": "current-industrial-land", "name": "临桂现状工业用地", "shp": "临桂合并工业用地0910",
        "group": "industry",
        "keep": ["BSM", "DLBM", "DLMC", "TBMJ", "ZLDWMC", "行政区", "用地性",
                 "公司名", "行业门", "行业_1", "产值（"],
        "rename": {"TBMJ": "图斑面积", "ZLDWMC": "坐落单位", "公司名": "企业名称",
                   "行业门": "行业代码", "行业_1": "行业名称", "产值（": "产值"},
    },
    {"id": "regulated-industrial", "name": "控规工业用地", "shp": "控规工业用地", "group": "industry"},
    {"id": "industrial-park", "name": "产业园区边界及主导产业定位", "shp": "产业园区边界及主导产业定位", "group": "industry"},
    # ---- 交通设施（新增分类，原 4 类无法容纳，单独成类）----
    # 道路路网缺 .prj，按同批数据统一补 EPSG:4525（坐标范围校验通过）。
    {
        "id": "road-network", "name": "道路路网", "shp": "道路路网", "group": "transport",
        "keep": ["Layer", "时速"], "rename": {"Layer": "道路等级"},
    },
    {"id": "highway-interchange", "name": "高速出入口", "shp": "高速出入口", "group": "transport",
     "keep": ["名称"]},
    {"id": "freight-station", "name": "货运场站用地", "shp": "货运场站用地", "group": "transport",
     "keep": ["名称", "状态"]},
    # ---- 服务与设施 ----
    {"id": "prod-service-point", "name": "生产性服务点位（点）", "shp": "生产性服务点位（点）", "group": "facility"},
    {"id": "prod-service-area", "name": "生产性服务点位（面）", "shp": "生产性服务点位（面）", "group": "facility"},
    {"id": "cultural-relic", "name": "文物保护单位", "shp": "文物保护单位", "group": "facility"},
]

GROUPS = [
    ("baseline", "底线管控"),
    ("control-line", "城市控制线"),
    ("industry", "产业用地"),
    ("facility", "服务与设施"),
    ("transport", "交通设施"),
]


def round_geom(geom):
    """坐标取整到 COORD_PRECISION 位小数（仅压缩体积，不改拓扑结构）。"""
    if geom is None or geom.is_empty:
        return geom
    return shapely.transform(geom, lambda c: np.round(c, COORD_PRECISION))


def resolve_shp(src_dirs, shp_name):
    """在多个源目录中查找 shp 文件。"""
    for d in src_dirs:
        p = os.path.join(d, shp_name + ".shp")
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="空间数据预处理与入库登记")
    ap.add_argument("--input-dir", required=True, action="append",
                    help="源 shp 所在目录，可重复传入多个")
    ap.add_argument("--out-gpkg", default="data/processed/layers.gpkg", help="GeoPackage 输出路径")
    ap.add_argument("--out-geojson", default="data/processed/geojson", help="GeoJSON 输出目录")
    ap.add_argument("--out-web", default="frontend/public/data/layers", help="前端静态 GeoJSON 目录")
    args = ap.parse_args()

    src_dirs = [os.path.abspath(d) for d in args.input_dir]
    gpkg_path = os.path.abspath(args.out_gpkg)
    geojson_dir = os.path.abspath(args.out_geojson)
    web_dir = os.path.abspath(args.out_web)

    os.makedirs(os.path.dirname(gpkg_path), exist_ok=True)
    os.makedirs(geojson_dir, exist_ok=True)
    os.makedirs(web_dir, exist_ok=True)

    # 重置 gpkg（避免重复写入冲突）
    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)

    manifest = []
    print(f"源目录: {', '.join(src_dirs)}\n")

    for spec in LAYERS:
        layer_id, name, shp_name, group = spec["id"], spec["name"], spec["shp"], spec["group"]
        shp_path = resolve_shp(src_dirs, shp_name)
        if not shp_path:
            print(f"[跳过] {name}: 未找到 {shp_name}.shp")
            continue

        gdf = gpd.read_file(shp_path, encoding="utf-8")

        # 丢弃空几何（个别图层存在无效记录）
        n_empty = int(gdf.geometry.isna().sum())
        if n_empty:
            gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
            print(f"       {name}: 剔除 {n_empty} 条空几何")

        # 缺坐标系 → 补 SRC_CRS（严禁"坐标系不明就入库"）
        if gdf.crs is None:
            gdf = gdf.set_crs(SRC_CRS)
            crs_note = "补 EPSG:4525"
        else:
            crs_note = str(gdf.crs)

        # 属性裁剪：白名单 → 剔 ArcGIS 内部字段 → 剔全空列 → 重命名
        if spec.get("keep"):
            keep = [c for c in gdf.columns if c in spec["keep"] or c == "geometry"]
            gdf = gdf[keep]
        gdf = gdf.drop(columns=[c for c in DROP_COLS if c in gdf.columns])
        null_cols = [c for c in gdf.columns if c != "geometry" and gdf[c].isna().all()]
        if null_cols:
            gdf = gdf.drop(columns=null_cols)
        if spec.get("rename"):
            gdf = gdf.rename(columns=spec["rename"])

        n = len(gdf)
        src_area = float(gdf.to_crs(SRC_CRS).area.sum() / 1e4) if gdf.geom_type.iloc[0] != "Point" else 0.0

        # 1) GeoPackage：统一 EPSG:4490 存储
        gdf.to_crs(STORE_CRS).to_file(gpkg_path, layer=layer_id, driver="GPKG")

        # 2) GeoJSON：EPSG:4326 供前端（坐标取整压缩体积）
        gdf_web = gdf.to_crs(WEB_CRS)
        gdf_web = gdf_web.set_geometry(gdf_web.geometry.map(round_geom))
        gdf_web.to_file(os.path.join(geojson_dir, f"{layer_id}.geojson"), driver="GeoJSON")
        gdf_web.to_file(os.path.join(web_dir, f"{layer_id}.geojson"), driver="GeoJSON")

        manifest.append({
            "id": layer_id,
            "name": name,
            "group": group,
            "features": n,
            "geom_type": sorted(gdf.geom_type.unique().tolist()),
            "src_crs": crs_note,
        })
        area_txt = f"  面积 {src_area:9.1f} ha" if src_area else ""
        print(f"[ok] {name:16s} ({layer_id})  要素 {n:4d}{area_txt}  {crs_note}")

    # 清单（供后端/前端参考）
    manifest_path = os.path.join(os.path.dirname(gpkg_path), "layers_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"groups": GROUPS, "layers": manifest}, f, ensure_ascii=False, indent=2)

    print(f"\n完成：")
    print(f"  GeoPackage: {gpkg_path}")
    print(f"  GeoJSON:    {geojson_dir}/*.geojson")
    print(f"  前端静态:   {web_dir}/*.geojson")
    print(f"  清单:       {manifest_path}")


if __name__ == "__main__":
    main()
