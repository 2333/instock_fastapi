# Pre-M3 Mainline Alignment Tracker

> Last updated: 2026-04-22
> Purpose: keep `W1` / `W2` / `W2a` / `W2b` / `W3` repair lanes recoverable if work is interrupted

## 恢复顺序

1. 先看 `docs/EXECUTION_PLAN.md`
2. 再看 `PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`
3. 然后看本 tracker
4. 最后进入当前 wave artifact

## 当前状态

- `M0` / `M1` / `M2`：已完成收口
- 现行路线：已移交给 [docs/EXECUTION_PLAN.md](../../EXECUTION_PLAN.md) 指向的里程碑；本 tracker 仅保留 `Pre-M3` closed baseline
- 历史禁止事项：启动 `M3` 前不得绕过 `schema_contract` release gate
- `PRE_M3_DECISION.md` 是 `W0` / `W5` 的唯一 live gate record
- `Pre-M3` 执行期主路线只看 3 份 route docs：`docs/EXECUTION_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`
- `PRE_M3_DECISION.md` 仅作为 gate file 使用，不承担日常路线导航
- `Pre-M3` 已作为 closed baseline 保留；当前执行可从 `M3 / P3-03` kickoff 继续
- `2026-04-21` review reopen 的 `W1` / `W2a` findings 已修复并通过 `reviewer + code-review-expert` double review
- `W5 reviewer gate` 已完成，当前结论已翻转为 `GO to start M3`
- `2026-04-22` 真实目标库已完成 truthful Alembic onboarding，`schema_contract` gate 在真实目标库通过
- `2026-04-22` `daily_bars` uniqueness drift 已通过真实 DDL + runtime code removal truthfully 收口
- `2026-04-22` 用户已明确 historical backfill 不属于 `Pre-M3` blocker，也不应留在 `fetch_daily_task` 这类日常任务模块里；对应入口已从 active code path 删除，`W2b` 以 active-path baseline truthfully 关闭
- `2026-04-22` reviewer reopen 的两个 `W2b` follow-up finding（跨窗口状态误伤、BaoStock unsupported target 混入 active-path）均已修复；focused tests 通过，`reviewer + code-review-expert` 复核均无新的 blocking finding
- 当前 repair work 已拆成三个 active lane：`worker-release` 负责 `W1`，`worker-runtime` 负责 `W2` / `W2a`，controller + `worker-runtime` 负责 `W2b`

## 当前 owner split

| Lane | Owner | 当前职责 |
|------|-------|----------|
| 协调 / docs | controller | 维护 plan、tracker、decision 与 handoff 状态 |
| `W1` 发布正确性 | `worker-release` | 冻结 prod migration/stamp/schema gate，修补 release proof path |
| `W2` runtime/schema | `worker-runtime` | 移除 `Strategy` residue，修复 ORM 读路径与 focused tests |
| `W2a` API contract | controller + `worker-runtime` | 修复 API contract regression、恢复 analytics `422` 路径并完成 legacy date fallback sweep |
| `W2b` 数据完整性 | controller + `worker-runtime` | 已关闭：当前 approved baseline 包含 canonical BaoStock helper/taxonomy、scheduler partial-gap detection、bounded explicit-window partial-gap backfill；historical backfill 已退出 `Pre-M3` active scope |
| `W3` 残留清理 | `worker-runtime` | 已完成 active residue 降级与 server-backed language preference bootstrap 修复，等待 `W4` 汇总进主线文档 |
| `W5` reviewer | `reviewer` | 汇总结论并决定能否启动 `M3` |

## 当前 disjoint write sets

- `W1`: `docs/deployment/release_workflow.md`、`scripts/deploy_release.sh`、`scripts/build_release_images.sh`、`scripts/release_precheck.py`、`scripts/migration_live_validation.py`、`Makefile` 的 release targets、`alembic.ini`、`alembic/env.py`、`app/database.py`、`app/main.py`、dedicated release/bootstrap tests、`artifacts/W1-release-correctness.md`
- `W2`: `app/models/stock_model.py`、`app/schemas/strategy_schema.py`、`app/api/routers/strategy_router.py`、`app/jobs/tasks/strategy_task.py`、dedicated strategy/API tests、`artifacts/W2-runtime-schema-alignment.md`
- `W2a`: `app/services/date_utils.py`、`app/services/indicator_service.py`、`app/services/fund_flow_service.py`、`app/services/pattern_service.py`、`app/api/routers/indicator_router.py`、`app/schemas/user_event_schema.py`、focused API/event/date tests、`scripts/smoke_api_contracts.py`、`artifacts/W2a-api-contract-alignment.md`
- `W2b`: `app/jobs/tasks/fetch_daily_task.py`、`tests/test_fetch_tasks.py`、`artifacts/W2b-data-completeness-alignment.md`
- `W3`: `web/src/router/index.ts`、`web/src/composables/useUserPreferences.ts`、`web/src/composables/useLocale.ts`、`web/src/views/Settings.vue`、`web/src/views/Attention.vue`、`web/src/views/Login.vue`、必要时 `web/src/App.vue`、`web/src/components/layout/AppHeader.vue`、`artifacts/W3-residue-cleanup.md`
- frozen shared area: `alembic/versions/`、`tests/conftest.py`、以及本 tracker / plan / decision；需要改动时先在 artifact 记录 `handoff required`

