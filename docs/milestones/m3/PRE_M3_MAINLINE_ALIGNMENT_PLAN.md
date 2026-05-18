# Pre-M3 Mainline Alignment Plan

> Status: active recovery source of truth
> Gate: must pass before `M3 / P3-03`
> Last updated: 2026-04-22
> Controller: Codex

`PRE_M3_DECISION.md` is the single live gate record for `W0` and `W5` approvals.

## 目标

在不引入兜底代码的前提下，先把当前主线重新收拢到可验收、可恢复、可发布的状态，再允许项目继续进入 `M3`。

这次修复的目标不是“顺手多做一点”，而是收口四类已经确认的漂移：

- production release correctness 漂移
- active runtime 与生产 schema 的契约漂移
- public / protected API interface contract 漂移
- 主线文档状态漂移
- 不属于当前 `PRD` 主线的 runtime residue

## 为什么现在必须先做这个

已经确认的事实是：

- `M2` 里程碑本身已验收
- 生产发布时，代码版本、migration 版本和生产库实际 schema 没有被强制锁死在同一个 gate 里
- active runtime 里还残留了不符合当前 `PRD` 边界的 `Strategy` 字段和读路径

因此当前的正确推进顺序不是“直接进入 `M3`”，而是：

`M2 accepted -> Pre-M3 alignment -> reviewer go -> M3`

## Source-of-truth 顺序

文档冲突时，按下面顺序裁决：

1. `docs/PRD.md`
2. `docs/ROADMAP.md`
3. `docs/EXECUTION_PLAN.md`（只负责里程碑位置、主路线状态与高层停止条件）
4. `PRE_M3_DECISION.md`（当前 live gate 与能否进入 `W5/M3` 的唯一裁决）
5. 本执行包（`Pre-M3` wave scope、依赖顺序、当前执行边界与恢复规则）
6. `PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`（live state / blockers / recovery handoff）
7. 对应 wave artifact
8. `docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md`
9. `docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md`
10. `docs/milestones/phase3/` 与 `phase4/` 设计资产

## 路线文档收敛原则

当前主路线只使用 3 份 route docs：

1. `docs/EXECUTION_PLAN.md`
2. `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`
3. `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`

`PRE_M3_DECISION.md` 继续保留，但只作为 gate / close-condition file 使用；tracker 与 wave artifacts 继续保留，用于中断恢复、分工边界和留痕。

## 范围

### In Scope

- 冻结 `Pre-M3` 的边界、分工、恢复顺序和 reviewer gate
- 修复 release correctness，补 migration/stamp/schema compatibility gate
- 修复 active runtime 中的 `Strategy` residue 与 ORM 读路径漂移
- 修复已确认的 API response / parameter contract 漂移，并把 live sweep 固化成可重复 smoke
- 把 `2026-04-21` review 新确认的 `W1` / `W2a` regression truthfully 回挂到既有 wave，而不是新开 wave 掩盖返工事实
- 把 `2026-04-21` 生产完整度审计暴露出的 partial-gap detection、BaoStock source-contract、partial-gap backfill blind spots 收口成独立 wave
- 为 market-data fault modes 建立可执行 owner split、artifact、blocker 与 truthfully recorded evidence
- 收口主线文档入口，使当前状态、下一步和恢复路径一目了然
- 清理已确认的非阻塞 residue，但不越界改产品方向

### Out Of Scope

- 不直接开始 `M3 / P3-03` 的业务开发
- 不在本轮重新打开 `M1` follow-up backlog
- 不以“兼容旧库”为由加入临时兜底字段、自由透传或 silent fallback
- 不把 `P3-04 策略社交` 重新带回 active plan-of-record
- 不把 historical daily-bars backfill 留在 `fetch_daily_task` 这类日常任务模块中；未来若需要历史补数，必须通过外部临时能力另行设计

## Wave 规划

