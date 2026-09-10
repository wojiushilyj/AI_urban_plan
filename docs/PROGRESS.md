# 进度日志

> **规则：每轮工作结束必须更新本文件。** 格式：日期 → 做了什么 → 当前状态 → 下一步 → 阻塞点。
> AI 读本文件时，请从底部最新条目开始看。

---

## 当前阶段
**阶段 2：后端选址引擎完成，前后端接口全部打通** ｜ 下一节点：**09-11 前端切真实后端联调 + 同步 docs/SCENARIOS.md**

## 当前阻塞点
- [x] GitHub 仓库已创建并推送 ✅
- [x] 前端全套 UI 已实现，mock 数据可独立演示 ✅
- [x] **后端选址引擎 + scenarios/layers/ai 路由已完成，54 项接口测试全通过** ✅
- [ ] `docs/SCENARIOS.md` 仍是旧 S1–S5 描述，与 10 门类不一致 ← 下一个要解决的
- [ ] 前端尚未切到真实后端（`VITE_USE_MOCK` 默认 true）
- [ ] 数据来源/时点细节待确认（`data/README.md` 中"待确认"项）
- [ ] 单位盖章流程（基本信息表 + 责任声明）

## Git 信息
- 远端：https://github.com/wojiushilyj/AI_urban_plan（**公开，已推送**）
- 提交身份：`wojiushilyj <7012750@qq.com>`
- 推送脚本：`scripts/push_to_github.sh`（用 GH_TOKEN 建仓并推送，推送后自动从远端 URL 中抹除令牌）
- 令牌有效期 90 天，到期前需重新生成；重新推送时用
  `git push https://wojiushilyj:<TOKEN>@github.com/wojiushilyj/AI_urban_plan.git main`

## 待定池（9-14 前不实现）
- 三维（Cesium）可视化
- 多用户与权限
- 与真实"一张图"平台的 API 对接
- 移动端适配

---

## 2026-09-07

**做了什么**
- 解析赛事通知（桂自然资办〔2026〕86 号），锁定赛道：**企事业单位 · 数智场景（赛题四，规划处）**。
- 确定项目名：国土 AI 竞赛｜多场景智慧选址系统（暂定）。
- 创建 GitHub 仓库 `AI_urban_plan`（公开）。
- 编写 `README.md` 总纲（AI 协作铁律、技术栈、目录、数据规范、倒排排期）。
- 编写 `AGENTS.md`、`docs/COMPETITION.md`、`docs/SCENARIOS.md`、`docs/DEMO.md`。
- 搭建前后端骨架：FastAPI 入口 + SQLite 初始化 + Vue3/Vite 前端占位。

**技术决策与理由**
- 数据库选 SQLite：评委"拷走即跑"，符合"小型本地数据库"定位，避免 Docker/PostGIS 依赖。
- GIS 前端选 MapLibre GL JS：开源免 Key，可挂载天地图/OSM 瓦片，规避付费 Key 卡演示的风险。
- 坐标系定 CGCS2000（EPSG:4490 存储 / EPSG:4545 量算 / EPSG:3857 展示），符合国土行业法定要求。

**当前状态**
骨架就绪，尚未实现业务逻辑。

**下一步（09-08）**
1. 确定演示区，建议南宁市或柳州市下辖县（数据可得性与辨识度平衡）。
2. 拉取/构造三区三线、DEM、路网、人口格网数据。
3. 编写 `scripts/preprocess.py` 统一转 EPSG:4490 并入库。
4. 确定团队信息与盖章流程（责任声明需单位盖章，提前走流程）。

---

## 2026-09-08

