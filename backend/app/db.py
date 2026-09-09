"""SQLite 连接与初始化。小型本地数据库，零外部依赖。"""
import sqlite3
from pathlib import Path

from app.config import settings

SCHEMA = """
-- 选址场景模板
CREATE TABLE IF NOT EXISTS scenario (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,          -- 行业门类分类：采矿业 / 制造业 / 能源与公用事业 / 建筑业 / 交通与物流 / 信息技术服务 / 科技服务 / 环境与公共设施
    description TEXT,
    config_json TEXT NOT NULL,          -- 约束层、因子层、权重（JSON）
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 空间图层登记（实际几何存文件/GeoJSON，此处只登记元信息）
CREATE TABLE IF NOT EXISTS layer (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,          -- constraint | factor | base
    crs         TEXT NOT NULL,
    source      TEXT,                   -- 数据来源
    is_sample   INTEGER DEFAULT 0,      -- 1 = 样例数据，申报/演示中必须标注
    path        TEXT,
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);

-- 选址任务与结果
CREATE TABLE IF NOT EXISTS task (
    id           TEXT PRIMARY KEY,
    scenario_id  TEXT NOT NULL,
    aoi_geojson  TEXT,                  -- 研究区
    params_json  TEXT,                  -- 网格、权重、最小面积等
    result_json  TEXT,                  -- Top-N 候选地块
    status       TEXT DEFAULT 'pending',
    created_at   TEXT DEFAULT (datetime('now','localtime'))
);
"""


def get_conn() -> sqlite3.Connection:
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