| Wave | 目标 | Owner | 输入 | 输出 | Go / No-Go |
|------|------|-------|------|------|------------|
| `W0` 范围冻结 | 固化主线边界、分工、恢复顺序与执行包结构 | controller | `PRD`、`ROADMAP`、`EXECUTION_PLAN`、审计/残留文档 | plan、tracker、artifact 模板 | `W0` 未冻结前不开始并行实现；closure 以 `PRE_M3_DECISION.md` 为准 |
| `W1` 发布正确性 | 建立 release precheck、prod migration/stamp 路径、postdeploy schema smoke，并修掉 runtime bootstrap 抢在 Alembic 前创建受管表的路径 | `worker-release` | `W0`、生产事故事实、当前 deploy 文档/脚本、`2026-04-21` review finding: `init_db/create_all` 会破坏 `user_events` migration path | 发布治理方案、bootstrap/Alembic 对齐修复、脚本/文档修改、artifact | runtime bootstrap 仍会在 Alembic 前创建受管表，或仍没有清晰 prod schema 对齐路径，即 no-go |
| `W2` runtime/schema 对齐 | 清理 `Strategy` residue、覆盖所有 ORM 读路径并补 focused tests | `worker-runtime` | `W0`、残留清单、`W1` 的 release gate 结论用于 closure | model/schema/router/task 修复、artifact | 仍有遗漏 ORM 读路径即 no-go |
| `W2a` API contract 对齐 | 修复已确认的 API contract regression，保持 invalid analytics payload 在 `422` 路径，并完成 legacy `trade_date` string fallback consumer sweep 后再固化 representative live API sweep | controller + `worker-runtime` | `W1`、`W2`、线上报错与 interface drift 事实、`2026-04-21` review findings（analytics `500` / ISO 日期 fallback） | API contract regression 修复、focused tests、smoke script、artifact | invalid analytics payload 仍会走 `500`、legacy string-date fallback 仍未收口，或 representative contract smoke 未通过，即 no-go |
| `W2b` 数据完整性对齐 | 收口 active-path 的 partial-gap detection、BaoStock source-contract anomalies、bounded explicit-window partial-gap backfill 与故障模式测试治理；historical backfill 不属于 `Pre-M3` blocker，且不得继续留在日常任务模块中 | controller + `worker-runtime` | `W1` baseline、`W2a` 接口基线、`2026-04-21` 完整度审计与补数事实、已批准的 scheduler partial-gap baseline | data completeness artifact、验证/测试计划、anomaly inventory | active-path blind spot 未闭环、bounded repair 不可用或 fault-mode tests 未通过，即 no-go |
| `W3` 残留清理 | 处理导航降级、文案误导、死样式等非阻塞 residue，并确保当前保留下来的“真实支持偏好”在 bootstrap/login/首屏阶段也真正生效 | `worker-runtime` | `W2` / `W2a` 输出、`2026-04-21` reviewer finding（server-backed language preference 未在 Settings 外生效） | residue cleanup artifact | 误删真实 contract，或把“真实支持偏好”只停留在表单展示层而未在非 Settings 路由生效，即返工 |
| `W4` 主线文档终扫 | 在 `W1` ~ `W3` 与 `W2b` 后做最终 doc sweep，确保入口、状态与恢复路径全部写实 | controller | `W1`、`W2`、`W2a`、`W2b`、`W3` 输出 | docs 更新、artifact | 文档与代码/发布结论不一致即 no-go |
| `W5` 最终审核 | reviewer 汇总风险并决定 `M3` 能否启动 | `reviewer` | `W1` ~ `W4` artifacts（含 `W2b`） | `PRE_M3_DECISION.md` | reviewer 未给 `go` 则停在 `Pre-M3` |

## 分工矩阵

