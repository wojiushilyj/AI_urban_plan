"""
AI_urban_plan · FastAPI 入口

启动：
    cd backend
    python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

接口文档：http://127.0.0.1:8000/docs
健康检查：http://127.0.0.1:8000/health

单端口部署：前端 `frontend/dist` 存在时会被挂到根路径 `/`，
浏览器只访问一个端口即可，接口走同源相对路径（无需 CORS、无需 Nginx）。
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

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

# ---------------------------------------------------------------------------
# 静态资源挂载（顺序敏感：必须先挂具体路径，最后挂根路径）
# ---------------------------------------------------------------------------

# 1) 处理后的 GeoJSON 图层：路径口径与前端 src/api/layers.ts 完全一致。
#    前端开发态由 Vite 从 frontend/public/data/layers 提供；
#    此处供单端口部署时使用，数据源与选址引擎同源（data/processed/geojson）。
_geojson_dir = settings.DATA_PROCESSED / "geojson"
if _geojson_dir.is_dir():
    app.mount("/data/layers", StaticFiles(directory=str(_geojson_dir)), name="layers-static")


class SpaStaticFiles(StaticFiles):
    """前端构建产物（dist）静态服务。

    本项目是单页工作台、未引入 vue-router，正常只会请求 `/`。
    但仍对未命中的路径回落 index.html：否则误敲一个不存在的路径时，
    用户看到的是 Starlette 的裸 404 JSON，而不是应用本身。
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


# 2) 前端 dist 挂到根路径。
#    ⚠️ 必须最后挂载，否则 `/` 会吞掉 /api、/docs、/health 等已注册路由。
#    目录不存在时跳过，此时服务退化为纯 API（本地后端联调场景）。
_dist_dir = settings.FRONTEND_DIST
if _dist_dir.is_dir():
    app.mount("/", SpaStaticFiles(directory=str(_dist_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    # 直接 `python main.py` 启动：监听地址与端口统一取自 .env（默认 0.0.0.0:8080）。
    # 传 app 对象而非 "main:app" 字符串，避免模块被二次导入。
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
