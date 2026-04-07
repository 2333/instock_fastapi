# M0 Rebaseline 跟踪板

> 版本: 2026-04-06
> 主分支策略: 只在 `rebaseline/m0-cleanup` 推进
> 状态流转: `todo` -> `in_progress` -> `review` -> `done`
> 阻塞态: `blocked`

---

## 使用规则

- 每个任务开始前，先把状态改成 `in_progress`
- 每个任务结束后，至少更新 `状态 / Last Update / 下一步`
- 若任务中涉及判断、文件范围、测试结果，补写到对应的 artifact 文件
- 所有 artifact 文件放在 `docs/rebaseline_artifacts/`

---

## 检查点状态

| Checkpoint | 状态 | 条件 | 说明 |
|-----------|------|------|------|
| `CP0` 快照确认 | `review` | `RB0-01` + `RB0-02` | 统一战场与真实快照已落盘 |
| `CP1` 范围签字 | `review` | `RB1-01` ~ `RB1-04` | 第一轮 keep/remove/hold 清单已形成，待按 `RB2-*` 落地验证 |
| `CP2` 运行时回到 M0 | `review` | `RB2-01` ~ `RB2-04` | 后端入口、前端入口、mixed view 与活跃链路残余 wiring 已收口，待进入物理删除阶段 |
| `CP3` 仓库结构清理完成 | `review` | `RB3-01` ~ `RB3-04` | 后端、前端、脚本、测试残余清理已完成，待进入验收 |
| `CP4` 可合并治理包 | `review` | `RB4-01` ~ `RB4-04` | 后端、前端、浏览器 smoke 与 merge 包说明已完成 |

---

## `R0` 冻结与快照

| ID | 任务 | 状态 | Owner | Depends | Parallel | Artifact | Last Update | 下一步 |
|----|------|------|-------|---------|----------|----------|-------------|--------|
| `RB0-01` | 冻结旧长分支使用方式，建立治理分支约束 | `review` | 人工 + Agent F | - | 否 | `docs/rebaseline_artifacts/RB0-01.md` | 2026-04-07 | 治理主文件、跟踪板和首批并行节奏已建立，待与快照结论一起收口 |
| `RB0-02` | 形成真实范围快照 | `review` | Agent F | `RB0-01` | 否 | `docs/rebaseline_artifacts/RB0-02.md` | 2026-04-07 | 真实偏航快照已落盘，并由 `RB1-01` ~ `RB1-04` 范围矩阵完成承接 |
| `RB0-03` | `docs/` 文档分类重构与导航整理 | `review` | Agent D | `RB0-01` | 与 `RB1-*` 并行 | `docs/rebaseline_artifacts/RB0-03.md` | 2026-04-07 | 已完成目录归类与第一轮导航修正，待做残余路径复扫 |

## `R1` 范围清单

| ID | 任务 | 状态 | Owner | Depends | Parallel | Artifact | Last Update | 下一步 |
|----|------|------|-------|---------|----------|----------|-------------|--------|
| `RB1-01` | 后端范围矩阵 | `review` | Agent A | `RB0-02` | 与 `RB1-02/03` 并行 | `docs/rebaseline_artifacts/RB1-01.md` | 2026-04-07 | 第一版后端矩阵已完成，可供 `RB1-04` 汇总；待边界项二次收敛 |
| `RB1-02` | 前端范围矩阵 | `review` | Agent C | `RB0-02` | 与 `RB1-01/03` 并行 | `docs/rebaseline_artifacts/RB1-02.md` | 2026-04-07 | 第一版前端矩阵已完成，可供 `RB1-04` 汇总；待混合文件细化 |
| `RB1-03` | 文档/脚本/测试范围矩阵 | `review` | Agent F | `RB0-02` | 与 `RB1-01/02` 并行 | `docs/rebaseline_artifacts/RB1-03.md` | 2026-04-07 | 第一版矩阵已完成，可供 `RB1-04` 汇总；等待后端/前端边界项对齐 |
| `RB1-04` | 汇总统一决策与回退顺序 | `review` | Agent F | `RB1-01`,`RB1-02`,`RB1-03` | 否 | `docs/rebaseline_artifacts/RB1-04.md` | 2026-04-07 | 第一轮统一判定已完成，可进入 `RB2-*` 运行时收口 |

## `R2` 运行时收口

