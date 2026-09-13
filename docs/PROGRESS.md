# 进度日志

> **规则：每轮工作结束必须更新本文件。** 格式：日期 → 做了什么 → 当前状态 → 下一步 → 阻塞点。
> AI 读本文件时，请从底部最新条目开始看。

---

## 当前阶段
**阶段 3：业务图层扩充至 18 个，前后端接口全通** ｜ 下一节点：**09-12 演示脚本定稿 + 申报书数据部分**

## 当前阻塞点
- [x] GitHub 仓库已创建并推送 ✅
- [x] 前端全套 UI 已实现，mock 数据可独立演示 ✅
- [x] **后端选址引擎 + scenarios/layers/ai 路由已完成，56 项接口测试全通过** ✅
- [x] `docs/SCENARIOS.md` 已重写为 10 门类口径 ✅
- [x] 前端已切真实后端（`VITE_USE_MOCK=false`），契约校验 30 项通过 ✅
- [x] 业务图层扩充至 **18 个**（新增市政设施、现状建设两个大类）✅
- [ ] **数据时点逐层确认**（`data/README.md`「时点待补充」表，16→18 个图层）← 卡在用户
- [ ] 单位盖章流程（基本信息表 + 责任声明）← 卡在用户，**最迟 09-12 必须启动**
- [ ] 演示脚本 / 3 分钟视频分镜未定稿

## Git 信息
- 远端：https://github.com/wojiushilyj/AI_urban_plan（**private**，2026-09-11 用户要求改回）
  ⚠️ 若申报书要填「作品展示链接」，提交前必须改回 public
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

## 2026-09-11

**做了什么（业务图层 16→18，commit 6dd3405）**
- 新增「工业配套市政用地」`municipal-land`（81 面，153.2 ha）→ 新建**市政设施**大类。
  属性：用地（国标代码 7 类）/名称/等级/状态/设施类/规模/备注。
- 新增「现状建筑分布」`current-building`（7851 面，634.6 ha）→ 新建**现状建设**大类。
  属性：区域（苏桥/秧塘/乐和/两江/大圆盘）、层数（1 层 3830 / 2 层 3027 / 3 层 994）。
- 大类顺序：底线管控 > 城市控制线 > 产业用地 > 服务与设施 > 交通设施 > **市政设施** > **现状建设** > 选址结果。
- 前端：`api/layers.ts` +2 id；`store/map.ts` +2 大类 +2 图层；
  `useMapLayers.ts` 的 `LayerStyle` 新增 `fillPaint?`（此前只有 `linePaint`，面图层只能纯色），
  市政用地按用地代码 match 着色（7 色），现状建筑按层数着色（鹅黄系，透明度 0.4）。
- 数据管线：`preprocess.py` 的 LAYERS / GROUPS 各 +2（含属性白名单）。
  市政用地含 1 条录入异常值「1303供电用电」，渲染用 `['slice',['get','用地'],0,4]` 取前 4 位匹配，
  异常值可正确落到"供电"色。

**技术决策与理由**
- **归类决策**：市政用地属工程性市政基础设施，与「服务与设施」（生产性服务业 + 文保）性质不同，
  单独成类；建筑轮廓不是"用地"，与产业用地口径不同，单独成类。不强行并入旧 4 大类。
- 两个新图层均缺 `.prj`，按同批补声明为 `EPSG:4525` 并做坐标范围反算校验。

**当前状态**
- 图层总数 18，七个大类；前端/后端/manifest/preprocess 四处引用完全对齐。
- ⚠️ **本轮未更新本文件**（违反"每轮工作结束必须更新 PROGRESS.md"铁律），
  本条由 09-11 下午的会话补记 —— 提醒后续 AI：commit 前先看这条规矩。

**09-11 下午的补强（同会话）**
- 修复 `scripts/api_smoke.py` 中写死的 `16 个图层` 断言 → 改为读取 `layers_manifest.json`
  动态比对。**此前每新增一个图层该测试就会假失败**，属于测试本身的设计缺陷。
- 重启后端（清 `lru_cache`）后全量回归：
  - `scripts/api_smoke.py` **56 项通过**（+2 项：图层数与清单一致、全部图层可用）
  - `scripts/contract_check.py` **30 项通过**（经 Vite 代理 → 后端全链路）
  - `scripts/engine_smoke.py` 门类 G：候选池 145 → 可行 107 → Top-5，170 ms
- 新图层经前端可访问性验证：`municipal-land` 81 图斑 / 171 KB、`current-building` 7851 图斑 / 2.3 MB

