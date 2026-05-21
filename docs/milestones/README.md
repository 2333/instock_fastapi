# Milestones 文档索引

按里程碑与阶段整理的文档统一放在这里，但这里不是主推进入口。
当前推进状态一律先看 [docs/EXECUTION_PLAN.md](../EXECUTION_PLAN.md)。

当前主路线说明:
- 当前执行口径以 `docs/EXECUTION_PLAN.md` 为准；`M0` / `M1` / `M2` / `Pre-M3` / `M3` 已完成收口，当前 active 路线是 `M5 / P3-05` 参数优化 kickoff
- `Pre-M3` 作为 closed baseline 保留在 `m3/` 目录中，后续 schema-changing 发布继续受 `schema_contract` gate 管控
- `phase3/` 与 `phase4/` 下保留的是设计/规划资产，不应自动解读为“已经完成”或“现在应直接启动”
- 旧 `P3-04 策略社交` 已从 active plan-of-record 退役，仅保留为历史设计
- 当前 `M5` 统一锚定到“参数优化任务 + trial 结果 + 最优参数应用”的最小闭环，先复用现有回测服务与异步任务模式，不默认引入新的队列系统

## 目录分层

### 1. 当前 active 执行包

- [`m5/`](./m5/)：当前 active 执行包。这里承接 `M5 / P3-05` 参数优化的 kickoff、scope freeze、并行任务拆分与 reviewer gate。

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
2. 如果要接当前主线，再进入 [`m5/`](./m5/)。
3. 如果要回顾历史执行，再看 `m0/`、`m1/`、`m2/`、`m3/`。
4. 如果只想看未来能力设计，最后再看 `phase3/`、`phase4/`。
