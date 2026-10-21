"""
PostGIS 空间数据库服务。
连接远程 PostgreSQL / PostGIS 数据库（117.72.210.60:5432/onemap_db），
提供国土空间规划图斑（land_use_tuban）的高性能空间检索、拓扑缓冲与多因子量算。
"""
from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import psycopg
from psycopg.rows import dict_row
from shapely import wkb, wkt
from shapely.geometry import mapping, shape

from app.config import settings

logger = logging.getLogger(__name__)

# 医药制药选址国标分类代码映射 (GB/T 50137-2011)
PHARMA_LAND_CODES = {
    # 研发总部推荐用地：B2 商务用地、创新型研发用地
    "hq": ["0902", "0904", "0901"],
    # 生产基地推荐用地：M1 一类工业用地、M2 二类工业用地、M 工业用地
    "factory": ["100101", "1001", "100102"],
    # 集中连片推荐用地：兼顾生产与总部的大型工业/产业用地
    "unified": ["100101", "1001", "0904", "100102"],
    # 产学研配套：高等教育用地 (A6)
    "university": ["080401"],
    # 医疗卫生配套：医院 (A51)
    "hospital": ["080601", "0806"],
    # 仓储物流：一类物流仓储 (W1)
    "logistics": ["110101", "1101"],
    # 市政给排水：供水 (U11) / 排水污水处理 (U12)
    "water_supply": ["1302"],
    "drainage_sewage": ["1301"],
    # 居住生活圈：二类居住用地 (R2)
    "residential": ["070102", "0701"],
    # 生态绿地：公园绿地 (G1)
    "park": ["1401"],
}


