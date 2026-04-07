# M0 Rebaseline 执行方案（方案 2）

> 版本: 2026-04-06
> 状态: R4 review
> 目标: 将 `origin/main` 收回为“真正的 M0 基线”，随后再从干净主线启动 `M1`
> 触发原因: `origin/main` 已合入 `a0a729f [M0] Phase 0/1 Baseline Freeze (#8)`，但实际合并范围超出 `M0` 边界

---

## 当前状态

- `R2` 运行时收口、`R3` 代码清理、`R4` 验收留痕均已推进到 `review`。
- 合并包说明见 `docs/rebaseline_artifacts/RB4-04.md`。
- 合并前仍建议对文档迁移进行 stage-aware review，并重新构建 Docker 前端镜像后做一次补充 smoke。

---

## 背景判断

- `M0` 原计划是冻结 Phase 0/1 基线，并停止继续把长分支当主承载。
- 实际合并到 `main` 的内容已包含一批不属于 `M0` 的 `Phase 2 / Phase 3 / M1` 资产。
- 因此当前最高优先级不再是“直接启动 `M1`”，而是先做一次 `rebaseline`，把主线恢复到可解释、可验收、可回滚的 `M0` 状态。

---

## 目标与非目标

### 目标

- 恢复 `main` 到与 `docs/milestones/m0/M0_PR_BOUNDARY.md` 一致的 `M0` 范围。
- 移除或禁用所有超出 `M0` 的运行时入口、调度入口和前端导航入口。
- 清理超范围代码、脚本、文档和无效测试，使仓库状态与执行计划一致。
- 补齐可持续推进的跟踪机制，确保任何时候都能从文件恢复上下文。

### 非目标

- 本轮不启动新的 `M1` 实现。
- 本轮不继续扩展 `P3-01/03/04/05/06` 功能。
- 本轮不做新的体验打磨或新增需求。
- 本轮不尝试通过一次性 `git revert` 粗暴回退整个 `#8` 合并包。

---

## 真正的 Source Of Truth

| 文件 | 用途 |
|------|------|
| `docs/REBASELINE_M0_PLAN.md` | 总体方案、阶段顺序、并行边界、检查点 |
| `docs/REBASELINE_M0_TRACKER.md` | 实时状态板，记录任务状态、Owner、证据、下一步 |
| `docs/rebaseline_artifacts/README.md` | 断点续推约定、任务记录模板、证据落盘规则 |
| `docs/EXECUTION_PLAN.md` | 里程碑级总览；只记录当前主线方向，不承载细节执行过程 |
| `docs/milestones/m0/M0_PR_BOUNDARY.md` | `M0` 保留/延后范围判定依据 |

---

## 分支与 PR 策略

### 分支策略

- 禁止继续在 `phase-0-complete-scanning-engine` 上叠加任何新需求。
- 从 `origin/main` 新建治理分支: `rebaseline/m0-cleanup`
- 仅在 `rebaseline/m0-cleanup` 上执行本方案中的任务。
- `M1` 相关实现必须等待 `rebaseline/m0-cleanup` 合回 `main` 后，再从新 `main` 开独立分支。

### PR 策略

建议拆成 3 个连续 PR，避免“大回退包”不可审：

1. `PR-A` 运行时收口
   - 路由、页面入口、导航、调度入口先回到 `M0`
2. `PR-B` 代码与资产清理
   - 删除超范围模块、页面、脚本、文档、测试
3. `PR-C` 验收与文档定稿
   - 测试、联调、文档回写、最终 merge 包整理

---

## 执行原则

### 原则 1: 先收口运行时，再删代码

- 先把用户和系统可触达的超范围入口关掉。
- 入口收口后再做代码级删除，风险最小。

### 原则 2: 一次只推进到下一个检查点

- 每个阶段结束必须有明确的 go/no-go 结论。
- 未通过检查点，不进入下一个阶段。

### 原则 3: 一切以任务 ID 和文件落盘为准