## 执行看板

| ID | 任务 | 状态 | Owner | Depends | Artifact | Last Update | 下一步 | Blocked By |
|----|------|------|-------|---------|----------|-------------|--------|------------|
| `W0` | 范围冻结、入口文档与恢复路径落盘 | completed | controller | - | [W0-scope-freeze.md](./artifacts/W0-scope-freeze.md) | 2026-04-20 | 启动 `W1` 发布正确性修复 | - |
| `W1` | 发布正确性修复 | completed | controller + `worker-release` | `W0` | [W1-release-correctness.md](./artifacts/W1-release-correctness.md) | 2026-04-22 | 作为当前 release baseline 继续生效；真实目标库 onboarding + `schema_contract` gate 已完成，可直接供 `M3` 继承 | - |
| `W2` | runtime/schema 对齐 | completed | controller + `worker-runtime` | `W0`; `W1` gate output required before closure | [W2-runtime-schema-alignment.md](./artifacts/W2-runtime-schema-alignment.md) | 2026-04-20 | 以当前最小 contract 进入 `W3` 残留清理 | - |
| `W2a` | API contract sweep 与生产接口对齐 | completed | controller + `worker-runtime` | `W1`, `W2` | [W2a-api-contract-alignment.md](./artifacts/W2a-api-contract-alignment.md) | 2026-04-21 | 作为当前接口基线继续生效，等待 `W4` 文档终扫收口 | real PostgreSQL legacy-row integration coverage still desirable |
| `W2b` | 数据完整性对齐与故障模式治理 | completed | controller + `worker-runtime` | `W1`, `W2a` | [W2b-data-completeness-alignment.md](./artifacts/W2b-data-completeness-alignment.md) | 2026-04-22 | 以当前 active-path baseline 进入 `W4` 文档终扫；historical backfill 后续若需要，改走外部临时能力 | - |
| `W3` | 残留清理与导航降级 | completed | `worker-runtime` | `W2`, `W2a` | [W3-residue-cleanup.md](./artifacts/W3-residue-cleanup.md) | 2026-04-21 | 等待 `W4` 把当前 residue cleanup 证据并入主线文档 | - |
| `W4` | 主线文档终扫 | completed | controller | `W1`, `W2`, `W2a`, `W2b`, `W3` | [W4-doc-mainline-alignment.md](./artifacts/W4-doc-mainline-alignment.md) | 2026-04-22 | 文档入口、当时执行包与设计资产分层已收敛；`W5` 已完成并在当时将主线切换到 `M3 / P3-03` | - |
| `W5` | reviewer 最终决策 | completed | `reviewer` | `W1` ~ `W4` | [PRE_M3_DECISION.md](./PRE_M3_DECISION.md) | 2026-04-22 | 结论：`GO to start M3`；`Pre-M3` 已关闭，下一步切换到 `M3 / P3-03` kickoff | - |

## 使用规则

- 每个 wave 结束时都要更新对应 artifact
- tracker 只记录“当前真相”，不要把愿望写成已完成
- 如果某 wave 被返工，直接把状态改回 `in_progress` 并写明 blocker
- 如果 lane 在中断前发现需要越过 write set，先把 tracker 的对应行改成 `blocked` 或在 `Blocked By` 列写明 `handoff required`

## 中断接手清单

1. 先按顶部“恢复顺序”读完 `EXECUTION_PLAN -> PRE_M3 plan -> 本 tracker`，确认当时 wave、owner 与 blocker。
2. 如果恢复的工作涉及 release restriction、close condition 或 `go / no-go` 判断，再补读 `PRE_M3_DECISION.md`。
3. 只进入该 lane 的 artifact 与 write set；不要顺手改另一个 lane 的文件。
4. 开工前先确认上一次记录的 `Next step` 仍然有效；如果不再有效，先把原因写回 artifact，再继续。
5. 停手前必须补齐 `Changed files`、`Commands run`、`Results`、`Open risks`、`Next step`、`Blocked by`、`Recovery note`。
