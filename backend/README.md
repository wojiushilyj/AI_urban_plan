# 后端 · 多场景智慧选址引擎

FastAPI + GeoPandas/Shapely + SQLite/GeoPackage。**无 Docker、无 PostGIS、无外部服务依赖**，拷贝即可运行。

## 一、快速启动

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows；Linux/macOS 用 source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

打开 http://127.0.0.1:8000/docs 查看交互式接口文档。

> 若 pip 拉包慢，可加国内镜像：
> `pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`

## 二、数据准备

引擎读取 `data/processed/layers.gpkg`（GeoPackage）。若该文件不存在，先运行预处理：

```bash
python scripts/preprocess.py           # 由 data/raw 的 SHP 生成 gpkg + GeoJSON
```

数据来源、坐标系与时点见 `data/README.md`。

## 三、接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查：数据是否就绪、图层数、坐标系 |
| GET | `/api/scenarios` | 行业门类模板列表（10 个门类） |
| GET | `/api/scenarios/{id}` | 单门类详情：硬约束 + 五维因子 + AHP 权重 |
| POST | `/api/selection/run` | **选址主流程**（见下） |
| GET | `/api/selection/result/{task_id}` | 取回历史任务结果（落库 SQLite） |
| GET | `/api/layers` | 空间图层清单（分组 + 要素数） |
| GET | `/api/layers/{id}` | 单图层 GeoJSON（EPSG:4490） |
| GET | `/api/layers/{id}/meta` | 单图层元信息 |
| POST | `/api/ai/parse` | 自然语言需求解析 → 门类 + 约束 + 规模 |
| POST | `/api/ai/chat` | 选址问答（规则版，无 Key 可用） |
| GET | `/data/layers/*.geojson` | 静态图层（与前端路径口径一致） |

## 四、选址主流程（POST /api/selection/run）

```
① 候选池   控规工业用地（regulated-industrial）∩ 研究区
② 硬约束   一票否决：生态保护红线、永久基本农田 + 城市蓝线、路网保护距离…
           （带 buffer 的约束先在 EPSG:4525 投影下做缓冲，再判相交）
③ 面积筛选 最小面积 min_area_ha
           + 用地规模区间 [目标×(1−容差), 目标×(1+容差)]（仅 target_area_ha 非空时生效）
           + 空结果自动放宽兜底（并在 message 中如实说明）
④ 因子量测 城市规划 / 交通物流 / 产业协同 / 基础配套 / 建造成本
           距离衰减 score = 100·exp(−d/d0)，STRtree 加速最近邻查询
⑤ 组合赋权 前端偏好权重 > AHP×α + 熵权×(1−α)
⑥ 排序     TOPSIS（默认）/ 多元回归 / K-Means 聚类优先
⑦ 输出     Top-N 候选地块（EPSG:4490 几何）+ 权重 ±20% 敏感性诊断
```

### 请求示例

```json
{
  "scenario_id": "G",
  "aoi": {"type": "Polygon",
          "coordinates": [[[110.0,25.0],[110.42,25.0],[110.42,25.5],[110.0,25.5],[110.0,25.0]]]},
  "grid_size_m": 30,
  "min_area_ha": 1.0,
  "top_n": 5,
  "alpha": 0.5,
  "algorithm": "topsis",
  "target_area_ha": 33.3,
  "area_tolerance": 0.5
}
```

```bash
curl -X POST http://127.0.0.1:8000/api/selection/run \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{"scenario_id":"G",
 "aoi":{"type":"Polygon","coordinates":[[[110.0,25.0],[110.42,25.0],[110.42,25.5],[110.0,25.5],[110.0,25.0]]]},
 "top_n":5,"algorithm":"topsis"}
JSON
```

### 无 HTTP 的引擎自测

```bash
<venv>/Scripts/python.exe scripts/engine_smoke.py            # 跑 B/C2/G/N 四个门类
<venv>/Scripts/python.exe scripts/engine_smoke.py G --area 33.3
```

## 五、坐标系约定（务必遵守）

| 用途 | 坐标系 | 说明 |
|---|---|---|
| 存储 / 输出 | **EPSG:4490** | CGCS2000 地理坐标，所有出入参几何 |
| **距离 / 面积量算** | **EPSG:4525** | CGCS2000 3度带 zone 37（CM 111E），桂林适用 |
| Web 展示 | EPSG:3857 | 前端 MapLibre 负责转换 |

⚠️ **严禁在 EPSG:4490（度）下直接计算距离或面积** —— 引擎内所有量算都先投影到 4525。

## 六、已知边界与如实声明

- 场景模板中 **居民点、饮用水源保护区、地质灾害、行洪区、机场净空、污染源** 六类约束
  目前**无对应图层数据**，引擎会跳过并在返回的 `message` 中列明，不静默忽略。
- 「城镇开发边界」是**正向因子**而非禁建区，因此不作一票否决。
- `area_tolerance` 默认 ±50% 为**初期限定**，最终限值需按行业门类核定
  （`app/config.py → DEFAULT_AREA_TOLERANCE`，与前端 `utils/area.ts` 须同步）。
- LLM 为可选增强，`LLM_ENABLED=false`（默认）时全流程走规则解析。