- 每个任务都有唯一 ID。
- 每次工作开始和结束都要更新 `docs/REBASELINE_M0_TRACKER.md`。
- 若任务中存在判断、文件范围、冲突说明，必须补写到 `docs/rebaseline_artifacts/<TASK_ID>.md`。

### 原则 4: 并行可以做，但写集必须分离

- 可以多 Agent 并行，但必须按前后端、文档、测试、调度切分责任。
- 任何并行任务都要先确认写入文件集不重叠。

---

## 阶段总览

| 阶段 | 名称 | 目标 | 结束条件 |
|------|------|------|---------|
| `R0` | 冻结与快照 | 锁定战场，建立真实快照 | 分支、基线、快照文档就绪 |
| `R1` | 范围清单 | 明确 keep/remove/hold 边界 | 后端/前端/文档脚本范围矩阵签字 |
| `R2` | 运行时收口 | `main` 行为先回到 `M0` | 超范围路由、页面、调度入口全部移除或禁用 |
| `R3` | 代码清理 | 仓库结构回到 `M0` | 超范围代码、脚本、文档、测试清理完成 |
| `R4` | 验收与定稿 | 形成可合并治理包 | 测试、联调、文档、回滚边界全部留痕 |

---

## 任务拆解

### `R0` 冻结与快照

| ID | 任务 | 依赖 | 可并行 | 建议 Owner | 输出物 |
|----|------|------|--------|-----------|--------|
| `RB0-01` | 冻结旧长分支使用方式，约定后续只在 `rebaseline/m0-cleanup` 推进 | 无 | 否 | 人工 + Agent F | 本文档、Tracker 更新、分支命名与工作约束确认 |
| `RB0-02` | 基于 `origin/main`、`docs/milestones/m0/M0_PR_BOUNDARY.md` 和 `#8` 合并结果，形成真实范围快照 | `RB0-01` | 否 | Agent F | `docs/rebaseline_artifacts/RB0-02.md` |
| `RB0-03` | `docs/` 文档分类重构: 将阶段/里程碑文档按目录归类并补导航 | `RB0-01` | 可与 `RB1-*` 并行 | Agent D | 文档目录结构 + 索引更新 + `docs/rebaseline_artifacts/RB0-03.md` |

### `R1` 范围清单

| ID | 任务 | 依赖 | 可并行 | 建议 Owner | 输出物 |
|----|------|------|--------|-----------|--------|
| `RB1-01` | 后端范围矩阵: router/service/model/schema/job 按 `keep/remove/hold` 标注 | `RB0-02` | 可与 `RB1-02/03` 并行 | Agent A | `docs/rebaseline_artifacts/RB1-01.md` |
| `RB1-02` | 前端范围矩阵: route/view/component/api/composable 按 `keep/remove/hold` 标注 | `RB0-02` | 可与 `RB1-01/03` 并行 | Agent C | `docs/rebaseline_artifacts/RB1-02.md` |
| `RB1-03` | 文档/脚本/测试范围矩阵: 识别历史保留项与应删除项 | `RB0-02` | 可与 `RB1-01/02` 并行 | Agent F | `docs/rebaseline_artifacts/RB1-03.md` |
| `RB1-04` | 汇总决策: 形成统一 keep/remove 清单与回退顺序 | `RB1-01`,`RB1-02`,`RB1-03` | 否 | Agent F | `docs/rebaseline_artifacts/RB1-04.md` |

### `R2` 运行时收口

