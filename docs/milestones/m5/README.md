# M5 文档索引

`m5/` 是当前 active 执行包，承接 `P3-05` 参数优化服务。

## 当前执行入口

- [docs/EXECUTION_PLAN.md](../../EXECUTION_PLAN.md) - 先确认当前里程碑位置、主路线状态和高层 stop condition
- [artifacts/](./artifacts/) - `M5 v1` 本地代码验收、review 结论、命令证据和剩余 release activity
- [M5_P3-05_REVIEW_CHECKLIST.md](./M5_P3-05_REVIEW_CHECKLIST.md) - reviewer gate 清单；未勾选项是 release activity
- [M5_P3-05_RESIDUE_DECISIONS.md](./M5_P3-05_RESIDUE_DECISIONS.md) - 参数优化残片与旧假设处理结论
- [M5_P3-05_KICKOFF_PLAN.md](./M5_P3-05_KICKOFF_PLAN.md) - 冻结 kickoff 基线和历史启动计划，仅用于回看原始 scope、依赖顺序和回滚边界

## 设计输入

- [../phase3/PHASE3_P3-05_PARAM_OPTIMIZATION.md](../phase3/PHASE3_P3-05_PARAM_OPTIMIZATION.md)
- [../phase3/PHASE3_P3-05_PARAM_OPTIMIZATION_IMPLEMENTATION.md](../phase3/PHASE3_P3-05_PARAM_OPTIMIZATION_IMPLEMENTATION.md)
- [../phase3/PHASE3_P3-05_PARAM_OPTIMIZATION_FRONTEND.md](../phase3/PHASE3_P3-05_PARAM_OPTIMIZATION_FRONTEND.md)

这些 `phase3/` 文档只作为设计资产；实际任务拆分、runtime 决策和 reviewer gate 以本目录为准。

## 执行治理规则

`M5` 的每个 work stream 或新增 / 扩 scope 的变更项，都必须按下面顺序推进：

```text
planner alignment -> implementation -> reviewer gate
```

硬约束：

- 写文件前必须先形成 planner alignment note，并由 planner 明确认可。
- alignment note 至少包含 scope、write set、dependencies、non-goals、acceptance、rollback boundary 和 evidence plan。
- 一条 note 只覆盖一个可审阅的 cohesive write set；不得用宽泛 note 覆盖整轮 `M5` 实现。
- implementation 偏离已批准 note 的 scope、write set、dependencies、non-goals 或 acceptance 时，必须停下重新对齐，不能先做后补。
- reviewer 发现无 alignment note、实现超出 note、证据与 acceptance 不对应时，直接 `NO-GO`。

## 当前完成结论

- `M3 / P3-03` 已关闭，`M5 / P3-05 v1` 已完成本地代码验收并进入 PR/release closure。
- `M5` 首轮不直接引入 Celery/RQ；先复用现有 `BacktestService` 与当前 async task 模式。
- `app/optimization/algorithms.py` 是 isolated prototype，不视为 runtime-ready 能力。
- 首轮最小闭环是：创建优化任务 -> 执行有限 trial -> 记录进度和结果 -> 提取最优参数 -> 应用到回测配置。
- `M5 v1` 已完成上述最小闭环：后端 schema/service/API/task runtime、Backtest 页面最小入口、best 参数回填、focused smoke、frontend typecheck/build 与 backend full pytest 均已通过。
- `M5 v1` 冻结的是参数数量上限与 `trial_count` 上限；当前代码没有单用户 `running` job hard cap，不应声称已实现并发限制。该限制可在后续 release/ops 中另开。
- 本地自动化 API smoke 已完成；它不替代 live browser / staging 手工 smoke。
- live browser / staging smoke、生产 backup、发布前 schema-contract gate 与 release smoke 属于未完成的 release activity，不阻塞本地 `M5 v1` 代码验收。

## 使用顺序

1. 先读 `docs/EXECUTION_PLAN.md`。
2. 再读本文件。
3. 进入 [artifacts/](./artifacts/) 复核本地验收证据、review 结论和剩余 release activity。
4. 按 [M5_P3-05_REVIEW_CHECKLIST.md](./M5_P3-05_REVIEW_CHECKLIST.md) 确认哪些 gate 已完成、哪些仍是 release activity。
5. 需要理解 residue 或扩 scope 边界时，再看 [M5_P3-05_RESIDUE_DECISIONS.md](./M5_P3-05_RESIDUE_DECISIONS.md)。
6. 只有需要回看原始启动范围、并行任务拆分和回滚边界时，才进入 [M5_P3-05_KICKOFF_PLAN.md](./M5_P3-05_KICKOFF_PLAN.md)。

## 与历史执行包的关系

- `m3/` 保留 `Pre-M3` 与 `M3 / P3-03` closed baseline。
- `phase3/` 保留设计资产，不承担当前推进状态裁决。
- 旧 `M4 / P3-04` 已退役，不进入 `M5` 范围。
