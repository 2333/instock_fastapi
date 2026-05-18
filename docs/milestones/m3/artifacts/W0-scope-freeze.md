# W0 Scope Freeze

> Status: completed
> Owner: controller
> Depends: -
> Last updated: 2026-04-20

`PRE_M3_DECISION.md` 是本 wave 的唯一 live gate record。

## 输入

- `docs/PRD.md`
- `docs/ROADMAP.md`
- `docs/EXECUTION_PLAN.md`
- `docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md`
- `docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md`

## 本 wave 冻结内容

- 当前 active 路线不是直接进入 `M3`，而是先执行 `Pre-M3`
- `M0` / `M1` / `M2` 已视为完成收口
- `P3-04 策略社交` 不再属于 active plan-of-record
- 恢复顺序固定为：`EXECUTION_PLAN -> Pre-M3 plan -> tracker -> 当前 wave artifact`
- `W1` ~ `W5` 的 owner、依赖和 gate 已冻结

## Changed files

- `docs/EXECUTION_PLAN.md`
- `docs/README.md`
- `docs/milestones/README.md`
- `docs/milestones/m2/README.md`
- `docs/milestones/phase3/README.md`
- `docs/deployment/release_workflow.md`
- `docs/milestones/m3/`

## Commands run

- `sed -n ...` / `rg ...` for current-doc drift inspection
- `mkdir -p docs/milestones/m3/artifacts`

## Results

- `Pre-M3` 执行包、tracker 与 artifact 模板已落盘
- 主线入口文档已从 “`M2 kickoff 前`” 切换到 “`Pre-M3`”
- `P3-04` 已在文档层面从 active plan-of-record 退役
- `planner` 已完成结构复核并通过

## Open risks

- `W1` 之前的 schema/ORM 生产发布仍处于 `NO-GO`

## Next step

- 按 `PRE_M3_DECISION.md` 维持当前 release restriction
- 启动 `W1` 发布正确性修复

## Blocked by

- -