**做了什么**
- 拉取项目仓库 `AI_urban_plan`（main 分支，HEAD e79ff1b）。
- 按附件《国土AI智慧选址系统模块清单》实现**前端全套 UI（9 大模块）+ mock 数据层**，后端不动。
- 前端架构：Vue3 + Vite + TS + Element Plus + MapLibre GL JS + ECharts + Pinia（新增唯一依赖）。
- 目录：`src/{styles,types,mock,api,store,composables,components,views,utils}`，约 50 个文件。
- 9 大模块落地：顶部导航/场景切换、AI 需求交互（对话+模板+解析一键应用）、约束配置、权重配置（滑块自动归一化+算法选型 TOPSIS/回归/K-Means）、GIS 地图（底图切换/图层管理/热力图/候选地块/框选 AOI/测量/弹窗）、计算结果（进度日志/综合指标/候选表格/ECharts 三图/双向联动）、报告生成与导出（PDF 打印/Excel Blob/图纸 canvas）、后端接口对接（mock 分流）、通用组件。
- 场景模板 S1–S5 从 `backend/app/services/scenarios.py` 逐字复制到 `src/mock/scenarios.ts`。

**技术决策与理由**
- **保持 Element Plus**（非 TDesign）：遵守 README/AGENTS 铁律"不得擅自更换技术栈"，通过 CSS 变量定制浅色现代主题（主色 #1C7D8C 自然科技青蓝）。
- **范围 = 前端全套 + mock**：后端接口大量缺失，竞赛演示可用 `VITE_USE_MOCK=true` 全流程离线跑通，切换真实后端仅改 `.env`。
- **引入 Pinia**（9 大模块状态交叉共享）；**不引入 vue-router**（单页工作台）；导出不引重型库（PDF 走浏览器打印、Excel 用 Blob）。
- **算法选型按模块清单**呈现 TOPSIS/多元回归/K-Means 三选项（后端后续实现）。
- 修复 tsconfig：补 `esModuleInterop`（MapLibre 类型兼容）、`noImplicitAny: false`（Element Plus 全局注册致模板事件参数无法推断）。

**当前状态**
- `npm run build` 通过（vue-tsc 0 错误 + vite 打包成功，产物 dist/）。
- `npm run dev` 正常，访问 http://localhost:5173/ 可看到三栏工作台（顶栏/左 AI-约束-权重/中地图/右结果-图表-报告/底部状态栏）。
- 全流程 mock 可演示：选场景 → 框选 AOI → 调权重 → 开始选址 → 热力图+候选 → 表格/图表联动 → 报告导出。

**下一步（09-09）**
1. 补后端 `backend/app/routers/scenarios.py`（约 20 行，包装已就绪的 `list_scenarios/get_scenario`，返回 `{items:[...]}`）→ 后端才能启动。
2. 实现 `backend/app/services/suitability.py` 六函数（grid/filter_hard/normalize/weight/cluster/sensitivity）→ `/api/selection/run` 出真实结果。
3. 实现 `scripts/preprocess.py` + 准备 `data/` 样例数据（三区三线、DEM、路网、人口格网）。
4. 确定演示区与团队信息，走盖章流程。

---

## 2026-09-09（下午）

**做了什么（前端 UI 精简）**
- 顶栏去掉「方案管理」按钮与「竞赛模式」开关，仅保留「帮助」。
- 删除「约束配置」「权重配置」两个页面（LeftPanel 仅保留 AI 需求交互）。
- 删除「快捷模板」框（RequirementTemplates）。
- 研究区改为固定「桂林市临桂区」，移除地图框选（AOI 绘制）能力：`store/map.ts` 初始 AOI 固定为临桂区简化边界，`useMap.ts` 中心/兜底边界改为临桂区（[110.2, 25.24], zoom 11）。
- 地图工具条去掉「框选研究区」「定位」两个按钮，保留缩放/测距/测面积/出图。
- 「开始选址」按钮从权重页迁移到 AI 面板输入区（ChatPanel），权重和校验逻辑沿用。
- 删除死代码：`WeightEditor.vue`、`ConstraintConfig.vue`、`ConstraintPreview.vue`、`RequirementTemplates.vue`、`SchemeManager.vue`、`useAoiDraw.ts`。
- mock 候选/热力中心从南宁改为临桂区。