**下一步（09-12）**
1. 逐层确认数据时点（`data/README.md`「时点待补充」表，现为 18 个图层）。
2. 演示脚本与视频分镜定稿（`docs/DEMO.md`）。
3. 启动盖章流程（基本信息表 + 责任声明）。
4. 考虑将 `current-building` 的「建筑密度」接入「建造成本」因子（当前 cost 只用面积与规整度）。

---

## 2026-09-11（下午·AI 能力建设）

**背景**：此前系统全部是 MCDA 多准则决策，**没有真正的 AI**。评委必问「AI 体现在哪」，
这是当时最大的软肋。本轮补齐。

**做了什么**

1. **偏好学习模型** `services/ai_model.py`（新增）
   - 样本：控规工业用地 145 地块；标签 = 是否已被实际开发（现状工业覆盖 > 5%）→ 66 正 / 79 负
   - 特征：4 规划因子 + 周边建成度（500m 环形邻域建筑占地率）
   - 模型：L2 正则逻辑回归（numpy 自研，零新增依赖）+ 5 折分层交叉验证
   - **AUC 0.693 ± 0.086**，准确率 0.663
2. **特征工程收敛** `services/features.py`（新增）
   - 把 RefSet、衰减函数、因子公式、建筑密度、邻域特征全部收敛到一处
   - 保证「模型学的因子」与「引擎打分的因子」严格同源，否则权重无法对接
3. **建造成本纳入拆迁量**：`cost = 8 + 45×规整度 + 45×min(面积/8,1) − 55×建筑占地率`
   - 数据来自新图层 `current-building`（7851 建筑轮廓）
   - 实测控规地块建筑占地率均值 13%、最高 87%，区分度显著
4. **可解释性**：因子贡献分解（留一法），输出每个候选地块的优势/短板
5. **稳健性**：蒙特卡洛 200 次权重扰动 → 各候选的 Top-N 入选概率
6. **权重来源切换**：`weight_mode` = expert（默认）/ learned / blended
7. **新接口**：`GET /api/ai/model`（模型指标与学习权重）、`GET /api/ai/model/parcels`（样本）
8. **前端展示**：新增 `AiModelCard.vue`（AUC、学习权重 vs 专家权重对比、消融实验、
   能力边界声明、权重来源切换）；`ParcelInfoCard.vue` 增加因子贡献条与入选概率
9. **测试**：`scripts/ai_model_smoke.py`（模型自测 + 泄漏审计断言）

**⚠️ 关键发现：数据泄漏审计**

初版把「产业协同用现状工业算距离」放进特征，AUC 冲到 **0.957**。
但标签来源正是「与现状工业用地的重叠率」—— 距离 ≈ 0 等价于已开发，这是定义性泄漏。

审计并剔除三处泄漏后，AUC 回落到 **0.640**（4 因子）→ 0.693（加周边建成度）。
**高 AUC 全是作弊来的。** 已在文档中如实记录，申报书与答辩应主动说明：
宁可报告诚实的 0.69，不要漂亮的假指标。

同时发现了**索引错位 bug**：`X` 还是 6 列而特征名只剩 5 个，导致消融实验张冠李戴
（「周边建成度」实际读到「邻域聚集」列）。已加断言防复发。

**当前状态**
- `scripts/api_smoke.py` **96 项通过**（+40 项 AI 相关）
- `scripts/contract_check.py` **45 项通过**（+15 项）
- `scripts/ai_model_smoke.py` **7 项通过**
- `vue-tsc --noEmit` 0 错误；`vite build` 成功（2326 模块）
- 三种 weight_mode 实测均可用，learned 与 expert 产出不同排序

**能力边界（必须在申报书/答辩中如实说明）**
- 样本仅 145，AUC 约 0.69、折间 ±0.09，**模型提供权重参照，不作为选址最终依据**
- 规划因子单独解释力有限（0.64），说明开发还受供地节奏、招商等非空间因素主导

**下一步（09-12）**
1. 逐层确认数据时点（18 个图层）
2. 演示脚本与视频分镜定稿（`docs/DEMO.md`）
3. 启动盖章流程 ← **最迟 09-12 必须启动**

---

## 2026-09-12（VPS 部署 · 单端口全栈）

**做了什么**
- 部署形态定为 **单端口全栈**：FastAPI 一个进程同时托管前端页面与 API，对外端口 **8080**
  （VPS 放行区间 8000–10000 内）。前端 axios `baseURL='/'` 走同源相对路径，
  因此**不需要 Nginx、不需要配 CORS**。
