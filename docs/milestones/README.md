# Milestones 文档索引

按里程碑与阶段整理的文档统一放在这里，但这里不是主推进入口。
当前推进状态一律先看 [docs/EXECUTION_PLAN.md](../EXECUTION_PLAN.md)。

当前主路线说明:
- 当前执行口径以 `docs/EXECUTION_PLAN.md` 为准；`M0` / `M1` / `M2` / `Pre-M3` / `M3` 已完成收口，当前 active 路线是 `M5 / P3-05` PR/release closure
- `M5 / P3-05 v1` 已完成本地代码验收并已提交 PR；live staging smoke、生产 backup、发布前 schema-contract gate 与 release smoke 仍是 release activity，不应写成生产完成
- `Pre-M3` 作为 closed baseline 保留在 `m3/` 目录中，后续 schema-changing 发布继续受 `schema_contract` gate 管控
- `phase3/` 与 `phase4/` 下保留的是设计/规划资产，不应自动解读为“已经完成”或“现在应直接启动”
- 旧 `P3-04 策略社交` 已从 active plan-of-record 退役，仅保留为历史设计
- 当前 `M5` 统一锚定到“参数优化任务 + trial 结果 + 最优参数应用”的最小闭环，先复用现有回测服务与异步任务模式，不默认引入新的队列系统
- `M5` 合并/发布完成后再进入 `M6 / P3-06`；在此之前 `M6` 只可做准备和设计回看

## 目录分层

### 1. 当前 active 执行包

- [`m5/`](./m5/)：当前 active 执行包。这里承接 `M5 / P3-05` 的本地验收证据、PR/release closure、release activity、residue 决策与 reviewer gate。`M5_P3-05_KICKOFF_PLAN.md` 保留为冻结 kickoff 基线/历史启动计划，不再作为当前唯一执行状态。

### 2. 已完成的历史执行包

- [`m0/`](./m0/)：`M0` 基线冻结、边界与稳定性相关文档。
- [`m1/`](./m1/)：`M1 / Phase 1.5` 数据层底座执行包与历史材料。
- [`m2/`](./m2/)：`M2 / P3-01` 用户行为埋点执行包、事件契约与验收留痕。
- [`m3/`](./m3/)：`Pre-M3` 与 `M3 / P3-03` 参数化筛选和订阅提醒的 closed baseline。

### 3. 设计与规划资产

- [`phase3/`](./phase3/)：`P3-01` ~ `P3-06` 的设计与预实现文档，不写当前完成状态。
- [`phase4/`](./phase4/)：更远期规划文档，不参与当前 `M3` 执行裁决。

## 建议阅读顺序

1. 先看 [docs/EXECUTION_PLAN.md](../EXECUTION_PLAN.md)。
2. 如果要接当前主线，再进入 [`m5/`](./m5/) 并优先看 `README.md` 与 `artifacts/` 的本地验收/release activity 证据。
3. 如果要回顾历史执行，再看 `m0/`、`m1/`、`m2/`、`m3/`。
4. 如果只想看未来能力设计，最后再看 `phase3/`、`phase4/`。
