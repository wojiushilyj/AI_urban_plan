"""
AI_urban_plan · FastAPI 入口

启动：
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

接口文档：http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import site_selection, scenarios

app = FastAPI(
    title="多场景智慧选址系统 API",
    description="国土 AI 竞赛｜多场景智慧选址系统 —— 约束叠加 + 多因子适宜性评价 + 候选地块生成",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok", "project": settings.PROJECT_NAME, "crs": settings.CRS_STORAGE}


app.include_router(scenarios.router, prefix="/api")
app.include_router(site_selection.router, prefix="/api")