| Workstream | 责任角色 | 主要写集 | 主要产物 |
|-----------|----------|---------|----------|
| 范围冻结、顺序设计、返工门禁 | `planner` | 评审本计划、tracker、W0 artifact 的规划部分 | 分工矩阵、依赖顺序、恢复路径建议 |
| release correctness gate | `worker-release` | `docs/deployment/release_workflow.md`、`scripts/deploy_release.sh`、`scripts/build_release_images.sh`、`scripts/release_precheck.py`、`scripts/migration_live_validation.py`、`Makefile` 的 release targets、`alembic.ini`、`alembic/env.py`、`app/database.py`、`app/main.py`、dedicated release/bootstrap tests、W1 artifact | W1 产物 |
| runtime/schema 对齐 | `worker-runtime` | `app/models/stock_model.py`、`app/schemas/strategy_schema.py`、`app/api/routers/strategy_router.py`、`app/jobs/tasks/strategy_task.py`、`app/services/date_utils.py`、`app/services/indicator_service.py`、`app/services/fund_flow_service.py`、`app/api/routers/indicator_router.py`、focused strategy/API tests、`scripts/smoke_api_contracts.py`、W2/W2a artifacts | W2/W2a 产物 |
| 数据完整性与补数治理 | controller + `worker-runtime` | 当前活跃切片包含 `app/jobs/tasks/fetch_daily_task.py`、`tests/test_fetch_tasks.py`、`artifacts/W2b-data-completeness-alignment.md`；scheduler partial-gap 与 bounded explicit-window repair 保持为已完成基线，historical backfill 已退出 `Pre-M3` active scope | W2b 产物 |
| 前端残留与偏好落地 | `worker-runtime` | `web/src/router/index.ts`、`web/src/composables/useUserPreferences.ts`、`web/src/composables/useLocale.ts`、`web/src/views/Settings.vue`、`web/src/views/Attention.vue`、`web/src/views/Login.vue`、必要时 `web/src/App.vue`、`web/src/components/layout/AppHeader.vue`、W3 artifact | W3 产物 |
| 主线文档与状态对齐 | controller | `docs/EXECUTION_PLAN.md`、`docs/README.md`、milestone 索引与执行包、`PRE_M3` plan/tracker/decision | W0/W4 产物 |
| 审核与返工裁决 | `reviewer` | review artifact、决策文件 | findings、go/no-go |

## 当前执行分工矩阵

参照 `M1` 的 single-writer 规则，`Pre-M3` 当前 repair work 按 lane 拆分，任何超出写集的需求都必须先停下并在对应 artifact 里记录 handoff。