| ID | 任务 | 依赖 | 可并行 | 建议 Owner | 输出物 |
|----|------|------|--------|-----------|--------|
| `RB2-01` | 后端运行时收口: 移除超范围 router 注册与 scheduler/job 入口 | `RB1-04` | 可与 `RB2-02` 并行 | Agent A | 代码变更 + `docs/rebaseline_artifacts/RB2-01.md` |
| `RB2-02` | 前端运行时收口: 移除超范围 route/nav/menu 入口 | `RB1-04` | 可与 `RB2-01` 并行 | Agent C | 代码变更 + `docs/rebaseline_artifacts/RB2-02.md` |
| `RB2-03` | 页面内嵌入口收口: 清理 `Dashboard` / `Backtest` 中的 `P3` 标签页与卡片 | `RB2-02` | 可与 `RB2-04` 并行 | Agent C | 代码变更 + `docs/rebaseline_artifacts/RB2-03.md` |
| `RB2-04` | 清理运行时残余引用: 关闭超范围 API 调用、状态轮询、feature wiring | `RB2-01`,`RB2-02` | 可与 `RB2-03` 并行 | Agent B | 代码变更 + `docs/rebaseline_artifacts/RB2-04.md` |

### `R3` 代码清理

| ID | 任务 | 依赖 | 可并行 | 建议 Owner | 输出物 |
|----|------|------|--------|-----------|--------|
| `RB3-01` | 删除超范围后端模块: `alert`/`report`/`optimization`/`strategy_social`/`events` 等 | `RB2-04` | 可与 `RB3-02/03` 并行 | Agent A | 代码变更 + `docs/rebaseline_artifacts/RB3-01.md` |
| `RB3-02` | 删除超范围前端页面与组件: `Alerts` / `Optimization` / `Reports` / `StrategyMarket` 等 | `RB2-03`,`RB2-04` | 可与 `RB3-01/03` 并行 | Agent C | 代码变更 + `docs/rebaseline_artifacts/RB3-02.md` |
| `RB3-03` | 删除或归档超范围文档与脚本: `M1_*` 启动资产、执行仪表板、启动脚本等 | `RB1-03`,`RB2-04` | 可与 `RB3-01/02` 并行 | Agent F | 文档/脚本变更 + `docs/rebaseline_artifacts/RB3-03.md` |
| `RB3-04` | 清理残余依赖与测试: import、dead code、无效测试、构建配置 | `RB3-01`,`RB3-02`,`RB3-03` | 否 | Agent B | 代码变更 + `docs/rebaseline_artifacts/RB3-04.md` |

### `R4` 验收与定稿

| ID | 任务 | 依赖 | 可并行 | 建议 Owner | 输出物 |
|----|------|------|--------|-----------|--------|
| `RB4-01` | 后端回归: `M0` 范围 quick suite + 关键 API 验证 | `RB3-04` | 可与 `RB4-02` 并行 | Agent F | `docs/rebaseline_artifacts/RB4-01.md` |
| `RB4-02` | 前端验收: `typecheck` / `build` / 入口 smoke | `RB3-04` | 可与 `RB4-01` 并行 | Agent C | `docs/rebaseline_artifacts/RB4-02.md` |
| `RB4-03` | 手工联调: Dashboard、Selection、StockDetail、Backtest 主链路 | `RB4-01`,`RB4-02` | 否 | Agent C + Agent F | `docs/rebaseline_artifacts/RB4-03.md` |
| `RB4-04` | 文档定稿: 更新 `EXECUTION_PLAN`、补 `M0` 现实状态、形成 merge 说明 | `RB4-03` | 否 | Agent F | `docs/rebaseline_artifacts/RB4-04.md` |

---

## 多 Agent 并行建议

### Agent 选择约定

- 代码改动任务默认使用 `coder`
  - 适用: `RB2-*`、`RB3-*`、`RB4` 中涉及代码修正的任务
- 范围梳理与只读扫描优先使用 `explorer`
  - 适用: `RB1-*` 这类 keep/remove/hold 矩阵梳理
- 文档整理、索引修正、归档迁移优先使用轻量 `worker`
  - 适用: `RB0-03`、`RB3-03`、`RB4-04`
- 关键节点可补一个 `reviewer`
  - 适用: `CP1`、`CP2`、`CP4` 进入 review 前

理由:

