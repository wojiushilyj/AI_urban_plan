"""
数据预处理：12 个真实规划 SHP → GeoPackage（SQLite）+ GeoJSON。

- 读取 `基础数据0910/` 下 12 个 shp（UTF-8 编码）
- 缺 .prj 的图层补 CRS = EPSG:4525（CGCS2000 3度带 zone 37，CM 111E，桂林临桂区）
- 统一转 EPSG:4490（CGCS2000 地理坐标）写入 GeoPackage `data/processed/layers.gpkg`
- 转 EPSG:4326（WGS84）输出 GeoJSON，供前端 MapLibre 直接加载

用法：
    python scripts/preprocess.py --input-dir "C:/Users/bin/Desktop/基础数据0910/基础数据0910"
"""
import argparse
import json
import os

import geopandas as gpd

# 源投影（缺失 .prj 时补此 CRS）与存储投影
SRC_CRS = "EPSG:4525"    # CGCS2000 / 3-degree Gauss-Kruger zone 37（CM 111E，带号坐标）
STORE_CRS = "EPSG:4490"  # CGCS2000 地理坐标（README 存储规范）
WEB_CRS = "EPSG:4326"    # WGS84（GeoJSON 规范，前端 MapLibre 原生）

# (layer_id, 中文名, 源 shp 文件名, 分类)
LAYERS = [
    ("perm-farmland", "永久基本农田", "永久基本农田", "baseline"),
    ("eco-redline", "生态保护红线", "生态保护红线", "baseline"),
    ("urban-boundary", "城镇开发边界", "城镇开发边界", "baseline"),
    ("yellow-line", "城市黄线", "城市黄线", "control-line"),
    ("blue-line", "城市蓝线", "城市蓝线", "control-line"),
    ("green-line", "城市绿线", "城市绿线", "control-line"),
    ("industrial-land", "工业用地", "工业用地", "industry"),
    ("regulated-industrial", "控规工业用地", "控规工业用地", "industry"),
    ("industrial-park", "产业园区边界及主导产业定位", "产业园区边界及主导产业定位", "industry"),
    ("prod-service-point", "生产性服务点位（点）", "生产性服务点位（点）", "facility"),
    ("prod-service-area", "生产性服务点位（面）", "生产性服务点位（面）", "facility"),
    ("cultural-relic", "文物保护单位", "文物保护单位", "facility"),
]

GROUPS = [
    ("baseline", "底线管控"),
    ("control-line", "城市控制线"),
    ("industry", "产业用地"),
    ("facility", "服务与设施"),
]

# 无业务含义的 ArcGIS 内部字段，入库/出图前剔除，减小体积
DROP_COLS = ["Shape_Leng", "Shape_Area", "Shape_Le_1"]


def main():
    ap = argparse.ArgumentParser(description="空间数据预处理与入库登记")
    ap.add_argument("--input-dir", required=True, help="源 shp 所在目录")
    ap.add_argument("--out-gpkg", default="data/processed/layers.gpkg", help="GeoPackage 输出路径")
    ap.add_argument("--out-geojson", default="data/processed/geojson", help="GeoJSON 输出目录")
    ap.add_argument("--out-web", default="frontend/public/data/layers", help="前端静态 GeoJSON 目录")
    args = ap.parse_args()

    src_dir = os.path.abspath(args.input_dir)
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
    print(f"源目录: {src_dir}\n")

    for layer_id, name, shp_name, group in LAYERS:
        shp_path = os.path.join(src_dir, shp_name + ".shp")
        if not os.path.exists(shp_path):
            print(f"[跳过] {name}: 未找到 {shp_name}.shp")
            continue

        gdf = gpd.read_file(shp_path, encoding="utf-8")

        # 缺失坐标系 → 补 SRC_CRS（严禁"坐标系不明就入库"）
        if gdf.crs is None:
            gdf = gdf.set_crs(SRC_CRS)
            crs_note = "补 EPSG:4525"
        else:
            crs_note = str(gdf.crs)

        # 剔除 ArcGIS 内部字段
        for col in DROP_COLS:
            if col in gdf.columns:
                gdf = gdf.drop(columns=col)

        n = len(gdf)

        # 1) GeoPackage：统一 EPSG:4490 存储
        gdf.to_crs(STORE_CRS).to_file(gpkg_path, layer=layer_id, driver="GPKG")

        # 2) GeoJSON：EPSG:4326 供前端
        gdf_web = gdf.to_crs(WEB_CRS)
        gdf_web.to_file(os.path.join(geojson_dir, f"{layer_id}.geojson"), driver="GeoJSON")
        gdf_web.to_file(os.path.join(web_dir, f"{layer_id}.geojson"), driver="GeoJSON")

        manifest.append({
            "id": layer_id,
            "name": name,
            "group": group,
            "features": n,
            "geom_type": gdf.geom_type.unique().tolist(),
            "src_crs": crs_note,
        })
        print(f"[ok] {name:14s} ({layer_id})  要素 {n:4d}  {crs_note}")

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
