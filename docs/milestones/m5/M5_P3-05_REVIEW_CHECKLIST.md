# M5 / P3-05 Reviewer Checklist

更新时间：2026-05-21

## 启动前 Gate

- [x] `docs/EXECUTION_PLAN.md`、`docs/README.md`、`docs/milestones/README.md` 均指向 `M5 / P3-05` 为当前 active route。
- [x] `docs/milestones/m5/` 是当前执行包入口。
- [x] `M5` 执行治理规则已写明：`planner alignment -> implementation -> reviewer gate`。
- [x] planner alignment note 的最小字段已明确：scope、write set、dependencies、non-goals、acceptance、rollback boundary、evidence plan。
- [x] reviewer 可因无 alignment note、实现超出 note、证据与 acceptance 不对应直接 `NO-GO`。
- [x] `docs/milestones/m3/` 只作为 `Pre-M3` 与 `M3` closed baseline。
- [x] `docs/milestones/phase3/PHASE3_P3-05*` 只作为设计输入，不承担执行状态裁决。
- [x] P3-05 文档不再声称 Celery/RQ、TaskBroker、optimizationApi 或后端 optimization API 已存在。
- [x] `app/optimization/algorithms.py` 的 experimental / isolated 状态已明确。
- [x] 架构图和类图没有把 optimization runtime 写成当前已运行能力。

## M5 实现前 Gate

- [x] 当前 slice 已有 planner 认可的 alignment note。
- [x] alignment note 覆盖一个可审阅的 cohesive write set，没有试图覆盖整轮 `M5`。
- [x] write set、dependencies、non-goals、acceptance、rollback boundary、evidence plan 均已冻结。
- [x] Schema/model 字段已冻结。
- [x] API contract 已冻结。
- [x] 任务状态机和取消语义已冻结。
- [x] 参数数量上限、`trial_count` 上限和参数空间限制已冻结。
- [x] 单用户 `running` job hard cap 明确不纳入 `M5 v1` 当前代码，后续 release/ops 可另开；不得声称 v1 已实现并发限制。
- [x] 回滚边界已明确。
- [x] 最小 smoke 路径已明确。

## 实现后 Gate

- [x] 实现没有超出对应 planner alignment note。
- [x] artifact 已记录 alignment note 链接 / ID、changed files、evidence、reviewer result、follow-ups / out-of-scope residue。
- [x] reviewer result 明确为 `approved` / `changes requested` / `no-go`。
- [x] 后端 focused tests 通过。
- [x] 前端 `typecheck` / `build` 通过。
- [x] Alembic head/current 一致。
- [x] 本地自动化 API smoke 覆盖 job 创建、执行、trial 结果、best 参数和 best 回测回放。
- [ ] live browser / staging 手工 smoke 覆盖 job 创建、progress、trial 结果、best 参数和取消；API smoke 不替代该项，这是 release activity，不阻塞本地 `M5 v1` 代码验收。
- [ ] 生产发布前 backup、schema-contract gate 和 release smoke 尚未完成；这是 release activity，不阻塞本地 `M5 v1` 代码验收。
