# Pre-M3 Decision

> Status: `W0` / `W1` / `W2` / `W2a` / `W2b` / `W3` / `W4` approved, `W5` completed with `GO`, release governance active
> Last updated: 2026-04-22

This file is the single live gate record for `W0` / `W5` and the current
release-eligibility rules for the active `Pre-M3` repair baseline.

## 当前结论

- `GO` to execute `Pre-M3`
- `GO` to treat `W1` as the current approved release/bootstrap baseline
- `GO` to treat `W2` as the current approved runtime/schema baseline
- `GO` to treat `W2a` as the current approved interface baseline
- `GO` to treat `W3` as the current approved residue/bootstrap baseline
- `GO` to treat `W2b` as the current approved market-data-integrity baseline for active runtime paths
- `GO` to treat `W4` as the current approved documentation-alignment baseline
- `GO` from `W5 reviewer gate` to start `M3 / P3-03`
- `GO` to close `Pre-M3` and hand off to `M3 / P3-03`
- `NO-GO` to cross-edit the other lane's write set without an explicit handoff recorded in artifact + tracker

## W5 Final Gate Result

`GO` to start `M3`.

Release/schema blockers closed on 2026-04-22:

1. The real target database has completed truthful schema onboarding:
   - one-time boundary alignment via `scripts/pre_m3_schema_onboarding_20260422.sql`
   - onboarding audit passed with `0` blockers
   - Alembic stamped truthfully to `m2_user_events`
   - `./.venv/bin/python scripts/release_precheck.py --release-class schema_contract --env-file .env` now passes on the real target DB
2. The live `daily_bars` schema contract is now truthfully closed for active runtime paths:
   - `uq_daily_bars_ts_code_trade_date_dt` and `ix_daily_bars_trade_date_dt` exist on the real target DB
   - `fetch_daily_task.py` no longer keeps a compatibility downgrade path for `daily_bars` writes

Final review outcome:

- `reviewer`: no remaining code/runtime/release blocker after the final doc truthfulness pass
- `code-review-expert`: no additional blocking finding on the final W1/W2b delta

Decision:

- `Pre-M3` is now closed
- `M3 / P3-03` may start from the current baseline

## Pre-M3 Close Condition

只有同时满足以下条件，才允许进入 `W5 reviewer gate`；当前这些条件均已满足：

- `W1` 的 release correctness gate 已落地，且 future `schema_contract` release 所需的 truthful onboarding / baseline 路径已写实
- `W1` 的 runtime bootstrap 不再抢在 Alembic 前创建受管表，当前 release path 不会被 `init_db/create_all` 破坏
- `W2` / `W2a` 已收口 active runtime 与 representative API contract，当前主链不再存在已知 `500` / response-contract 漂移，invalid analytics payload 会回到 `422`，legacy `trade_date` string fallback consumer sweep 已完成
- `W2b` 已写实并收口 active-path 市场数据完整性 blind spots，至少覆盖 partial-gap detection、BaoStock source-contract anomaly inventory、bounded explicit-window repair 与 fault-mode verification 要求；historical backfill 不属于 `Pre-M3` blocker
- `W3` 已收口会误导主线判断的 active residue，至少覆盖 `Workspace`、`Settings`、`Attention` 的提醒语义
- `W4` 已完成，且主路线文档已收敛到 `EXECUTION_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`

满足以上条件后，`W5 reviewer gate` 已显式给出 `go to start M3`，因此允许启动 `M3 / P3-03`。

## Current release eligibility

- `GO`: non-schema production releases, but only through `prod-release-precheck`
  + `prod-deploy-version` + postdeploy smoke
- `GO`: schema-/ORM-contract-changing releases only when the selected target
  database is under Alembic control and the `schema_contract` gate passes
- `NO-GO`: bypassing `scripts/release_precheck.py` or treating legacy deploy
  commands as sufficient release proof
- Note: one-time onboarding/stamp is now complete on the current target DB; future schema-changing releases must use the normal `schema_contract` precheck/upgrade path, not restamp.

## 当前授权的 owner split

- controller: owns `PRE_M3` coordination docs and updates lane state when handoff
  is needed
- `worker-release`: owns `W1` release correctness lane and its declared release
  write set
- `worker-runtime`: owns `W2` / `W2a` runtime/API-contract lane and its declared runtime write
  set