- `backend/main.py`
  - 新增 `SpaStaticFiles`（未命中路径 404 时回落 `index.html`）；
  - 在**所有路由之后**才把 `frontend/dist` 挂到根路径 `/`；挂载顺序为
    `/data/layers` → `/`，否则根路径会吞掉 `/api`、`/docs`、`/health`；
  - 新增 `__main__` 入口：`python main.py` 即按 `.env` 启动（传入 app 对象，避免模块二次导入）。
- `backend/app/config.py`：新增 `FRONTEND_DIST = ROOT_DIR/frontend/dist`。
- `backend/.env`（新增，不进 Git）：`API_HOST=0.0.0.0`、`API_PORT=8080`；`.env.example` 同步说明。
- `frontend/.env.vps`（新增）：`VITE_USE_MOCK=false`；`package.json` 新增 `npm run build:vps`
  （`vite build --mode vps`）。**本地 `npm run build` 仍产出 mock 版，两者互不影响。**
  `.gitignore` 放行 `!.env.vps`、忽略 `deploy/`。
- 组装 `deploy/vps/AI_urban_plan/`：backend 源码 + `data/processed` 真实数据
  （layers.gpkg 12.8 MB / 18 图层）+ `frontend/dist` + 5 个 .bat + `DEPLOY.md`；
  另附 `_fallback/mock-demo/` 纯前端应急版（后端装不上时兜底）；产出
  `deploy/vps/AI_urban_plan_vps_8080.zip` 便于远程桌面整包复制。

**本地实测（本轮最重要的事）**
- 本地建 `backend/.venv` 实装依赖，实际解析到 **starlette 1.6.0 / pandas 3.0.5 / numpy 2.5.3 /
  geopandas 1.1.4**（均为较新大版本，存在兼容风险）—— **实测全部兼容**，无导入或运行期错误。
  这条务必记住：`requirements.txt` 只写下限，装出来的大版本已跨过 starlette 1.0 与 pandas 3.0。
- `python main.py` 单端口启动成功，监听 `0.0.0.0:8080`。
- 专项验证（全部通过）：`/` 200 html、`/docs` 200、`/health`（`gpkg_exists=true`、`layers=18`、
  `EPSG:4525`）、`/data/layers/*.geojson` 200 且 UTF-8 中文正常、`/api/layers` 200、
  SPA 兜底 `/not-exist-page` 返回 index.html。
- `scripts/api_smoke.py http://127.0.0.1:8080`：**96 项通过 / 0 失败**
  （候选池 145 → 可行 107 → Top-5；三种算法；AUC 0.693；三种 weight_mode；蒙特卡洛 200 次）。

**技术决策与理由**
- 选单端口而非双端口：前端所有请求本来就是相对路径，同源托管零改动、零跨域、只需开一个端口；
  双端口反而要改前端地址重新构建，并多一个进程要维护。
- 用独立 `--mode vps` 而不是直接改 `.env`：本地离线演示（mock）与服务器真实演示（真后端）
  两种构建产物必须能共存，否则改一个坏一个。
- 打包脚本用纯 ASCII 文件名与内容（`1-install.bat` 等）：Windows 批处理对非 ASCII 编码极敏感，
  中文说明一律放 `DEPLOY.md`。

**当前状态**
- 部署包已就绪且本地全链路验证通过，等待用户在 VPS 上执行
  `1-install.bat` → `3-firewall.bat` → `2-start.bat`，再访问 `http://<VPS公网IP>:8080/`。
- ⚠️ 本轮改动**尚未 commit**（后端 2 个文件 + 前端 3 个配置 + .gitignore + 本文件）。

**下一步（09-13）**
1. VPS 实际部署 + `/health` 复核（`gpkg_exists` 必须为 true、`layers` 必须为 18）。
2. 逐层确认数据时点（18 个图层，`data/README.md` 仍有「时点待补充」表）。
3. 演示脚本与视频分镜定稿；启动盖章流程。

**已知问题 / 提醒**
- 前端 JS 单文件 3.0 MB（gzip 957 KB），未做代码分割，首屏偏慢；不影响演示，可后续优化。
- `VITE_TIANDITU_KEY` 为空 → 底图回退 OSM 公共瓦片；若要天地图，填 Key 后须重新
  `npm run build:vps` 并替换 `dist`。
- 服务以 `0.0.0.0:8080` 对公网开放且**无任何鉴权**，演示结束应停服或收敛安全组来源 IP。

---

## 2026-09-12（DeepSeek + 天地图 Key 接入）

