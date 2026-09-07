# AGENTS.md

> AI 入口文件。**任何 AI 工具在进入本仓库时，第一个要读的文件是 `README.md`。**

## 强制流程

1. 读 `README.md`（项目总纲 / 铁律 / 技术栈 / 排期）。
2. 读 `docs/PROGRESS.md`（当前进度与阻塞点）。
3. 读 `docs/SCENARIOS.md`（业务场景定义）。
4. 读 `docs/COMPETITION.md`（比赛规则与提交要求）。
5. 以上全部读完后，才允许修改任何文件。
6. 结束工作前，**必须更新 `docs/PROGRESS.md`**。

## 不得违反

- 不得擅自更换技术栈（Vue3+Vite+MapLibre / FastAPI / SQLite）。
- 不得提交原始数据、涉密数据、个人信息、密钥。
- 不得虚构数据或把样例数据说成真实数据。
- 坐标系不明的数据，禁止入库。
- 9 月 14 日后冻结功能，只修 bug 与文档。

## 上下文优先级

`README.md` > `docs/PROGRESS.md` > `docs/SCENARIOS.md` > `docs/COMPETITION.md` > 代码注释

规则冲突时，以 `README.md` 为准，并在 `docs/PROGRESS.md` 记录冲突点。
