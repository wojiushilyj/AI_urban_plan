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
| GET | `/api/ai/model` | **AI 偏好学习模型**：AUC、学习权重、消融实验、泄漏审计 |
| GET | `/api/ai/model/parcels` | 模型训练样本明细（供可视化） |
| GET | `/data/layers/*.geojson` | 静态图层（与前端路径口径一致） |

## 四、选址主流程（POST /api/selection/run）

```
① 候选池   控规工业用地（regulated-industrial）∩ 研究区
② 硬约束   一票否决：生态保护红线、永久基本农田 + 城市蓝线、路网保护距离…
           （带 buffer 的约束先在 EPSG:4525 投影下做缓冲，再判相交）
③ 面积筛选 最小面积 min_area_ha
           + 用地规模区间 [目标×(1−容差), 目标×(1+容差)]（仅 target_area_ha 非空时生效）
           + 空结果自动放宽兜底（并在 message 中如实说明）
④ 因子量测 城市规划 / 交通物流 / 产业协同 / 基础配套 / 建造成本（含拆迁量）
           距离衰减 score = 100·exp(−d/d0)，STRtree 加速最近邻查询
⑤ 组合赋权 weight_mode: expert（AHP×α + 熵权×(1−α)）/ learned（AI 学习）/ blended
⑥ 排序     TOPSIS（默认）/ 多元回归 / K-Means 聚类优先
⑦ 输出     Top-N 候选地块（EPSG:4490 几何）
           + 因子贡献分解（留一法，优势/短板）
           + 蒙特卡洛入选概率（200 次扰动）
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
  "weight_mode": "expert",
  "algorithm": "topsis",
  "target_area_ha": 33.3,
  "area_tolerance": 0.5
}
```

> `weight_mode` 是 AI 能力的接入点：`expert`（默认，专家知识主导）／
> `learned`（从临桂区真实开发事实学到的权重）／`blended`（两者各半）。
> 注意：`weights_override` 优先级高于 `weight_mode`，非 expert 模式下请勿传。

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

## 六、AI 能力（三处可验证的算法能力）

模块位置：`app/services/ai_model.py`（偏好学习）、`app/services/features.py`（特征工程）、
`app/services/suitability.py`（可解释性与稳健性）。**零新增依赖**，仅用 numpy 实现。

### 1. 偏好学习：从真实开发事实反推权重

- 样本：控规工业用地 **145** 个地块；标签 = 是否已被实际开发（现状工业覆盖 > 5%）→ 66 正 / 79 负
- 特征：4 个规划因子 + **周边建成度**（500 m 环形邻域建筑占地率）
- 模型：L2 正则逻辑回归；5 折**分层**交叉验证 **AUC 0.693 ± 0.086**
- 接入：请求字段 `weight_mode`

```bash
curl -s http://127.0.0.1:8000/api/ai/model | python -m json.tool | head -40
<venv>/Scripts/python.exe scripts/ai_model_smoke.py     # 含消融实验与泄漏审计
```

### 2. ⚠️ 数据泄漏审计（必须知道的三条）

| 曾用特征 | 问题 | 处理 |
|---|---|---|
| 产业协同用**现状**工业算集聚距离 | 标签来源就是与现状工业的重叠率 → 距离 ≈ 0 即等价于已开发 | 改回**总规**工业用地 |
| 建造成本含**本地块**建筑占地率 | 有建筑 ⇔ 已开发 | cost 不参与训练 |
| 周边建成度用 **buffer** | 地块自身建筑混入邻域 | 改用 `buffer.difference(地块)` 取环带 |

**带泄漏版本 AUC 0.957，修正后 0.640。** 修改特征前务必先想清楚「这个量的标签来源是不是同一个图层」。

### 3. 可解释性与稳健性

- **因子贡献分解（留一法）**：把某因子替换为全域均值后重算排序分，差值即边际贡献。
  正值 = 优势，负值 = 短板。模型无关，对 TOPSIS 同样适用。
- **蒙特卡洛入选概率**：权重按 Dirichlet 扰动 200 次（≈±20%），统计各候选保持在 Top-N 的
  频率。比单一确定性排名更能支撑「要不要上报」这类决策。

## 七、已知边界与如实声明

- **AI 模型样本量仅 145**（受限于临桂区控规工业地块总量），AUC 约 0.69、折间波动 ±0.09。
  **该模型提供权重参照，不作为选址最终依据**；默认权重来源仍是专家 AHP + 熵权。
- 规划因子对本区实际开发的解释力有限（AUC 0.64），说明开发决策还受供地节奏、招商、
  产权等**非空间因素**主导 —— 这本身是有价值的结论。
- 场景模板中 **居民点、饮用水源保护区、地质灾害、行洪区、机场净空、污染源** 六类约束
  目前**无对应图层数据**，引擎会跳过并在返回的 `message` 中列明，不静默忽略。
- 「城镇开发边界」是**正向因子**而非禁建区，因此不作一票否决。
- 「河湖管理范围」用城市蓝线代理、「高速/铁路安全保护距离」用道路路网代理且**默认不启用**
  （路网含全部等级道路，一律加 100 m 缓冲会把候选从 145 剔到 3）。
- `area_tolerance` 默认 ±50% 为**初期限定**，最终限值需按行业门类核定
  （`app/config.py → DEFAULT_AREA_TOLERANCE`，与前端 `utils/area.ts` 须同步）。
- LLM 为可选增强，`LLM_ENABLED=false`（默认）时全流程走规则解析。