**技术决策与理由**
- 演示区定为临桂区：广西桂林市辖区，贴合「壮美广西」主题且辨识度高；数据用样例（SAMPLE）简化边界。
- 约束/权重收敛进 AI 自动解析 + 场景默认值，界面只暴露「选场景 → AI 描述 → 开始选址」极简链路，契合 3 分钟演示。

**当前状态**
- `npm run build` 通过（vue-tsc 0 错误 + vite 打包成功），`npm run dev` 正常，http://localhost:5173/ 可访问。
- 坑：换电脑后 `node_modules/.vite` 与 `dist` 触发 WorkBuddy safe-delete 拦截导致启动/构建失败，需先 `rm -rf node_modules/.vite` 与 `rm -rf dist`（带提权）再跑。

**下一步**
1. 继续 09-09 后端选址引擎与 scenarios 路由（见上）。
2. 若需真实临桂区边界/数据，替换 `store/map.ts` 的 `LINGUI_AOI` 与 `useMap.ts` 的兜底边界为真实数据。

---

## 2026-09-09（下午·二）

**做了什么（场景改为国民经济行业门类）**
- 顶部场景选择从 S1–S5 业务场景改为 **10 大国民经济行业门类**：B 采矿业、C1 制造业（消费品）、C2 制造业（原材料与中间品）、C3 制造业（装备设备）、D 电力热力燃气水、E 建筑业、G 交通仓储邮政、I 信息传输软件、M 科研技术服务、N 水利环境公共设施。
- 每个门类配置专属硬约束（含缓冲）与评价因子 + AHP 权重：如 C2 原材料制造要求居民点安全距离 500m、D 能源设施要求居民点 500m + 行洪区/机场净空、N 环境设施要求饮用水源保护区 + 500m 邻避距离等。
- 前后端同步：`frontend/src/mock/scenarios.ts` 与 `backend/app/services/scenarios.py` 逐字对齐。
- AI 关键词匹配（`mock/aiChat.ts`）从旧场景改写为 10 门类关键词，默认/兜底场景 id 由 S1 改为 B。
- 文案统一：帮助弹窗、AI 欢迎语、输入占位符、报告生成、ScenarioSwitcher 占位等由「场景」改为「行业门类」。
- `backend/app/schemas/selection.py` 默认 `scenario_id` 由 S1 改 B；`db.py` category 注释同步。

**技术决策与理由**
- 门类 id 直接用国民经济行业分类门类字母（B/C1/C2/C3/D/E/G/I/M/N）；C 制造业按产业链拆为消费品/原材料与中间品/装备设备三类，符合用户指定的 10 类口径。
- 因子与约束基于各行业通用选址逻辑设计（邻避设施安全距离、物流贴近交通节点、科研贴近高校等），仍为样例演示数据。

**当前状态**
- `npm run build` 通过，`npm run dev` 正常（http://localhost:5173/）。
- 提示：后端 `scenarios` 路由尚未接线（`routers/scenarios.py` 仍缺失，见上方阻塞点），前端仍走 mock。

**下一步**
1. 补后端 `routers/scenarios.py` 包装 `list_scenarios/get_scenario`，让后端真实返回 10 门类。
2. 同步更新 `docs/SCENARIOS.md`（仍描述旧 S1–S5 业务场景）。

---

## 2026-09-09（下午·三）

