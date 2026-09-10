"""全局配置。坐标系约定见 README.md §4，改这里等于改全项目，谨慎。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]          # backend/
ROOT_DIR = BASE_DIR.parent                               # AI_urban_plan/


class Settings(BaseSettings):
    PROJECT_NAME: str = "多场景智慧选址系统"

    # ---- 坐标系（国土行业法定要求，勿随意改）----
    CRS_STORAGE: str = "EPSG:4490"    # CGCS2000 地理坐标，入库存储
    CRS_PROJECTED: str = "EPSG:4525"  # CGCS2000 3度带 zone 37（CM 111E），距离/面积量算（桂林临桂区）
    CRS_WEB: str = "EPSG:3857"        # Web Mercator，前端展示

    # ---- 数据库（小型本地数据库：SQLite）----
    DB_PATH: Path = ROOT_DIR / "data" / "app.db"
    SPATIALITE_ENABLED: bool = False  # 空间 SQL 需求超限时再开，默认用 GeoPandas 算

    # ---- 数据目录 ----
    DATA_RAW: Path = ROOT_DIR / "data" / "raw"
    DATA_PROCESSED: Path = ROOT_DIR / "data" / "processed"

    # ---- 服务 ----
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # ---- AI 增强（可选，关闭时系统必须仍可跑通）----
    LLM_ENABLED: bool = False
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # ---- 选址引擎默认参数 ----
    DEFAULT_GRID_SIZE_M: int = 30       # 分析网格边长（米）
    DEFAULT_MIN_AREA_HA: float = 1.0    # 候选地块最小面积（公顷）
    DEFAULT_TOP_N: int = 5
    # 用地规模容差（±比例）：用户在需求中提到占地面积时，候选地块面积须落在
    # [目标 × (1 − 容差), 目标 × (1 + 容差)] 区间内。
    # ⚠️ 0.5（±50%）只是**初期限定**，最终限值由算法设计人员按行业门类核定。
    # 前端对应位置：frontend/src/utils/area.ts → DEFAULT_AREA_TOLERANCE，两处须同步。
    DEFAULT_AREA_TOLERANCE: float = 0.5

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