**背景**：用户要求把天地图 API 与 DeepSeek API 接进系统。排查后发现一个**必须如实说明的缺口**：
后端 `LLM_ENABLED / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL` 四项此前**只是占位配置**，
全项目只在 `config.py`（定义）、`main.py`（health 回显）、`ai_parse.py`（拼一句提示文案）出现，
**没有任何发起大模型请求的代码** —— 填了 Key 也不会真的调用。

**做了什么**

1. **新增 `backend/app/services/llm.py`** —— DeepSeek / 任意 OpenAI 兼容接口客户端
   - `llm_available()` 判定四项配置是否齐全；`chat()` 返回文本、`chat_json()` 解析 JSON 对象
   - 超时 30 s、重试 1 次；**任何异常（网络/鉴权/限流/格式）一律吞掉返回 None**，不抛异常
   - `chat_json` 容错两轮提取：剥离 ` ```json ` 围栏、从夹带解释文字中正则抠出 JSON
   - 日志只截取错误体前 200 字符，避免凭据进日志
2. **改造 `backend/app/services/ai_parse.py`**（规则版为基线 + LLM 增强）
   - `parse_requirement`：关键词识别门类与正则抽取面积为**基线**；LLM 可修正门类、补齐面积、润色结论
     - 输出全部经校验：`scenarioId` 必须在 `SCENARIOS` 内、面积必须在 `MIN_HA~MAX_HA` 内，非法即忽略
     - **确定性换算优先**：规则已解析出面积时不采信模型数值（防模型算错单位）
     - 返回体新增 `llmEnhanced` 字段，前端可据此提示"本次结论由大模型增强"
   - `chat_reply`：配置 Key 时由 LLM 接管，未配置或失败时回退原确定性 FAQ
     - 系统提示词注入项目真实口径（研究区、18 图层、1 公顷=15 亩、EPSG:4525、约束规则、
       5 维权重 5/3/1、三种算法、±50% 规模容差），并明确要求"不确定就说不确定，不得臆造数字"
3. **测试脚本 `scripts/llm_smoke.py`（新增，24 项断言）**
   - 规则模式结果完整性、连不通时静默回退、模型输出非法值被拒、JSON 容错、真实调用（配了 Key 才跑）
4. **Key 存放位置（两处，安全设计）**
   - 天地图 tk → `frontend/.env.vps.local`（**新建，已被 .gitignore 忽略**）；填后须重新 `npm run build:vps`
   - DeepSeek Key → `backend/.env`（不入 Git）；填后重启服务即可，无需重构前端
5. **部署文档 `DEPLOY.md` 新增第七节**「配置天地图与大模型 Key」，含两处位置对照表、
   生效方式、验证命令、容错行为说明与代理故障排查；FAQ 增加 3 条相关条目

**⚠️ 发现的安全隐患**

`.gitignore` 为让 `VITE_USE_MOCK=false` 随仓库传递而放行了 `!.env.vps`，
**该文件是被 Git 追踪的** —— 若把天地图 Key 填进 `.env.vps`，下次 commit 就会推到 GitHub。
已实测确认：`git check-ignore frontend/.env.vps` 返回 1（不被忽略）、
`frontend/.env.vps.local` 返回 0（被忽略）。因此 Key 一律填 `.env.vps.local`。

**本地实测（全部通过）**

- `vite loadEnv` 优先级实测：`mode=vps` 读到 `VITE_TIANDITU_KEY`（来自 `.env.vps.local`，
  成功覆盖 `.env.vps` 的空值）且 `USE_MOCK=false`；`mode=production` 仍是 `USE_MOCK=true`、Key 为空
  → 证明**两种构建产物互不干扰**、`.local` 覆盖确实生效
- `scripts/llm_smoke.py`：**24 项通过 / 0 失败**
  - 关键项：连不通时 `parse_requirement` 返回完整结果且 `llmEnhanced=false`；越界门类 `ZZZ`
    与面积 `999999` 均被忽略；规则已算出 33.33 公顷时不被模型覆盖
- `scripts/api_smoke.py http://127.0.0.1:8080`：**96 项通过 / 0 失败**（新增 `llmEnhanced`
  字段未破坏任何原有断言，零回归）
- 部署包已同步新代码并重新打包

**技术决策与理由**

- **规则版为基线、LLM 只做增强**：竞赛现场网络不可控，必须保证"断网也能完整演示"。
  这是 README 铁律「无 LLM Key 时仍可跑通全流程」的落地，而非事后补丁。
