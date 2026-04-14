# M1 文档索引

`M1` 对应 Phase 1.5 数据层 / Timescale 底座。当前权威重启入口是 [M1_RESTART_PLAN.md](./M1_RESTART_PLAN.md)。

旧 kickoff / readiness 文档保留为历史上下文；如果它们引用已删除的 readiness 或 Timescale 过渡脚本，以 `M1_RESTART_PLAN.md` 为准。

当前阶段验收已收敛为 token-independent 范围：`daily_bars`、本地 `technical_factors`、Alembic existing-schema 路径、质量检查、Timescale 健康检查。`daily_basic` / `stock_st` 作为 gated follow-up 保留，不再阻塞当前阶段收口。

## 总览与启动材料

- [M1_RESTART_PLAN.md](./M1_RESTART_PLAN.md) - 当前 source of truth
- [DATA_LAYER_REPORT.md](./DATA_LAYER_REPORT.md)
- [M1_INITIATION_TASKS.md](./M1_INITIATION_TASKS.md)
- [M1_READINESS_SUMMARY.md](./M1_READINESS_SUMMARY.md)
- [M1_KICKOFF_CHECKLIST.md](./M1_KICKOFF_CHECKLIST.md)
- [M1_TUSHARE_TOKEN_BLOCK.md](./M1_TUSHARE_TOKEN_BLOCK.md)
- [M1_PROGRESS_TRACKER.md](./M1_PROGRESS_TRACKER.md)

## 任务与模板

- [M1_TASK_BREAKDOWN.md](./M1_TASK_BREAKDOWN.md)
- 当前只迁移 `origin/main` 已存在的 `M1` 文档；旧长分支上的额外 `M1_TASK_WS*.md` 任务包不纳入本次 rebaseline PR。

## 当前使用约定

- `M1_RESTART_PLAN.md` 是重启后的执行口径。
- 其他文档目前作为 `M1` 准备资产和历史分析保留，不代表 `M1` 已正式启动。
- 如旧文档仍指向 `scripts/check_m1_readiness.py` 等已删除脚本，不要直接执行，需按 restart plan 重新做当前仓库的 readiness check。