- controller + `worker-runtime`: jointly own `W2b` market-data-integrity lane and its declared scheduler/bounded-backfill/source-contract write set
- `worker-runtime`: owns the current approved `W3` residue/bootstrap lane and its declared frontend write set
- reviewer: keeps final `W5` go / no-go authority

## 当前并行执行约束

1. `W1` 与 `W2` 可以同时推进，但都必须留在各自 artifact 声明的 write set 内。
2. `W2/W2a` 可以先完成 runtime residue 修复、API contract 对齐与 focused tests，但不能在 `W1` 未冻结 release gate 之前宣告整体 closure。
3. `W2b` 以 active-path partial-gap detection 与 bounded explicit-window repair 为关闭口径；historical backfill 已退出 `Pre-M3` blocker，也不得继续留在 `fetch_daily_task` 这类日常任务模块里。
4. 一旦任一 lane 需要进入 `alembic/versions/`、`tests/conftest.py` 或对方 lane 的文件，必须先停下并记录 handoff。
5. 如果执行中断，先读 tracker，再回到对应 lane artifact 继续，不跳过 gate 记录。

## 决策依据

- `M2` 里程碑已验收，但生产发布链路曾存在 release correctness 漂移
- `W1` 已补上 release precheck、deploy gate 与 operator 输入约束
- `W2` 已移除当前主线之外的 `Strategy` residue，并覆盖已知 ORM 读路径
- `W2a` 已修复已知线上 `500`，并用 live API contract smoke 把 public/protected representative routes 固化为当前接口基线
- `2026-04-21` review reopen 的两项 finding 现已关闭：analytics invalid payload 重新回到 `422` 路径，startup bootstrap 不再在 Alembic 前创建 `user_events`
- `reviewer` 与 `code-review-expert` 对 `W1/W2a` 当前修复均未提出新的 blocking finding
- `2026-04-21` 生产完整度审计与补数已证明：主链曾存在 market-data completeness blind spots，特别是 `daily_bars` uniqueness drift、partial-gap detection blind spot、BaoStock source-contract anomalies 与 partial-gap backfill limitation；当前 W2b 已收口 scheduler partial-gap detection 与 bounded explicit-window partial-gap backfill 两个 active-path 子切片
- `2026-04-22` 用户已明确：historical backfill 不属于当前推进 blocker，且不应继续留在 `fetch_daily_task` 这类日常任务模块里；对应历史入口已从 active code path 删除，未来如需历史补数，改走外部临时能力
- `2026-04-22` reviewer reopen 的两个 `W2b` follow-up finding 已修复：bounded repair 不再被其他窗口状态误伤，BaoStock unsupported `BJ` / ETF target 不再混入 active-path baseline；focused tests 通过，reviewer 复审 `No findings`
- 主线入口文档已完成 `W4` 收口：`EXECUTION_PLAN.md` 是唯一 `plan-of-record`，当前执行包固定为 `m3/`，`phase3/phase4` 与审计/残留文档已降级为设计/分析资产入口
- 当前主路线只以 `EXECUTION_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md` 三份 route docs 为日常入口；`PRE_M3_DECISION.md` 仅作 gate file
- `2026-04-22` 真实目标库已完成 truthful schema onboarding，evidence 记录在 `docs/milestones/m3/artifacts/W1-prod-schema-onboarding-2026-04-22.json`
- `2026-04-22` `schema_contract` release gate 已在真实目标库通过
- `2026-04-22` `daily_bars` live uniqueness drift 已通过真实 DDL + runtime code removal truthfully 关闭
- `2026-04-22` `W5 reviewer gate` 复核后只发现两处 stale doc blocker；回写 decision/tracker 后无新增 blocker，因此 `M3` 由 `NO-GO` 翻转为 `GO`

## 当前冻结的执行顺序

1. `W0` 范围冻结与恢复入口
2. `W1` 发布正确性
3. `W2` runtime/schema 对齐
4. `W2a` API contract sweep 与生产接口对齐
5. `W2b` 数据完整性对齐
6. `W3` 残留清理
7. `W4` 主线文档终扫
8. `W5` reviewer 最终放行

## Approvals

- controller: Codex
- planner: approved for owner split / disjoint write-set execution
- reviewer: approved for `W0` baseline and `W1` / `W2` implementation