- **不采信模型的确定性换算**：面积单位换算是纯算术，正则比模型可靠；模型的优势在语义理解
  （"建个机房"→ 信息技术服务业），两者分工，各取所长。
- **`llmEnhanced` 如实回传**：让前端与评委都能看出"这一步到底有没有真用上大模型"，
  避免把规则版结果包装成 AI 结论。
- **`httpx` 未加 `trust_env=False`**：保持库的默认行为（尊重 `HTTP_PROXY`）。
  本次测试中请求被本机代理截走并返回 502，正好验证了失败回退路径；该坑已写入
  `llm.py` 文档与 `DEPLOY.md` FAQ（服务器残留代理变量时清空即可）。

**当前状态**
- 两处 Key 位置已备好（内容留空待用户填写），代码与文档就绪，本地全链路验证通过。
- ⚠️ 本轮改动**仍未 commit**（新增 `llm.py`、`scripts/llm_smoke.py`、`frontend/.env.vps.local`；
  修改 `ai_parse.py`、`backend/.env(.example)`、`frontend/.env.example`、`DEPLOY.md`、本文件）。

**下一步（09-13）**
1. 用户填入两个 Key；天地图 Key 填完后需重新 `npm run build:vps` 并替换 VPS 上的 `dist`。
2. VPS 实际部署 + `/health` 复核（`gpkg_exists=true`、`layers=18`、填了 Key 后 `llm_enabled=true`）。
3. 逐层确认数据时点；演示脚本与分镜定稿；启动盖章流程。

---

## 2026-09-12（晚 · 真实 Key 实测与推理模型预算修复）

**背景**：用户填入两个真实 Key 后准备部署到 VPS。部署前做实测验证，
发现一个**只在推理模型下才暴露的静默失效问题**，另确认天地图 Key 的权限类型。

### 关键发现 1 · `deepseek-flash` 是推理模型，旧输出预算卡在临界值

`LLM_MODEL` 实际填的是 `deepseek-flash`（非 `deepseek-chat`）。两者行为差异极大：

| 模型 | 类型 | 同一解析任务 |
|---|---|---|
| `deepseek-chat` | 对话模型 | 仅耗 13 token，零 reasoning，秒回 |
| `deepseek-flash` | **推理模型** | 先生成不返回给用户的思考内容，同样占用 `max_tokens` |

旧代码两处预算为 `max_tokens=300 / 700`。实测 6 个解析输入：
**5 个成功、1 个失败** —— 输入「我们那个厂子想搬到桂林临桂这边来，看看有没有合适的地」
时思考占满 300 token、正文为空，连续重试 3 次皆空，最终静默回退规则版。耗时 5.9s 却毫无 AI 效果。

**这是最难发现的一类故障**：不报错、不中断、接口照常返回 200，只有 `llmEnhanced=false`
能看出端倪，而它恰恰是 AI 能力是否真正生效的唯一信号。

**修复**（`app/config.py` 新增三项配置，默认值即适配推理模型）：

```python
LLM_MAX_TOKENS_PARSE: int = 2048   # 需求解析
LLM_MAX_TOKENS_CHAT: int = 2048    # 对话
LLM_TIMEOUT_S: float = 60.0        # 原 30s
```

- `ai_parse.py` 两处调用改用 `settings.LLM_MAX_TOKENS_*` 与 `settings.LLM_TIMEOUT_S`
- `llm.py` 的 `TIMEOUT_S` 改为读配置
- **关键认知**：`max_tokens` 是**上限**而非预分配，**设大不额外计费**，只在模型真写满时按量付费；设小则会被截断。故放宽无成本代价。
- 修复后重测：**6/6 解析全部 LLM 生效**（含此前失败的输入，3.7s 通过），4/4 对话成功，耗时 1.8~4.8s
- 附带质量提升：输入「这里适合做什么类型的工业项目？」原先被规则误判为制造业 C2，
  现由模型正确回答"缺少区位、用地规模与产业意向，无法判定，请补充"

### 关键发现 2 · 天地图 Key 属「浏览器端」类型，服务端直连必然 403

服务端 `curl` 取瓦片返回：

```
403 {"msg":"权限类型错误","resolve":"Key权限类型为:浏览器端，请使用浏览器访问！","code":301012}
```

**这不是 Key 无效**。补上 `Referer` 头模拟浏览器后：`http=200  type=image/jpg  bytes=23987` ✅

前端由浏览器直连瓦片服务、天然带 `Referer`，因此**不受影响，无需任何改动**。
此坑已补入 `DEPLOY.md` FAQ，避免后续用服务端方式验证时误判为 Key 失效。