class PostGISService:
    def __init__(self, conn_str: Optional[str] = None):
        self.conn_str = conn_str or (
            f"host={settings.POSTGIS_HOST} port={settings.POSTGIS_PORT} "
            f"dbname={settings.POSTGIS_DB} user={settings.POSTGIS_USER} "
            f"password={settings.POSTGIS_PASSWORD} connect_timeout=15"
        )
        self._amenity_cache: Optional[Dict[str, List[Tuple[float, float]]]] = None
        self._shared_conn: Optional[psycopg.Connection] = None

    def get_connection(self):
        """获取 psycopg 数据库连接（自动重连与连接复用）。"""
        if self._shared_conn is not None:
            try:
                self._shared_conn.execute("SELECT 1;")
                return self._shared_conn
            except Exception:
                try:
                    self._shared_conn.close()
                except Exception:
                    pass
                self._shared_conn = None

        self._shared_conn = psycopg.connect(
            self.conn_str,
            row_factory=dict_row,
            autocommit=True,
        )
        return self._shared_conn

    def get_amenity_coords_projected(self) -> Dict[str, List[Tuple[float, float]]]:
        """
        一次性拉取高校、医院、物流、供水排水等关键配套图斑在 EPSG:4525 投影下的坐标。
        在内存中完成高速距离量算，避免循环调用导致的 WAN 网络延迟与超时。
        """
        if self._amenity_cache is not None:
            return self._amenity_cache

        import pyproj
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4525", always_xy=True)

        target_categories = {
            "university": PHARMA_LAND_CODES["university"],
            "hospital": PHARMA_LAND_CODES["hospital"],
            "logistics": PHARMA_LAND_CODES["logistics"],
            "water_supply": PHARMA_LAND_CODES["water_supply"],
            "drainage_sewage": PHARMA_LAND_CODES["drainage_sewage"],
            "residential": PHARMA_LAND_CODES["residential"],
        }
        all_codes = [c for codes in target_categories.values() for c in codes]

        sql = """
            SELECT land_code, 
                   ST_X(ST_Centroid(geom)) AS lon, 
                   ST_Y(ST_Centroid(geom)) AS lat
            FROM land_use_tuban
            WHERE land_code = ANY(%s)
              AND (district = '临桂区' OR ST_X(ST_Centroid(geom)) <= 110.235);
        """
        cache: Dict[str, List[Tuple[float, float]]] = {k: [] for k in target_categories}

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (all_codes,))
                    for row in cur.fetchall():
                        code = row["land_code"]
                        lon, lat = float(row["lon"]), float(row["lat"])
                        x, y = transformer.transform(lon, lat)
                        for cat, cat_codes in target_categories.items():
                            if code in cat_codes:
                                cache[cat].append((x, y))
            self._amenity_cache = cache
            return cache
        except Exception as e:
            logger.warning(f"Failed to load amenity coords from PostGIS: {e}")
            return cache

    def calculate_distance_to_category(
        self,
        lon: float,
        lat: float,
        category: str,
    ) -> float:
        """
        在 EPSG:4525 投影下高速计算经纬度点到指定设施类型的最近米级距离。
        """
        import pyproj
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4525", always_xy=True)
        px, py = transformer.transform(lon, lat)

        cache = self.get_amenity_coords_projected()
        coords = cache.get(category, [])
        if not coords:
            # 行业默认基准参考距离
            defaults = {
                "university": 3500.0,
                "hospital": 2500.0,
                "logistics": 2000.0,
                "water_supply": 1500.0,
                "drainage_sewage": 1800.0,
                "residential": 450.0,
            }
            return defaults.get(category, 2000.0)

        # 欧几里得距离量算（在 EPSG:4525 平面投影下，1单位=1米）
        min_d = min(math.hypot(px - x, py - y) for x, y in coords)
        return float(min_d)

    def health_check(self) -> Dict[str, Any]:
        """检查 PostGIS 连接与图斑总数。"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                pg_version = cur.fetchone()["version"]
                cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis';")
                postgis_ver = cur.fetchone()["extversion"]
                cur.execute("SELECT count(*) as total_count FROM land_use_tuban;")
                total = cur.fetchone()["total_count"]
                return {
                    "status": "connected",
                    "host": settings.POSTGIS_HOST,
                    "database": settings.POSTGIS_DB,
                    "postgresql_version": pg_version.split(",")[0],
                    "postgis_version": postgis_ver,
                    "total_tuban": total,
                }
        except Exception as e:
            logger.warning(f"PostGIS health check failed: {e}")
            return {
                "status": "disconnected",
                "error": str(e),
                "host": settings.POSTGIS_HOST,
                "database": settings.POSTGIS_DB,
            }

    def fetch_pharma_candidates(
        self,
        role: str = "factory",
        min_ha: float = 1.0,
        max_ha: float = 50.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        按角色获取医药制药候选地块：
        - hq: 研发总部（B2 商务用地、研发用地）
        - factory: 生产基地（M1/M2 一类/二类工业用地）
        - unified: 集中连片大型产业用地
        """
        target_codes = PHARMA_LAND_CODES.get(role, PHARMA_LAND_CODES["factory"])

        sql = """
            SELECT id, land_code, land_type, 
                   round((area_m2 / 10000.0)::numeric, 2) AS area_ha,
                   round(perimeter_m::numeric, 2) AS perimeter_m,
                   ST_AsGeoJSON(geom) AS geojson,
                   ST_X(ST_Centroid(geom)) AS centroid_lon,
                   ST_Y(ST_Centroid(geom)) AS centroid_lat,
                   round((4.0 * pi() * area_m2 / (perimeter_m * perimeter_m))::numeric, 4) AS compactness
            FROM land_use_tuban
            WHERE land_code = ANY(%s)
              AND (area_m2 / 10000.0) >= %s
              AND (area_m2 / 10000.0) <= %s
              AND (district = '临桂区' OR ST_X(ST_Centroid(geom)) <= 110.235)
            ORDER BY (district = '临桂区') DESC, area_m2 DESC
            LIMIT %s;
        """

        try:
            conn = self.get_connection()
            with conn.cursor() as cur:
                cur.execute(sql, (target_codes, min_ha, max_ha, limit))
                rows = cur.fetchall()
                if rows:
                    result = []
                    for r in rows:
                        item = dict(r)
                        if item.get("geojson"):
                            item["geometry"] = json.loads(item["geojson"])
                        item["role"] = role
                        result.append(item)
                    return result
        except Exception as e:
            logger.warning(f"PostGIS fetch candidates warning ({e}), falling back to local dataset...")

        # --- 优雅降级：当外部网络闪断或超时，从本地临桂区法定图斑提取真实候选 ---
        return self._fetch_local_fallback(role, min_ha, max_ha, limit)

    def _fetch_local_fallback(self, role: str, min_ha: float, max_ha: float, limit: int) -> List[Dict[str, Any]]:
        """本地临桂区法定规划离线备用候选池。"""
        try:
            from app.services import spatial
            if role == "hq":
                layer = spatial.get_layer("prod-service-area")
            else:
                layer = spatial.get_layer("regulated-industrial")
            if layer is None or layer.empty:
                layer = spatial.get_layer("regulated-industrial")
            if layer is None or layer.empty:
                return []
            result = []
            for idx, row in layer.iterrows():
                geom = row.geometry
                geom_proj = spatial.to_projected(geom)
                area_ha = geom_proj.area / 10000.0
                if min_ha <= area_ha <= max_ha:
                    p = geom_proj.length
                    compactness = (4 * math.pi * geom_proj.area) / (p * p) if p > 0 else 0.5
                    c_pt = geom.centroid
                    result.append({
                        "id": (10200 if role == "hq" else 10000) + int(idx) + 1,
                        "land_code": "0902" if role == "hq" else "100101",
                        "land_type": "研发总部(B2·临桂)" if role == "hq" else "控规工业(M1·临桂)",
                        "area_ha": round(area_ha, 2),
                        "perimeter_m": round(p, 1),
                        "geometry": mapping(geom),
                        "centroid_lon": round(c_pt.x, 6),
                        "centroid_lat": round(c_pt.y, 6),
                        "compactness": round(compactness, 4),
                        "role": role,
                    })
                    if len(result) >= limit:
                        break
            return result
        except Exception as e:
            logger.error(f"Fallback error: {e}")
            return []

    def fetch_amenities_layers(
        self,
        codes: Optional[List[str]] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """获取高校、医院、物流、市政等周边配套设施图斑。"""
        if not codes:
            codes = (
                PHARMA_LAND_CODES["university"]
                + PHARMA_LAND_CODES["hospital"]
                + PHARMA_LAND_CODES["logistics"]
                + PHARMA_LAND_CODES["drainage_sewage"]
                + PHARMA_LAND_CODES["water_supply"]
            )

        sql = """
            SELECT id, land_code, land_type,
                   round((area_m2 / 10000.0)::numeric, 2) AS area_ha,
                   ST_AsGeoJSON(geom) AS geojson,
                   ST_X(ST_Centroid(geom)) AS centroid_lon,
                   ST_Y(ST_Centroid(geom)) AS centroid_lat
            FROM land_use_tuban
            WHERE land_code = ANY(%s)
            LIMIT %s;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (codes, limit))
                    rows = cur.fetchall()
                    result = []
                    for r in rows:
                        item = dict(r)
                        if item.get("geojson"):
                            item["geometry"] = json.loads(item["geojson"])
                        result.append(item)
                    return result
        except Exception as e:
            logger.error(f"Error fetching amenities: {e}")
            return []

    def calculate_distance_to_features(
        self,
        parcel_id: int,
        target_land_codes: List[str],
    ) -> Optional[float]:
        """
        利用 PostGIS ST_Distance 在法定 EPSG:4525 投影下精确量算米级距离。
        """
        sql = """
            SELECT round(min(ST_Distance(
                ST_Transform(p.geom, 4525),
                ST_Transform(t.geom, 4525)
            ))::numeric, 2) AS min_dist_m
            FROM land_use_tuban p, land_use_tuban t
            WHERE p.id = %s
              AND t.land_code = ANY(%s)
              AND t.id <> p.id;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (parcel_id, target_land_codes))
                    row = cur.fetchone()
                    if row and row["min_dist_m"] is not None:
                        return float(row["min_dist_m"])
                    return None
        except Exception as e:
            logger.warning(f"Distance calculation error for parcel {parcel_id}: {e}")
            return None

    def calculate_commute_distance(
        self,
        hq_parcel_id: int,
        factory_parcel_id: int,
    ) -> float:
        """计算研发总部与生产基地之间的直线/通勤投影距离（米）。"""
        sql = """
            SELECT round(ST_Distance(
                ST_Transform(h.geom, 4525),
                ST_Transform(f.geom, 4525)
            )::numeric, 2) AS dist_m
            FROM land_use_tuban h, land_use_tuban f
            WHERE h.id = %s AND f.id = %s;
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (hq_parcel_id, factory_parcel_id))
                    row = cur.fetchone()
                    if row and row["dist_m"] is not None:
                        return float(row["dist_m"])
                    return 0.0
        except Exception as e:
            logger.warning(f"Commute calculation error: {e}")
            return 0.0


# 全局单例
postgis_service = PostGISService()