**做了什么（UI 视觉现代化重设计）**
- 按「现代简约 · 专业工具风」重设计全局视觉，**保留现有三栏布局与技术栈**（Vue3 + Element Plus，不换库）。
- `variables.css`：重构设计 token。中性色对比度提升（text-secondary #8A94A6→#66707E 等，达 WCAG AA）；统一圆角体系 6/8/12/全圆；阴影改冷色调弱化（rgba 灰蓝，非纯黑）；新增动效 token（--ease-out/--duration-*）与断点 token。
- `element-theme.css`：同步 Element Plus 变量，按钮 hover 上浮 + 按压回弹（transform/opacity），表格/标签页/对话框/弹层统一圆角与弱阴影。
- `base.css`：字体栈升级（HarmonyOS/system-ui + tabular-nums 数字等宽）；移除 `min-width:1280px`；加 `prefers-reduced-motion` 全局降级；滚动条美化。
- `layout.css`：三栏 → 响应式（桌面标准 / 平板收窄 / 移动端地图置顶、面板堆叠）。
- 组件微调：TopNav 品牌区层次、StatusBar 字号与「门类」标签、CardContainer 弱阴影、ScrollPanel 卡片间距（padding+gap）、CandidateTable 空状态文案修复。

**技术决策与理由**
- 品牌主色 #1C7D8C 保留（品牌连续性 + 红蓝之外的政府 GIS 青蓝），仅做中性色与质感校准，不做 AI 紫/渐变 slop。
- 动效仅用 transform/opacity + cubic-bezier，克制且尊重 reduced-motion，不引入 Motion/GSAP（避免技术栈变更与 bundle 膨胀）。
- 浅色锁定：底图为浅色 OSM/天地图，深色 UI 会与地图割裂，故不做 dark mode。

**当前状态**
- `npm run build` 通过，`npm run dev` 正常（http://localhost:5173/）。
- 移动端响应式为 CSS 级降级（地图置顶 + 面板堆叠），未做抽屉式交互，桌面为演示主场景。

**下一步**
1. 视需要做移动端抽屉式折叠交互（需 JS 交互）。
2. 继续后端 scenarios 路由与 docs/SCENARIOS.md 同步（见上）。

---

## 2026-09-09（下午·四）

**做了什么（全局玻璃拟态 2.0 / Glassmorphism 2.0）**
- 按 UI/UX Pro Max skill 将浅色简约风升级为玻璃拟态 2.0，**保留三栏布局与技术栈**。
- `variables.css`：新增玻璃 token（--glass-bg-soft/--glass-bg/--glass-bg-strong 三档不透明度 0.58/0.72/0.86、--glass-blur、--glass-saturate、--glass-border、--shadow-glass）；圆角 8→10/12→14 更圆润。
- `base.css`：body 加光晕渐变背景（青蓝/蓝绿/淡紫 4 层 radial-gradient，background-attachment: fixed）供玻璃透视；新增全局 `.glass` / `.glass-strong` 工具类 + `@supports` 降级（不支持 backdrop-filter 时退回高不透明实底）。
- `layout.css`：容器改透明透出光晕；左右面板半透明磨砂（blur 28px + saturate）。
- `element-theme.css`：对话框/抽屉/下拉弹层玻璃化。
- 组件玻璃化：TopNav、StatusBar、CardContainer、ChatPanel 输入区、地图浮层（MapToolbar 按钮改透明玻璃、MapLegend、BasemapControl、LayerManager）。

**技术决策与理由**
- 玻璃拟态 2.0 关键：面板用**高不透明度（≥0.58，卡片 0.72，弹层 0.86）**避免 1.0 的可读性问题；文字用深色 #16222E（skill 对比度规则：玻璃卡浅色模式用 white/80+、文字 slate-900 而非 slate-400）。
- 地图浮层（工具条/图例/底图/图层）玻璃效果最出彩——直接 blur 底图内容；左右面板只做轻透（0.58），保证密集文字可读。
- 品牌青蓝 #1C7D8C 不变，仅背景加青蓝/蓝绿/淡紫光晕。

**当前状态**
- `npm run build` 通过，`npm run dev` 正常（http://localhost:5173/）。
- backdrop-filter 已配 -webkit- 前缀（Safari）+ @supports 降级（旧浏览器退回实底）。