| Lane | Owner | Owned scope | Disjoint write set | Depends on | Recovery artifact |
|------|-------|-------------|--------------------|------------|-------------------|
| 协调 / docs lane | controller | `W0`/`W4` 文档、状态裁决、owner split 维护 | `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`、`PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`、`PRE_M3_DECISION.md`、`artifacts/W0-scope-freeze.md`、`artifacts/W4-doc-mainline-alignment.md` | `PRD`、`ROADMAP`、`EXECUTION_PLAN` | controller 在 tracker 与 decision 中维护最新 lane 状态 |
| `W1` release correctness lane | `worker-release` | release precheck、prod migration/stamp/schema gate、postdeploy smoke 路径、startup bootstrap 不得抢在 Alembic 前创建受管表 | `docs/deployment/release_workflow.md`、`scripts/deploy_release.sh`、`scripts/build_release_images.sh`、`scripts/release_precheck.py`、`scripts/migration_live_validation.py`、`Makefile` 的 release targets、`alembic.ini`、`alembic/env.py`、`app/database.py`、`app/main.py`、dedicated release/bootstrap tests、`artifacts/W1-release-correctness.md` | `W0` | `artifacts/W1-release-correctness.md` |
| `W2` runtime/schema lane | `worker-runtime` | `Strategy` residue 移除、ORM 读路径修复、focused tests | `app/models/stock_model.py`、`app/schemas/strategy_schema.py`、`app/api/routers/strategy_router.py`、`app/jobs/tasks/strategy_task.py`、dedicated strategy tests、`artifacts/W2-runtime-schema-alignment.md` | `W0`；`W1` gate freeze 影响 closure 但不阻塞 lane 内实现 | `artifacts/W2-runtime-schema-alignment.md` |
| `W2a` API contract lane | controller + `worker-runtime` | 已确认 API contract regression 修复、analytics validation 保持 `422` 路径、legacy `trade_date` string fallback consumer sweep、representative live smoke | `app/services/date_utils.py`、`app/services/indicator_service.py`、`app/services/fund_flow_service.py`、`app/services/pattern_service.py`、`app/api/routers/indicator_router.py`、`app/schemas/user_event_schema.py`、focused API/event/date tests、`scripts/smoke_api_contracts.py`、`artifacts/W2a-api-contract-alignment.md` | `W1`、`W2` | `artifacts/W2a-api-contract-alignment.md` |
| `W2b` data completeness lane | controller + `worker-runtime` | active-path partial-gap detection、BaoStock canonical/no-fallback bounded backfill、对应 focused tests；historical backfill 已从日常任务模块与 `Pre-M3` blocker 中移出 | `app/jobs/tasks/fetch_daily_task.py`、`tests/test_fetch_tasks.py`、`artifacts/W2b-data-completeness-alignment.md` | `W1` release baseline、`W2a` interface baseline、已批准的 scheduler partial-gap baseline | `artifacts/W2b-data-completeness-alignment.md` |
| `W3` residue lane | `worker-runtime` | active nav/default-home residue、Attention 提醒语义降级、server-backed language preference bootstrap 生效 | `web/src/router/index.ts`、`web/src/composables/useUserPreferences.ts`、`web/src/composables/useLocale.ts`、`web/src/views/Settings.vue`、`web/src/views/Attention.vue`、`web/src/views/Login.vue`、必要时 `web/src/App.vue`、`web/src/components/layout/AppHeader.vue`、`artifacts/W3-residue-cleanup.md` | `W2`、`W2a` | `artifacts/W3-residue-cleanup.md` |
| `W5` reviewer lane | `reviewer` | gate review、返工裁决、最终放行 | `PRE_M3_DECISION.md` 的 reviewer decision 段落、review artifact | `W1` ~ `W4` artifacts | `PRE_M3_DECISION.md` |

## Shared File Rules

- `PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`、tracker、decision 只由 controller 改；`W1`/`W2` worker 不直接改这些协调文件。
- `artifacts/W1-release-correctness.md` 由 `worker-release` 单写；`artifacts/W2-runtime-schema-alignment.md` 由 `worker-runtime` 单写。controller 只在 owner 变更或恢复协调时改抬头和状态。
- `artifacts/W2b-data-completeness-alignment.md` 由 controller + `worker-runtime` 共同维护，但必须基于可复现的审计结果与代码证据，不把未验证推测直接写入 tracker / decision。
- `artifacts/W3-residue-cleanup.md` 当前处于 reopened 状态；若需要进入 `web/src/App.vue` 之外的新前端共享文件，先在 artifact 里记录 why，并由 controller 回写 tracker。
- `alembic/versions/` 在 `W1`/`W2` 当前 repair window 内视为 frozen shared area；若任一 lane 认为必须新增/改写 revision，先停下，在 artifact 与 tracker 里记录 handoff，不得直接创建并行 migration head。
- `tests/conftest.py` 与其他共享 fixture 文件默认冻结；`W1`/`W2` 都优先改 dedicated test files。若必须改共享 fixture，先记录 handoff，再由 controller 重新分配单写 owner。
- `W1` 不进入 `app/models/stock_model.py` / `strategy_schema.py` / `strategy_router.py` / `strategy_task.py`；`W2` 不进入 release docs/scripts、`Makefile` release targets、`alembic.ini`、`alembic/env.py`。
- `W2b` 当前允许进入 `app/jobs/tasks/fetch_daily_task.py` 与 `tests/test_fetch_tasks.py` 这一条 active-path bounded partial-gap 写集；historical backfill 相关入口应删除或保持在 `Pre-M3` 外部，不再作为日常任务模块的一部分。
- `W3` 不进入后端 contract；当前只允许在已声明的前端残留/locale bootstrap 写集内修复 reviewer reopen 的问题。

## 并行边界