### 关键发现 3 · 测试断言未覆盖「LLM 开启」模式

`api_smoke.py` 原断言：输入「随便选址」须回落默认门类 `B`（规则版确定性契约）。
LLM 开启后语义判断由模型接管，实测该输入会返回 `C2` 或 `C1`（且**每次不同**），断言必然失败。

判定为**测试未覆盖新配置**，非产品缺陷。修法：读取 `/health` 的 `llm_enabled` 分流断言 ——
LLM 关闭时严格校验 `== "B"`（基线契约），开启时只校验"返回值仍在合法门类集合内"（上层契约）。
两种模式下断言都保持有效，不放松对契约的保护。

### 部署包更新

- 路径示例由 `D:\` 改为用户实际使用的 `C:\AI_urban_plan`；已核实**所有 `.bat` 均用 `%~dp0`
  引用自身目录、无硬编码盘符**，故放任意盘符均可运行
- 修复 `DEPLOY.md` 中重复的「## 八、」章节编号（应急兜底为八、安全合规为九）
- 按用户选择，**含真实 Key 的 `backend/.env` 已打进 zip**（`deploy/` 已被 gitignore，不会上传 GitHub）
- 清理 `dist/assets` 中 robocopy 遗留的旧 JS（`index-DHvSZ3RS.js` 2.9MB），改用 `/MIR` 镜像同步

### 验证结果（全部通过）

| 测试 | 结果 |
|---|---|
| `api_smoke.py`（LLM 开启） | **96 项通过 / 0 失败** |
| `llm_smoke.py` | **27 项通过 / 0 失败**（含真实调用 3 项） |
| 端到端解析 | **6/6 LLM 生效** |
| 端到端对话 | **4/4 成功**，拒答无关话题、数据来源表述准确 |
| 天地图 Key | 浏览器 UA 取瓦片 `200 image/png 18739 bytes`（当时误记为「靠 Referer」，见下节更正） |
| 部署包 | 47.78 MB / 77 文件，ZIP 12.69 MB |

### 本轮改动（仍未 commit）

- 修改：`backend/app/config.py`、`app/services/llm.py`、`app/services/ai_parse.py`、
  `scripts/api_smoke.py`、`backend/.env(.example)`、`deploy/vps/**`
- 已重新构建 `frontend/dist`（含天地图 Key）并重新打包 zip

---

## 2026-09-12（晚·二 · VPS 浏览器整块地图全白）

### 现象

用户在 **VPS 本机浏览器**打开 `http://127.0.0.1:8080/`，地图区域**整块全白**（连业务图层与兜底虚线边界都没有）；
但用**自己电脑**打开 `http://150.109.17.70:8080/` 天地图底图正常。

### 排查过程（逐项实测，排除了三个假设）

| 假设 | 实测 | 结论 |
|---|---|---|
| 天地图 Key 有 Referer 白名单，`127.0.0.1` 被拒 | **天地图根本不校验 Referer**：带浏览器 UA 时，`127.0.0.1` / `localhost` / `150.109.17.70` / 不带 Referer **全部 200 图片**（18739B 逐字节一致）；而 python UA 时**无论 Referer 是什么都 403 `code 301012`** | ❌ 排除 |
| VPS 在境外（新加坡），天地图封境外 IP | 经香港出口（`155.117.84.83`）取同一瓦片 → **200 图片**，与国内直连结果一致 | ❌ 排除 |
| VPS 出不了国 / 连不上国内服务 | 远程调 VPS 的 `/api/ai/parse` → **`llmEnhanced=true`**，VPS 真实调通了 `api.deepseek.com` | ❌ 排除 |

⚠️ **重要更正**：上一节把「服务端直连 403」解释为「靠补 Referer 解决」是**错的**。
天地图「浏览器端」Key 的判定依据是 **User-Agent**，不是 Referer。
以后排查瓦片 403 先查 UA，别去折腾 Referer 白名单。

补充事实：`150.109.17.70` 归属 **腾讯云新加坡节点（Singapore, SG）**，非香港。

### 根因（⚠️ 本节结论已作废，见文末「晚·三」更正）

~~**WebGL 不可用**。用户确认「整块全白、图层和虚线都没有」——若只是瓦片取不到，MapLibre 仍会渲染自绘图层；
连 canvas 内容都没有，说明 MapLibre GL 的 WebGL 上下文根本没建立。云服务器无独立显卡，
Chromium 内核浏览器（Edge / Chrome）会直接禁用 WebGL；RDP 会话中更常见。~~

**该判据不成立**：业务图层默认**全部关闭**、兜底虚线仅 1px，底图空白时看不见属正常现象。
用户后续实测「**切到 OSM 就能正常显示地图**」⇒ 渲染链路完好，真实原因在**底图瓦片源可达性**。

### 处理

**1. 前端加兜底（`frontend/src`）**

- 新增 `utils/webgl.ts`：`detectWebgl()` 依次尝试 `webgl2` → `webgl` → `experimental-webgl`，
  返回 `{ supported, version, renderer }`（renderer 取自 `WEBGL_debug_renderer_info`，便于识别 SwiftShader / Basic Render Driver）
- `components/layout/MapStage.vue`
  - `onMounted` 先探测 WebGL，不可用则**不再初始化地图**，改为显示说明面板
    （含 `edge://gpu` 自查、`--enable-unsafe-swiftshader` 启动参数、换 Firefox、改用另一台电脑访问四条指引）
  - `init()` 包 `try/catch`，MapLibre 初始化异常同样落到说明面板，避免空白无提示
  - 新增瓦片失败兜底：监听 `map.on('error')`，筛 `sourceId` 为 `tdt` / `tdtAnno` 的错误，
    累计 ≥4 次则自动把底图降级为 OSM 并 `ElMessage` 提示（防 Key 失效/欠额导致只剩空白底图）
- 样式沿用项目既有变量（`--bg-panel` / `--border-lighter` / `--text-regular` / `--radius-md` 等）

**2. 部署文档**：`DEPLOY.md` 第五节新增「5.1 整块地图全白（WebGL 不可用）」——
先教用户区分「瓦片没取到」与「WebGL 不可用」两类白，再给四条解决路径。
排查表新增一行指向该节。

### 验证

| 项 | 结果 |
|---|---|
| `npm run build:vps` | **vue-tsc 0 错误**，vite 18.14s（chunk 3020 kB / gzip 958 kB） |
| 产物核对 | `enable-unsafe-swiftshader`、`当前环境无法渲染地图`、天地图 Key **均在 JS 中** |
| 部署包 HTTP 冒烟 | `/` 200、新 JS 200（3029162B）、新 CSS 200、`/data/layers/*` 200、`/api/scenarios` 200，`index.html` 引用与 assets 一致 |
| 部署包 | `/MIR` 同步后只剩 1 个 JS，**77 文件 / 47.78 MB，ZIP 12.69 MB** |

### 结论与建议

- **推荐演示方式：从自己的电脑访问 `http://150.109.17.70:8080/`**，
  瓦片请求由本机浏览器发出，与 VPS 显卡、网络都无关，最稳。
- 若必须在 VPS 本机浏览器演示，用 `--enable-unsafe-swiftshader` 开软件渲染，或换 Firefox。
- 未用真实浏览器做可视验证（本机无 playwright/puppeteer）——**VPS 上刷新页面即可闭环确认**
  是否出现说明面板。

### 本轮改动（仍未 commit）

- 新增 `frontend/src/utils/webgl.ts`
- 修改 `frontend/src/components/layout/MapStage.vue`、`deploy/vps/AI_urban_plan/DEPLOY.md`
- 重新构建 `frontend/dist` 并重新打包 zip

---

## 2026-09-12（晚·三 · 更正根因：不是 WebGL，是「底图瓦片源可达性」）

### 触发

用户反馈：**VPS 上把底图切到 OSM 就能正常显示地图**。

这一句直接推翻上一节的根因 —— **OSM 与天地图在代码里走完全相同的渲染路径**
（`composables/useMap.ts` 里两者都是 `type:'raster'` 的 source + `raster` layer，
同一个 MapLibre 实例、同一个 WebGL canvas），唯一差别是 `sources[*].tiles` 里的 URL。
OSM 能画出来 ⇒ **WebGL / MapLibre / 页面 JS 全部正常**。

### 本轮实测（补齐上一节缺失的关键数据）

| 探测项 | 结果 |
|---|---|
| 天地图瓦片（国内直连，浏览器 UA + 模拟页面 Origin/Referer） | **200 image/png**，响应头带 **`access-control-allow-origin: *`** ⇒ **无 CORS 障碍**、Key 有效、URL 格式正确 |
| 同上换**非浏览器 UA** | **403 `{"msg":"权限类型错误","code":301012}`**（经境外代理出口同样 403） |
| 天地图 DNS | `t0/t3.tianditu.gov.cn` → `116.205.76.122` / `116.205.76.86` |
| **OSM 瓦片（国内直连）** | **`ConnectTimeout`**（`199.96.58.85`，Fastly） |
| OSM 瓦片（check-host 5 节点 SG/HK/JP/US/DE） | **全部 200**，0.01~0.12s（`151.101.x` / `146.75.x`） |
| 天地图瓦片（同 5 节点） | SG **418**/4.27s、JP 418、US 418、DE 418、HK **403** —— ⚠️ **不可用于判定地域**（探针不带浏览器 UA，必被拒） |
| 上一轮"境外出口"的真实身份 | `155.117.84.83` → **美国俄亥俄州辛辛那提**（另一库给"比利时"）⇒ 确属境外，非国内中转 |
| 同上出口 + 浏览器 UA 取天地图 | **200 image/png** ⇒ **天地图并不封锁境外 IP** |