**下一步**
1. 视需要做移动端抽屉式折叠交互（需 JS）。
2. 继续后端 scenarios 路由与 docs/SCENARIOS.md 同步。

---

## 2026-09-09（下午·五）

**做了什么（底图与候选地块交互）**
- 底图按钮标签简化为「OSM / 矢量 / 影像」（`useMap.ts` BASEMAPS name 短化，`BasemapControl` 去掉 replace）。
- 默认底图改为**天地图矢量**（`store/map.ts` basemap 默认 'tianditu-vec'；`useMap.ts` init 增加 `basemap` 参数 + `resolveStyle` 按 Key 可用性回退 OSM；`MapStage` onMounted 传当前 basemap）。`.env` 已有 `VITE_TIANDITU_KEY`。
- 删除地图图例左下角「研究区 · 临桂区」行（`MapLegend` 去掉 aoi 行与 `mapStore` 依赖，仅在出结果时显示适宜度/候选地块图例）。
- 候选地块点击交互：**不再弹 popup 卡片**，改为「选中地块放大居中 + 加粗描边」——`MapStage` onParcelClick 仅设 `selectedRank`，删除 `showParcelPopup` 与 `ParcelPopup.vue`；selectedRank watch 由 flyTo 质心改为 `fitBounds`（padding 140, maxZoom 16）；`useMapLayers` renderCandidates 选中地块 line-width 1.5→5、line-color 加深 #0E4A53、fill-opacity 0.5→0.7。

**技术决策与理由**
- 放大居中用 fitBounds + 大 padding，保证地块完整可见且居中；加粗描边用 case 表达式按 rank 区分，避免新增图层。

**当前状态**
- `npm run build` 通过（2318 modules），`npm run dev` 正常（http://localhost:5173/）。

**下一步**
1. 视需要做移动端抽屉式折叠交互（需 JS）。
2. 继续后端 scenarios 路由与 docs/SCENARIOS.md 同步。

---

## 2026-09-09（下午·六）

**做了什么（地图浮层精简 + 候选地块红色描边与右侧卡片）**
- 移除地图左下角图例（`MapLegend.vue` 删除）、右下角放大缩小按钮（`NavigationControl`）与天地图/OSM 版权控件（`AttributionControl`，`useMap.ts` init 内删两行 addControl）。
- 候选地块选中描边改为**红色 #E5484D**（`useMapLayers` renderCandidates 选中 line-color）。
- 新增地图右侧贴边浮动卡片 `ParcelInfoCard.vue`：选中地块时右侧贴边弹出，显示综合得分（大号红色）、面积、评估结论、各指标得分，带滑入动效与关闭按钮；`MapStage` 加 `selectedParcel`/`factorNames` computed + 渲染 + `@close` 清空 `selectedRank`。

**技术决策与理由**
- 右侧卡片用 `position:absolute; right; top:50%` 贴边垂直居中，玻璃拟态样式与全局一致；得分用红色呼应选中描边。
- 移除版权控件符合演示诉求；注意：正式公开部署需按 OSM/天地图条款保留 attribution，此处为竞赛演示内部使用。

**当前状态**
- `npm run build` 通过（2318 modules），`npm run dev` 正常（http://localhost:5173/）。

**下一步**
1. 视需要做移动端抽屉式折叠交互（需 JS）。
2. 继续后端 scenarios 路由与 docs/SCENARIOS.md 同步。

---

## 2026-09-09（下午·七）