- `W0` 完成前，不允许任意并行改动
- `W1` 与 `W2` 当前允许并行执行，因为 write set 已拆开；但 `W2` 不能在 `W1` 还没写清 release gate 结论时宣告 closure
- `W2a` 依赖 `W1` / `W2` 基线，但仍留在 runtime/API contract write set 内，不进入 release lane 文件
- `W2b` 依赖 `W1` 的 release baseline 与 `2026-04-21` 完整度审计事实；当前以 scheduler partial-gap detection 与 bounded explicit-window repair 作为 active-path baseline，historical backfill 不再构成 `W4` / `W5` blocker
- `W1` 若发现需要 runtime/model/schema 改动，或 `W2` 若发现需要 release/deploy gate 改动，必须先在各自 artifact 中写下 handoff，再由 controller 更新 tracker
- `W3` 只能在 `W2` / `W2a` 识别出哪些 contract 必须保留后再做；当 reviewer reopen 指向“真实支持偏好未在 bootstrap 生效”时，可在声明的前端写集内修复
- `W4` 必须在 `W1` ~ `W3`（以及 `W2a` / `W2b` 证据收口）后执行，作为最终 doc sweep
- `W5` 只在 `W1` ~ `W4` artifact 完整且 `W2b` 有 truthfully recorded 结论时启动

## 中断恢复规则

如果执行在任意时点中断，恢复顺序固定为：

1. `docs/EXECUTION_PLAN.md`
2. `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_PLAN.md`
3. `docs/milestones/m3/PRE_M3_MAINLINE_ALIGNMENT_TRACKER.md`
4. 当前 wave 对应 artifact
5. `docs/PROJECT_MAINLINE_AUDIT_2026-04-20.md`
6. `docs/RESIDUE_REMOVAL_CANDIDATES_2026-04-20.md`

不要跳过 tracker 直接接代码；先确认当前卡在哪个 wave、阻塞项是什么、哪个 artifact 是最新事实。
只有在需要判断 release restriction、close condition 或 `go / no-go` 时，才进入 `docs/milestones/m3/PRE_M3_DECISION.md`。

如果恢复的是具体 lane，额外遵守：

- `W1` 恢复：只进 `W1-release-correctness.md` 和它声明的 release write set，不跨到 runtime 文件。
- `W2` 恢复：只进 `W2-runtime-schema-alignment.md` 和它声明的 runtime write set，不跨到 release 文件。
- `W2a` 恢复：先跑 `scripts/smoke_api_contracts.py`，再回到 `W2a-api-contract-alignment.md` 和它声明的 API contract write set。
- `W2b` 恢复：先读最新完整度报告与 `artifacts/W2b-data-completeness-alignment.md`，确认 `303` 个 BaoStock unsupported BJ universe 与 `22` 个 `no_source_but_db_present` anomaly 已被区分记录，再决定是否继续实现或仅更新计划。
- 如果 tracker 里出现 `handoff required` 或 shared-file freeze 解除，先读 tracker 的最新 owner 更新；只有涉及 gate / 放行裁决时才补读 decision，再继续。

## 返工触发条件

- 试图通过运行时代码兜底掩盖真实 schema 漂移
- 生产发布链路仍然不能回答“上线前库必须到哪个 revision / stamp 状态”
- 只修 API，不修后台任务或其他 ORM 读路径
- 仍把市场数据 freshness 近似成 `MAX(trade_date)`，而不记录 partial-gap blind spot
- 把 `303` 个 BaoStock unsupported BJ 标的与 `22` 个 `no_source_but_db_present` anomaly 混成同一类问题
- `W1` / `W2` 任一 lane 越过自己的 disjoint write set 直接改共享文件
- 文档仍然把仓库状态写成 `M2 kickoff 前`，或把 `P3-04 策略社交` 当成 active milestone
- 产物缺少恢复所需的 `changed files / commands / results / blockers / next step`

## 关闭条件

- `Pre-M3` 的 close condition / `go to start M3` 只以 `PRE_M3_DECISION.md` 为准。
- 本执行包保留 wave、write set、依赖顺序和恢复规则，不再维护第二套关闭条件。