### 更正与认知

1. **上一节「根因 = WebGL 不可用」作废**；判据（"连图层和虚线都没有"）本身不可靠。
2. 新判据（不依赖用户主观描述）：**让它切一次备用底图**。
   - 切了正常 ⇒ 渲染完好，查**瓦片源可达性**（DNS / 出海链路 / UA / Key 权限类型）
   - 切了仍全白 ⇒ 才查 WebGL
3. **用 check-host.net 之类多节点探针判断"境外能否访问国内瓦片服务"必然得出假结论** ——
   它不带浏览器 UA，一律 403/418，看着像地域封锁。要判地域，必须用**能自定义 Header 的境外出口**复测。
4. ⚠️ **默认底图是 `tianditu-vec`**（`store/map.ts`），页面一打开就走天地图路径；白屏首先怀疑它。
5. ⚠️ **上一轮加的"瓦片失败自动降级 OSM"只对境外出口的客户端有效**：OSM 国内直连超时，
   国内演示时降级等于换一种白屏。兜底底图需另选国内可达的源。
6. 本轮**未改任何代码**，仅更正结论与文档。

### 待确认（下一步）

`t0~t7.tianditu.gov.cn` 从 **VPS 本机浏览器**是否可达 —— 只能在该机器上实测：
浏览器直接打开瓦片 URL，或 PowerShell **带浏览器 UA** 请求。据此再定修复方案。