**做了什么（门类上移 + 选址偏好 5 维度）**
- 行业门类选择器从顶栏移到**左侧 AI 聊天框上方**（`TopNav` 移除 ScenarioSwitcher，`ChatPanel` 顶部新增 config 区）。
- 门类下方新增「选址偏好」卡片 `PreferenceCard.vue`：5 个统一维度（城市规划/交通物流/产业协同/基础配套/建造成本）× 三档单选（在意/一般/不在意）。
- **评分与权重统一改为 5 维度**：`store/config.ts` 新增 `FACTOR_DEFS`（5 维度）、`PREFERENCE_LEVELS`（三档权重基值 5/3/1）、`preferences`、`computeWeights`（自动归一化）、`setPreference`；`applyScenario` 权重改为由偏好计算。
- 前后端 scenarios 的 `factors`/`weights_ahp` 统一为 5 维度（`mock/scenarios.ts` + `backend/app/services/scenarios.py`）。
- `ParseResult` 去掉「初始权重」展示与权重覆盖（AI 只识别门类 + 建议约束）；AI 欢迎语/解析文案/对话回复同步改为「权重由选址偏好决定」。

**技术决策与理由**
- 权重 = 三档偏好（在意 5 / 一般 3 / 不在意 1）归一化，权重和恒为 1；评分按统一 5 维度打分（mock 因子生成遍历 `scenario.factors`）。
- 门类仍各保留专属硬约束（如 C2 居民点 500m、D 行洪区等），约束与偏好解耦。

**当前状态**
- `npm run build` 通过（2321 modules），`npm run dev` 正常（http://localhost:5173/）；后端 scenarios.py 语法校验通过。

**下一步**
1. 继续后端 scenarios 路由与 docs/SCENARIOS.md 同步。
2. 视需要做移动端抽屉式折叠交互（需 JS）。

---

## 2026-09-10

**做了什么（真实规划数据入库 + 前端图层分类管理）**
- 用户提供 12 个真实规划 SHP（桂林临桂区，**非样例**，UTF-8）。实测坐标系为 **CGCS2000 3 度带 zone 37（CM 111E，EPSG:4525，带号坐标）**，仅「永久基本农田」「生态保护红线」带 .prj，其余 9 个缺 .prj 经坐标范围校验统一补声明。
- 重写 `scripts/preprocess.py`：12 shp → 补 CRS → 转 EPSG:4490 存 GeoPackage（`data/processed/layers.gpkg`，SQLite 形式）+ 转 EPSG:4326 出 GeoJSON（`data/processed/geojson/` 与 `frontend/public/data/layers/` 双份）。
- **校正坐标系**：README §4 / `backend/app/config.py` / `suitability.py` 的投影坐标系 EPSG:4545（CM 108E）→ **EPSG:4525**（zone 37，CM 111E，桂林适用）。
- 登记 `data/README.md`：12 个真实图层清单，来源与时点暂填"桂林市临桂区规划成果 / 2026-09 获取"待确认。
- **前端图层分类管理**：`store/map.ts` 图层改分组结构（5 大类）；`LayerManager.vue` 分组 UI（大类总开关 + 每图层单开关 + 点击展开/收缩）；`useMapLayers.ts` mock 几何改为 `renderGeoLayers` 懒加载真实 GeoJSON；`MapStage.vue` 业务图层渲染不依赖结果守卫。
- `.gitignore` 新增 `frontend/public/data/`（真实数据严禁入库）。

**技术决策与理由**
- 存储用 GeoPackage（本质 SQLite，符合"小型本地数据库"定位 + 评委拷走即跑），GeoJSON 仅作**出图/交换格式**，不是存储格式。
- 真实数据不入 git（README 铁律），评委环境运行 `preprocess.py` 重新生成即可。

**当前状态**
- `npm run build` 通过（2318 modules，vue-tsc 0 错误），dev server http://localhost:5173/ 正常，`/data/layers/*.geojson` 静态可访问（中文字段、坐标、7.5MB 大图层均验证）。

**下一步**
1. 后端 `/api/layers` 接口（从 gpkg 读图层返回 GeoJSON），前端切换到 API 加载。
2. 确认数据来源/时点细节，补全 `data/README.md` 与申报书数据声明。
3. 后端 scenarios 路由与选址引擎接线（仍未完成）。

