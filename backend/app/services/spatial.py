"""
空间数据服务：GeoPackage 读取、CRS 转换、缓存与 GeoJSON 输出。

单一数据源：`data/processed/layers.gpkg`（GeoPackage = SQLite，符合"小型本地数据库"定位）。
GeoJSON 仅作出图/交换格式，不是存储格式。

坐标系：
  存储  EPSG:4490（CGCS2000 地理坐标）—— 对外输出一律用这个
  量算  EPSG:4525（CGCS2000 3度带 zone 37 / CM 111E，桂林适用）—— 距离/面积一律在这个投影下算
  ⚠️ 严禁在 4490（度）下直接算距离或面积。

线程安全：lru_cache 缓存的 GeoDataFrame 为只读，调用方**不得原地修改**。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import geopandas as gpd
from shapely.geometry import mapping

from app.config import settings

GPKG_PATH: Path = settings.DATA_PROCESSED / "layers.gpkg"
MANIFEST_PATH: Path = settings.DATA_PROCESSED / "layers_manifest.json"


class LayerNotFound(Exception):
    """图层不存在或数据文件缺失。"""


# --------------------------------------------------------------------------- #
# 清单
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    """读取图层清单（分组 + 图层元信息）。文件缺失时退化为扫描 gpkg。"""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {"groups": [], "layers": [{"id": i, "name": i} for i in available_layer_ids()]}


@lru_cache(maxsize=1)
def available_layer_ids() -> tuple[str, ...]:
    """gpkg 中实际存在的要素图层 id（按名称排序）。"""
    if not GPKG_PATH.exists():
        return ()
    import pyogrio

    return tuple(sorted(pyogrio.list_layers(GPKG_PATH)[:, 0].tolist()))


def layer_display_name(layer_id: str) -> str:
    for item in manifest().get("layers", []):
        if item.get("id") == layer_id:
            return item.get("name", layer_id)
    return layer_id


# --------------------------------------------------------------------------- #
# 图层读取（带缓存）
# --------------------------------------------------------------------------- #

def _read(layer_id: str) -> gpd.GeoDataFrame:
    if layer_id not in available_layer_ids():
        raise LayerNotFound(f"图层「{layer_id}」不存在（数据文件：{GPKG_PATH}）")
    gdf = gpd.read_file(GPKG_PATH, layer=layer_id)
    if gdf.crs is None:
        gdf = gdf.set_crs(settings.CRS_STORAGE)
    return gdf


@lru_cache(maxsize=32)
def load_layer(layer_id: str) -> gpd.GeoDataFrame:
    """按**存储坐标系（EPSG:4490）**读取图层。返回值只读，勿原地修改。"""
    gdf = _read(layer_id)
    if gdf.crs is not None and gdf.crs.to_string() != settings.CRS_STORAGE:
        gdf = gdf.to_crs(settings.CRS_STORAGE)
    return gdf


@lru_cache(maxsize=32)
def load_layer_projected(layer_id: str) -> gpd.GeoDataFrame:
    """按**投影坐标系（EPSG:4525）**读取图层，供距离/面积量算使用。"""
    gdf = _read(layer_id)
    if gdf.crs is None:
        gdf = gdf.set_crs(settings.CRS_STORAGE)
    return gdf.to_crs(settings.CRS_PROJECTED)


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #

def geometries(layer_id: str) -> list:
    """图层的几何列表（存储坐标系）。"""
    return list(load_layer(layer_id).geometry)


def projected_geometries(layer_id: str) -> list:
    """图层的几何列表（投影坐标系，用于量算）。"""
    return list(load_layer_projected(layer_id).geometry)


def to_feature_collection(
    geoms: Iterable,
    props: list[dict[str, Any]] | None = None,
    *,
    drop_internal: bool = True,
) -> dict[str, Any]:
    """
    几何 + 属性 → GeoJSON FeatureCollection（EPSG:4490 经纬度）。

    drop_internal=True 时剔除 SHP 内部字段（Shape_Leng / Shape_Area / fid 等），
    这些字段对用户无意义且会暴露数据来源细节。
    """
    geoms = list(geoms)
    props = props or [{} for _ in geoms]
    internal = {"Shape_Leng", "Shape_Area", "SHAPE_LENG", "SHAPE_AREA", "fid", "FID", "ogc_fid"}
    features: list[dict[str, Any]] = []
    for i, geom in enumerate(geoms):
        if geom is None or geom.is_empty:
            continue
        raw = props[i] if i < len(props) else {}
        clean: dict[str, Any] = {}
        for k, v in dict(raw).items():
            if drop_internal and k in internal:
                continue
            if hasattr(v, "item"):          # numpy 标量 → Python 标量
                v = v.item()
            if v != v:                       # NaN
                v = None
            clean[k] = v
        features.append(
            {"type": "Feature", "geometry": mapping(geom), "properties": clean}
        )
    return {"type": "FeatureCollection", "features": features}


def layer_feature_collection(layer_id: str) -> dict[str, Any]:
    """整图层 → GeoJSON FeatureCollection（存储坐标系）。"""
    gdf = load_layer(layer_id)
    records = gdf.drop(columns=[gdf.geometry.name]).to_dict("records")
    return to_feature_collection(gdf.geometry, records)


def layer_summary() -> dict[str, Any]:
    """图层清单（分组 + 每个图层的要素数与几何类型），供 /api/layers 使用。"""
    data = manifest()
    layers = []
    for item in data.get("layers", []):
        lid = item.get("id")
        layers.append({**item, "available": lid in available_layer_ids()})
    return {"groups": [{"id": g[0], "name": g[1]} for g in data.get("groups", [])], "layers": layers}