- `coder` 在小到中等范围代码修改上更高效，适合当前的运行时收口和后续删除/清理任务。
- `explorer` 更适合做边界梳理，避免为只读分析付出过高成本。
- 文档整理不需要高推理强度，轻量 agent 更划算。

### 并行波次 A: 范围梳理

- Agent A: `RB1-01`，建议 `explorer`
- Agent C: `RB1-02`，建议 `explorer`
- Agent F: `RB1-03`，建议轻量 `worker`
- Agent D: `RB0-03`，建议轻量 `worker`
- 汇总由 Agent F 承接 `RB1-04`

### 并行波次 B: 运行时收口

- Agent A: `RB2-01`，建议 `coder`
- Agent C: `RB2-02`，建议 `coder`
- Agent B: `RB2-04`，建议 `coder`
- `RB2-03` 在 `RB2-02` 完成后由 Agent C 接续，建议 `coder`

### 并行波次 C: 代码清理

- Agent A: `RB3-01`，建议 `coder`
- Agent C: `RB3-02`，建议 `coder`
- Agent F: `RB3-03`，建议轻量 `worker`
- Agent B: 待前三项完成后承接 `RB3-04`，建议 `coder`

### 并行波次 D: 验收

- Agent F: `RB4-01`，建议 `coder` 或 `reviewer`
- Agent C: `RB4-02`，建议 `coder`
- `RB4-03` 与 `RB4-04` 串行执行

---

## 检查点与回顾机制

### `CP0` 快照确认

进入条件:
- `RB0-01`、`RB0-02` 完成

回顾问题:
- 是否已经明确当前唯一治理分支？
- 是否已经用文件而不是口头结论记录了真实偏航情况？

### `CP1` 范围签字

进入条件:
- `RB1-01` ~ `RB1-04` 完成

回顾问题:
- 是否所有超范围运行时入口都被识别？
- 是否存在 `hold` 项仍未决？

### `CP2` 运行时回到 M0

进入条件:
- `RB2-01` ~ `RB2-04` 完成

回顾问题:
- 主线是否仍暴露 `Alerts / Optimization / Reports / StrategyMarket`？
- 是否还有后台调度或 API 入口会触发延后功能？

### `CP3` 仓库结构清理完成

进入条件:
- `RB3-01` ~ `RB3-04` 完成

回顾问题:
- 是否还残留超范围模块被 import？
- 文档是否仍错误宣称 `M1` 已可立即启动？

### `CP4` 可合并治理包

进入条件:
- `RB4-01` ~ `RB4-04` 完成

回顾问题:
- 测试与联调是否都能支撑“现在的 `main` 就是 M0”？
- 文档、代码、运行行为是否重新一致？

---

## 中断恢复机制

每次任务中断、quota 触顶、进程崩溃前后，都按以下流程恢复:

1. 打开 `docs/REBASELINE_M0_TRACKER.md`
2. 找出状态为 `in_progress` 或 `blocked` 的任务
3. 打开对应 `docs/rebaseline_artifacts/<TASK_ID>.md`
4. 根据“最后结论 / 剩余动作 / 风险”三段继续推进
5. 本轮结束前必须更新 Tracker 与任务记录文件

---

## 建议的首批落地顺序

建议先完成以下最小闭环，再动代码:

1. `RB0-01` 冻结工作方式
2. `RB0-02` 真实范围快照
3. `RB1-01` / `RB1-02` / `RB1-03` 并行梳理
4. `RB1-04` 汇总 keep/remove 清单
5. 再进入 `PR-A` 的 `RB2-*` 任务

---

## 完成定义

当以下条件全部满足时，视为 `rebaseline` 完成:

- `main` 的运行时行为仅保留 `M0` 范围能力
- 超范围代码和入口不再影响构建、测试、联调
- `EXECUTION_PLAN.md` 与代码现实一致
- 后续 `M1` 可以从新 `main` 独立启动，不依赖旧长分支残留资产