---

## 2026-09-10（晚间·后端选址引擎）

**做了什么**
- **补齐启动阻塞点**：新建 `backend/app/routers/scenarios.py`（此前缺失导致 `main.py` import 失败，后端根本起不来）。
- **实现真实选址引擎** `backend/app/services/suitability.py`（原为 NotImplementedError 返回 501）：
  候选池（控规工业用地 145 图斑）→ 硬约束一票否决（生态红线/永久基本农田/城市蓝线/路网缓冲）→
  面积筛选（最小面积 + 目标规模区间 + 兜底放宽）→ 五维因子真实空间量测 → 组合赋权 → 三种算法排序 → Top-N。
- **新增空间数据服务** `backend/app/services/spatial.py`：从 GeoPackage 读取 16 个图层、CRS 统一、
  投影缓存、GeoJSON 输出（剔除 Shape_Length/Shape_Area 等内部字段）、STRtree 加速。
- **新增图层接口** `/api/layers`、`/api/layers/{id}`、`/api/layers/{id}/meta`，并把 GeoJSON 挂到
  `/data/layers` 静态路径，与前端 `api/layers.ts` 路径口径一致（后端可独立部署）。
- **新增 AI 接口** `/api/ai/parse`、`/api/ai/chat`（规则版，无 Key 可用；换算口径与前端 utils/area.ts 对齐）。
- **选址结果落库**：写入 SQLite `task` 表，新增 `GET /api/selection/result/{task_id}` 读回。
- **测试脚本**：`scripts/engine_smoke.py`（无 HTTP 直测引擎）、`scripts/api_smoke.py`（HTTP 层 54 项断言）。
- `backend/README.md`：启动方式、接口一览、算法口径、坐标系约定、已知边界。
- `frontend/.env.example`：`VITE_USE_MOCK` 切换说明。

**技术决策与理由**
- **约束默认只启用 required 项**：库里只有「道路路网」而没有「高速/铁路」专层，若对全部道路一律加
  100m 缓冲，145 个候选图斑会被剔到只剩 3 个——那是把约束用错，不是地块真的不合规。
  因此 `required=false` 的约束改为**按需启用**（请求传 `constraints` 显式开启）。
- **"城市规划"因子公式修正**：边界外用「形态规模得分 × 0.55」，严格低于边界内的 60 分基准，
  避免"距开发边界越近分越高"的逻辑倒挂（原公式存在该隐患）。
- **得分与排序解耦**：K-Means 模式最初把聚类优先级混入分值（×1000），导致 Top-5 得分清一色 96.0，
  失去区分度。改为**聚类只影响排序、得分仍用 TOPSIS 贴近度**。
- **如实声明数据缺口**：模板中的居民点、饮用水源保护区、地质灾害、行洪区、机场净空、污染源
  六类约束**无对应图层**，引擎跳过并在 `message` 中逐条列明，绝不静默忽略。

**当前状态**
- 后端可启动（`uvicorn main:app --port 8000`），`scripts/api_smoke.py` **54 项断言全部通过**。
- 实测（门类 G，临桂区 AOI）：候选池 145 → 可行 107 → Top-5，单次计算约 150ms（冷启动首帧稍慢）。
- 三种算法得分均有区分度；面积约束（目标 8 公顷 ±50%）正确筛出 4–12 公顷地块 50 个。
- 权重敏感性分析：Top-5 在两个维度 ±20% 扰动下最低重合率 0.8。

**下一步（09-11）**
1. `docs/SCENARIOS.md` 重写为 10 门类口径（当前仍是旧 S1–S5，申报书若照抄会出错）。
2. 前端切真实后端联调（`frontend/.env` 置 `VITE_USE_MOCK=false`），核对几何渲染与候选卡片。
3. 补齐 data/README.md 的数据来源与时点（当前 12 个图层来源标注为"待确认"）。

---
