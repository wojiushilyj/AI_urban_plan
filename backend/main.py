"""
AI_urban_plan · FastAPI 入口

启动：
    cd backend
    python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

接口文档：http://127.0.0.1:8000/docs
健康检查：http://127.0.0.1:8000/health
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import init_db
from app.routers import ai, layers, scenarios, site_selection


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="多场景智慧选址系统 API",
    description=(
        "国土 AI 竞赛｜多场景智慧选址系统 —— "
        "硬约束一票否决 + 五维因子适宜性评价 + 多准则排序（TOPSIS / 多元回归 / K-Means）"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["系统"])
def health():
    """健康检查：确认服务在线、数据就绪。"""
    from app.services import spatial

    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "crs": {"storage": settings.CRS_STORAGE, "measure": settings.CRS_PROJECTED},
        "gpkg_exists": spatial.GPKG_PATH.exists(),
        "layers": len(spatial.available_layer_ids()),
        "llm_enabled": settings.LLM_ENABLED,
    }


app.include_router(scenarios.router, prefix="/api")
app.include_router(site_selection.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
app.include_router(ai.router, prefix="/api")

# 把处理后的 GeoJSON 图层挂到 /data/layers，与前端 api/layers.ts 的路径口径一致。
# 前端开发态由 Vite 从 frontend/public/data/layers 提供；此处供后端独立部署时使用。
_geojson_dir = settings.DATA_PROCESSED / "geojson"
if _geojson_dir.is_dir():
    app.mount("/data/layers", StaticFiles(directory=str(_geojson_dir)), name="layers-static")
