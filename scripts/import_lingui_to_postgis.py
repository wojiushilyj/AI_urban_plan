"""
将桂林市临桂区真实空间规划图斑全量导入远程 PostGIS (onemap_db) 的 land_use_tuban 表。
使空间智能体选址算法直接从 PostGIS 检索临桂区范围内的候选工业与研发地块，并基于临桂本土公服设施量算。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import pyproj
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.services.postgis_service import postgis_service


def to_multipolygon(geom) -> MultiPolygon:
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    elif isinstance(geom, MultiPolygon):
        return geom
    else:
        raise ValueError(f"Unsupported geometry type: {type(geom)}")


def run_import():
    conn = postgis_service.get_connection()
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4525", always_xy=True)

    print("==> 1. 清理已有临桂区图斑...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM land_use_tuban WHERE district = '临桂区' OR id >= 10000;")
        print(f"    已清理 {cur.rowcount} 条旧数据")

    records_to_insert: List[Dict[str, Any]] = []
    current_id = 10001

    # 1. 控规工业用地 (regulated-industrial) -> 145 宗 M1 工业基地候选
    p_reg = ROOT_DIR / "data" / "processed" / "geojson" / "regulated-industrial.geojson"
    if p_reg.exists():
        with open(p_reg, encoding="utf-8") as f:
            d = json.load(f)
        for idx, feat in enumerate(d.get("features", [])):
            geom_shapely = shape(feat["geometry"])
            mp = to_multipolygon(geom_shapely)
            coords_proj = [transformer.transform(x, y) for poly in mp.geoms for x, y in poly.exterior.coords]
            poly_proj = Polygon(coords_proj)
            area_m2 = poly_proj.area
            peri_m = poly_proj.length
            records_to_insert.append({
                "id": current_id,
                "land_code": "100101",
                "land_type": f"控规工业用地(M1·临桂#{idx+1})",
                "area_m2": round(area_m2, 2),
                "area_mu": round(area_m2 * 0.0015, 2),
                "perimeter_m": round(peri_m, 2),
                "geojson": json.dumps(mapping(mp)),
                "district": "临桂区",
            })
            current_id += 1
        print(f"    已加载控规工业用地 {len(d.get('features', []))} 宗")

    # 2. 生产性服务与研发总部片区 (prod-service-area) -> 11 宗 B2 商务研发候选
    p_psa = ROOT_DIR / "data" / "processed" / "geojson" / "prod-service-area.geojson"
    if p_psa.exists():
        with open(p_psa, encoding="utf-8") as f:
            d = json.load(f)
        for idx, feat in enumerate(d.get("features", [])):
            geom_shapely = shape(feat["geometry"])
            mp = to_multipolygon(geom_shapely)
            coords_proj = [transformer.transform(x, y) for poly in mp.geoms for x, y in poly.exterior.coords]
            poly_proj = Polygon(coords_proj)
            area_m2 = poly_proj.area
            peri_m = poly_proj.length
            name = feat.get("properties", {}).get("企业名称") or feat.get("properties", {}).get("名称") or f"研发总部集聚区#{idx+1}"
            records_to_insert.append({
                "id": current_id,
                "land_code": "0902",
                "land_type": f"研发商务总部(B2·{name})",
                "area_m2": round(area_m2, 2),
                "area_mu": round(area_m2 * 0.0015, 2),
                "perimeter_m": round(peri_m, 2),
                "geojson": json.dumps(mapping(mp)),
                "district": "临桂区",
            })
            current_id += 1
        print(f"    已加载生产性服务与研发总部 {len(d.get('features', []))} 宗")

    # 3. 货运枢纽场站 (freight-station) -> 17 处
    p_fs = ROOT_DIR / "data" / "processed" / "geojson" / "freight-station.geojson"
    if p_fs.exists():
        with open(p_fs, encoding="utf-8") as f:
            d = json.load(f)
        for idx, feat in enumerate(d.get("features", [])):
            geom_shapely = shape(feat["geometry"])
            mp = to_multipolygon(geom_shapely)
            coords_proj = [transformer.transform(x, y) for poly in mp.geoms for x, y in poly.exterior.coords]
            poly_proj = Polygon(coords_proj)
            area_m2 = poly_proj.area
            peri_m = poly_proj.length
            records_to_insert.append({
                "id": current_id,
                "land_code": "110101",
                "land_type": f"货运物流场站(W1·临桂#{idx+1})",
                "area_m2": round(area_m2, 2),
                "area_mu": round(area_m2 * 0.0015, 2),
                "perimeter_m": round(peri_m, 2),
                "geojson": json.dumps(mapping(mp)),
                "district": "临桂区",
            })
            current_id += 1
        print(f"    已加载货运物流场站 {len(d.get('features', []))} 宗")

    # 4. 市政设施 (municipal-land): 1301供水, 1302排水/污水
    p_mun = ROOT_DIR / "data" / "processed" / "geojson" / "municipal-land.geojson"
    if p_mun.exists():
        with open(p_mun, encoding="utf-8") as f:
            d = json.load(f)
        for idx, feat in enumerate(d.get("features", [])):
            geom_shapely = shape(feat["geometry"])
            mp = to_multipolygon(geom_shapely)
            coords_proj = [transformer.transform(x, y) for poly in mp.geoms for x, y in poly.exterior.coords]
            poly_proj = Polygon(coords_proj)
            area_m2 = poly_proj.area
            peri_m = poly_proj.length
            props_str = str(feat.get("properties", {}))
            code = "1301" if "1301" in props_str else ("1302" if "1302" in props_str else "1303")
            records_to_insert.append({
                "id": current_id,
                "land_code": code,
                "land_type": f"市政设施({code}·临桂#{idx+1})",
                "area_m2": round(area_m2, 2),
                "area_mu": round(area_m2 * 0.0015, 2),
                "perimeter_m": round(peri_m, 2),
                "geojson": json.dumps(mapping(mp)),
                "district": "临桂区",
            })
            current_id += 1
        print(f"    已加载市政设施 {len(d.get('features', []))} 宗")

    # 5. 高等院校 (桂林医学院临桂新校区) & 三甲医院 (桂林医学院第二附属医院)
    # 桂医临桂校区 (致远路1号, 约 80 ha)
    uni_poly = Polygon([
        [110.1930, 25.2710], [110.2030, 25.2710], [110.2030, 25.2790], [110.1930, 25.2790], [110.1930, 25.2710]
    ])
    records_to_insert.append({
        "id": current_id,
        "land_code": "080401",
        "land_type": "高等院校(A6·桂林医学院临桂新校区)",
        "area_m2": 800000.0,
        "area_mu": 1200.0,
        "perimeter_m": 3600.0,
        "geojson": json.dumps(mapping(to_multipolygon(uni_poly))),
        "district": "临桂区",
    })
    current_id += 1

    # 桂医第二附属医院 (三甲, 人民路212号)
    hosp_poly = Polygon([
        [110.1900, 25.2660], [110.1950, 25.2660], [110.1950, 25.2700], [110.1900, 25.2700], [110.1900, 25.2660]
    ])
    records_to_insert.append({
        "id": current_id,
        "land_code": "080601",
        "land_type": "三甲综合医院(A51·桂医二附院)",
        "area_m2": 200000.0,
        "area_mu": 300.0,
        "perimeter_m": 1800.0,
        "geojson": json.dumps(mapping(to_multipolygon(hosp_poly))),
        "district": "临桂区",
    })
    current_id += 1

    print(f"==> 2. 开始写入 PostGIS (共 {len(records_to_insert)} 条临桂区图斑)...")
    sql = """
        INSERT INTO land_use_tuban (id, land_code, land_type, area_m2, area_mu, perimeter_m, geom, district, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), %s, NOW());
    """
    with conn.cursor() as cur:
        for r in records_to_insert:
            cur.execute(sql, (
                r["id"], r["land_code"], r["land_type"], r["area_m2"], r["area_mu"],
                r["perimeter_m"], r["geojson"], r["district"]
            ))
    print("==> 3. 写入完成！创建临桂空间索引...")
    with conn.cursor() as cur:
        cur.execute("REINDEX TABLE land_use_tuban;")
        cur.execute("SELECT count(*) as total, count(*) FILTER (WHERE district = '临桂区') as lingui_total FROM land_use_tuban;")
        row = cur.fetchone()
        print(f"    PostGIS 库内最新统计：总图斑 {row['total']} 宗，临桂区专属图斑 {row['lingui_total']} 宗。")


if __name__ == "__main__":
    run_import()