| ID | 任务 | 状态 | Owner | Depends | Parallel | Artifact | Last Update | 下一步 |
|----|------|------|-------|---------|----------|----------|-------------|--------|
| `RB2-01` | 后端路由与调度入口收口 | `review` | Agent A | `RB1-04` | 与 `RB2-02` 并行 | `docs/rebaseline_artifacts/RB2-01.md` | 2026-04-07 | 运行时入口已收口，待 `RB2-04` / `RB4-01` 验证残余引用与行为 |
| `RB2-02` | 前端路由与导航入口收口 | `review` | Agent C | `RB1-04` | 与 `RB2-01` 并行 | `docs/rebaseline_artifacts/RB2-02.md` | 2026-04-07 | 独立路由与头部入口已收口，下一步进入 mixed view 裁剪 |
| `RB2-03` | `Dashboard` / `Backtest` 页面内嵌入口收口 | `review` | Codex | `RB2-02` | 与 `RB2-04` 并行 | `docs/rebaseline_artifacts/RB2-03.md` | 2026-04-07 | 已移除 Dashboard 公共策略/报告/优化卡片，Backtest 公共策略/优化标签页，以及 Attention 预警与埋点；`web` typecheck 通过 |
| `RB2-04` | 清理运行时残余 wiring | `review` | Codex | `RB2-01`,`RB2-02` | 与 `RB2-03` 并行 | `docs/rebaseline_artifacts/RB2-04.md` | 2026-04-07 | 活跃页面残余 `useAnalytics` 已摘除，剩余引用主要在待删除页面/组件与 API 导出中，转入 `RB3-02` / `RB3-04` |

## `R3` 代码清理

| ID | 任务 | 状态 | Owner | Depends | Parallel | Artifact | Last Update | 下一步 |
|----|------|------|-------|---------|----------|----------|-------------|--------|
| `RB3-01` | 删除超范围后端模块 | `review` | Coder + Codex | `RB2-04` | 与 `RB3-02/03` 并行 | `docs/rebaseline_artifacts/RB3-01.md` | 2026-04-07 | 后端超范围模块已删除，`app` 引用复扫与 `app.main` import 通过；测试残余转 `RB3-04` |
| `RB3-02` | 删除超范围前端页面与组件 | `review` | Coder + Codex | `RB2-03`,`RB2-04` | 与 `RB3-01/03` 并行 | `docs/rebaseline_artifacts/RB3-02.md` | 2026-04-07 | 前端超范围页面/组件/API 已删除，`web/src` 引用复扫与 typecheck 通过 |
| `RB3-03` | 删除或归档超范围文档与脚本 | `review` | Codex | `RB1-03`,`RB2-04` | 与 `RB3-01/02` 并行 | `docs/rebaseline_artifacts/RB3-03.md` | 2026-04-07 | `Makefile:init-db` 已改为 M0 初始化入口，M1/Timescale 脚本与根目录 quickfix 已删除，`make init-db` 通过 |
| `RB3-04` | 清理残余依赖、导入与测试 | `review` | Codex | `RB3-01`,`RB3-02`,`RB3-03` | 否 | `docs/rebaseline_artifacts/RB3-04.md` | 2026-04-07 | 已删除 events API 旧测试，active 引用复扫、app import、router tests、web typecheck 通过 |

## `R4` 验收与定稿

| ID | 任务 | 状态 | Owner | Depends | Parallel | Artifact | Last Update | 下一步 |
|----|------|------|-------|---------|----------|----------|-------------|--------|
| `RB4-01` | 后端回归与 API 验证 | `review` | Codex | `RB3-04` | 与 `RB4-02` 并行 | `docs/rebaseline_artifacts/RB4-01.md` | 2026-04-07 | 后端全量测试通过：129 passed, 1 warning |
| `RB4-02` | 前端构建验收 | `review` | Codex | `RB3-04` | 与 `RB4-01` 并行 | `docs/rebaseline_artifacts/RB4-02.md` | 2026-04-07 | 前端 `npm run build` 通过，保留 Sass/chunk 既有 warning |
| `RB4-03` | 手工联调与验收留痕 | `review` | Codex | `RB4-01`,`RB4-02` | 否 | `docs/rebaseline_artifacts/RB4-03.md` | 2026-04-07 | 当前源码 dev server 完成 Dashboard/Selection/Backtest/Attention/Stocks/StockDetail 浏览器 smoke |
| `RB4-04` | 文档定稿与 merge 包整理 | `review` | Codex | `RB4-03` | 否 | `docs/rebaseline_artifacts/RB4-04.md` | 2026-04-07 | merge 包范围、验证证据、已知注意事项和合并前建议已落盘 |

---

## 当前收口状态（2026-04-07）

- `RB0` ~ `RB4` 均已推进到 `review`。
- 合并包说明见 `docs/rebaseline_artifacts/RB4-04.md`。
- 提交前重点检查 `docs/archive/`、`docs/milestones/`、`docs/rebaseline_artifacts/` 是否全部 staged。
- Docker 前端 `localhost:3002` 仍是旧镜像，若要用 Docker 端口验收，需要先重新构建镜像。

---

## 备注

- 所有 `M1` 工作在本跟踪板完成前均视为未启动。
- 若发现新的超范围入口，先写入对应 artifact 文件，再决定是否追加任务 ID。
