"""
空间图层接口。数据源：data/processed/layers.gpkg（GeoPackage）。

- GET /api/layers         图层清单（分组 + 要素数 + 几何类型 + 是否可用）
- GET /api/layers/{id}    单图层 GeoJSON（EPSG:4490 经纬度）

前端在 mock 模式下直接从 /data/layers/*.geojson 静态加载；
切换到真实后端（VITE_USE_MOCK=false）时改用本接口。
"""
from fastapi import APIRouter, HTTPException

from app.services import spatial

router = APIRouter(tags=["空间图层"])


@router.get("/layers")
def api_list_layers():
    """图层清单（按大类分组）。"""
    return spatial.layer_summary()


@router.get("/layers/{layer_id}")
def api_get_layer(layer_id: str):
    """单图层 GeoJSON。"""
    try:
        return spatial.layer_feature_collection(layer_id)
    except spatial.LayerNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/layers/{layer_id}/meta")
def api_layer_meta(layer_id: str):
    """单图层元信息（要素数、几何类型、坐标系）。"""
    if layer_id not in spatial.available_layer_ids():
        raise HTTPException(status_code=404, detail=f"图层「{layer_id}」不存在")
    gdf = spatial.load_layer(layer_id)
    return {
        "id": layer_id,
        "name": spatial.layer_display_name(layer_id),
        "features": int(len(gdf)),
        "geom_type": sorted({str(t) for t in gdf.geom_type.dropna().unique()}),
        "crs": str(gdf.crs),
    }