---

## 2026-09-13（日）v5 UI 对齐收尾 + 真实模式联调 + Word 可研格式报告

### 本轮完成

1. **v5 设计稿骨架迁移收尾**：顶栏精简（去中间导航/通知/头像，系统名 22px）、右栏三卡高度锁定
   （ChatPanel basis-0、算法说明卡恒 grow）、选中态墨黑统一、面板加宽（360/430）、
   候选地块空态复刻参考稿（SVG 插图 + 引导语 + 耗时胶囊）。
2. **真实模式联调**：frontend/.env 切 VITE_USE_MOCK=false，本机 FastAPI(8000/8080) 实测
   /api/ai/model = AUC 0.693 / 145 样本 / 66 已开发（与 VPS 一致）；AI 偏好学习数值确认为真实训练值。
3. **顶栏运行状态灯**（新 api/system.ts）：演示模式 / 算法后台·在线 / 离线 三态，30s 轮询 /health。
4. **图层面板要素数量**（新 layerCounts.generated.ts，构建期内嵌零请求）：
   tools/gen_layer_counts.py 离线统计 18 层，如现状建筑 7851、永基 3544、控规工业 145；格式「（7851项）」10px。
5. **Word 报告（可研格式重排）**（新 reportDocx.ts / reportCharts.ts，docx@9.7.1 按需分包 382KB）：
   封面 + 静态逐行目录 + 第一章总论…第六章论证与建议，7 表 4 图按章编号；
   页面预览标注「简版报告」；按钮改名「Word 详细报告 / PDF 简版报告」。
   - fix：ECharts 离屏截图补 animation:false（此前捕获动画第 0 帧 = 空图表）；
   - fix：雷达图量纲（因子分实为 0–100，误 ×100 致多边形飞出画布、画布被半透明填充染粉）；
     正文 7 处「标准化 0–1」更正为「0–100 分制」。
6. **清理**：删除 5 个 09-12 旧部署 zip（≈63.5MB）与项目自身 __pycache__；部署包目录、数据、依赖未动。

### 遗留 / 注意

- 8080 现由项目 backend 目录 main.py 提供（0.0.0.0:8080 单端口全栈），此前「部署包进程数据目录不一致」已消除。
- VPS（117.72.210.60:8000）上轮探测 502，后端疑似未运行，待远端排查。
- 09-14 起冻结功能，只修 bug 与文档。
