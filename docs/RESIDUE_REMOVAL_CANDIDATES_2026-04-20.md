# Residue Removal Candidates

> 分析/清理清单文档，不是当前主线推进入口。
> 当前状态、下一步和执行顺序请先看 `docs/EXECUTION_PLAN.md`。

> Date: 2026-04-20
> Goal: identify code, docs, and plan items that should not stay on the active mainline

## Decision rule

If a capability is not part of the current `PRD -> ROADMAP -> EXECUTION_PLAN` mainline, it should not stay in:

- active runtime code
- active API/schema contracts
- production schema expectations
- primary navigation
- current plan-of-record

Historical design is allowed to exist only as archive/design material, not as half-active runtime.

## A. Must change in active plan-of-record and governance docs

### A1. Retire `P3-04 策略社交` from the active plan-of-record

Why:

- `PRD` explicitly says InStock is not a community platform and that `社区 / 评论 / 排行榜` are never-do items.
- But `EXECUTION_PLAN` still keeps `M4` as `策略社交`.

Evidence:

- `docs/PRD.md`
- `docs/EXECUTION_PLAN.md`
- `docs/milestones/phase3/PHASE3_P3-04_STRATEGY_MARKET.md`

Action:

1. change `docs/EXECUTION_PLAN.md` so `P3-04 策略社交` no longer appears as an active committed future milestone
2. replace downstream references that still present it as a future committed milestone
3. reclassify `P3-04` docs as historical rejected design rather than future execution material

Decision:

- `must remove`

Recommended wording:

- `P3-04 策略社交与 PRD v2.0 的硬边界冲突，自 2026-04-20 起不再属于 active plan-of-record。docs/milestones/phase3/P3-04* 保留为历史设计参考，不代表承诺实施、运行时契约或未来 milestone 默认入口。`

### A2. Fix active document status drift

Files:

- `docs/EXECUTION_PLAN.md`
- `docs/README.md`

Why:

- `M2` acceptance is already `go`, but active docs still tell readers the repo is at `M2 kickoff 前`.
- This does not crash runtime, but it pollutes the plan-of-record and causes incorrect execution decisions.

Decision:

- `must fix`

## B. Must remove from active runtime

### B1. Strategy social and public-library residue in ORM model

Files:

- `app/models/stock_model.py`

Fields: hard social residue

- `is_public`
- `is_official`
- `rating`
- `rating_count`
- `favorite_count`
- `comment_count`

Fields: non-mainline public-library / display metadata

- `backtest_count`
- `view_count`
- `tags`
- `risk_level`
- `suitable_market`

Why:

- The first group comes from the old strategy-social/community design.
- The second group comes from the old public-strategy-library presentation model.
- Neither group belongs in the current personal-tool mainline runtime.
- Together they create schema expectations that are absent in production.

Decision:

- `must remove`

### B2. Strategy social and public-library residue in response schema

Files:

- `app/schemas/strategy_schema.py`

Fields: hard social residue

- `is_public`
- `is_official`
- `rating`
- `rating_count`
- `favorite_count`
- `comment_count`
- `user_rating`
- `user_favorited`

Fields: non-mainline public-library / display metadata

- `backtest_count`
- `view_count`
- `tags`
- `risk_level`
- `suitable_market`

Why:

- These fields keep the social or public-library contract alive at the API level even if the UI does not use it.

Decision:

- `must remove`

### B3. All ORM read paths that assume the leaked `Strategy` schema

Files:

- `app/api/routers/strategy_router.py`
- `app/jobs/tasks/strategy_task.py`

Current risk:

- Active API paths execute `select(Strategy)`, which pulls every ORM-mapped column.
- The scheduled strategy job also executes `select(Strategy)`.
- Once the model contains leaked fields, any old DB schema will fail on read or background task execution.

Decision:

- `must remove or refactor together with B1/B2`

## C. Should be downgraded or removed from active navigation

### C1. TradingView workspace

Files:

- `web/src/router/index.ts`
- `web/src/components/layout/AppHeader.vue`
- `web/src/views/Workspace.vue`
- `web/src/composables/useUserPreferences.ts`

Why:

- The page is actively exposed in top navigation.
- Its shape leans toward a trading terminal/workstation experience.
- Current PRD explicitly warns against drifting toward `看盘终端化`.
- It is not part of current milestone acceptance materials.

Recommended action:

1. remove from top navigation now
2. keep existing `defaultHome` preference contract working until a safe fallback/migration is in place
3. either archive the page or keep it as an internal experiment outside mainline

Decision:

- `should remove from active navigation`
- `physical delete optional after product confirmation`

### C2. Settings page with mixed real settings contract and placeholder UI

Files:

- `web/src/router/index.ts`
- `web/src/components/layout/AppHeader.vue`
- `web/src/views/Settings.vue`
- `app/api/routers/auth_router.py`
- `web/src/api/index.ts`

Why:

- The page is actively exposed from header/user menu.
- It contains notification/data-source toggles that are not part of current milestone delivery.
- Several controls are local-only UI state and do not represent stable product commitments.
- But `/auth/settings` and `user_settings` are real capabilities and should not be accidentally deleted with the placeholder UI.

Recommended action:

1. remove from active navigation if not part of the next milestone
2. keep the real settings/preferences contract
3. if preferences are needed, keep only truly implemented settings and cut placeholders

Decision:

- `should downgrade or shrink heavily`

## D. Optional cleanup after the main blockers

### D1. Attention-page reminder wording and hidden alert plumbing

Files:

- `web/src/views/Attention.vue`
- `web/src/api/index.ts`
- `app/api/routers/attention_router.py`
- `app/services/attention_service.py`
- `app/models/stock_model.py`
- `app/schemas/stock_schema.py`

Current state:

- The UI subtitle still says `设置提醒条件`.
- Visible `alert_conditions` editing was already removed during rebaseline.
- Backend contract and model field still accept/store `alert_conditions`.

Why this is tricky:

- It overlaps with future `M3` alerting.
- It was also documented in earlier mainline summaries as part of attention management.

Recommended action:

1. at minimum, fix the misleading copy now
2. decide whether `alert_conditions` stays as passive watchlist metadata or is removed until `M3`

Decision:

- `optional cleanup with product decision`

### D2. Dead CSS / dead concept residue for reports and optimization on Dashboard

Files:

- `web/src/views/Dashboard.vue`

Why:

- The file still contains style blocks for `reports` and `optimization` cards that are no longer rendered.
- This does not break runtime, but it keeps old feature concepts visually alive in the codebase.

Decision:

- `safe cleanup`

## E. Keep as archive only

### E1. Phase 3 strategy-social design docs

Files:

- `docs/milestones/phase3/PHASE3_P3-04_STRATEGY_MARKET.md`
- `docs/milestones/phase3/PHASE3_P3-04_STRATEGY_MARKET_FRONTEND.md`
- `docs/milestones/phase3/PHASE3_P3-04_STRATEGY_MARKET_IMPLEMENTATION.md`

Action:

- keep as historical design only if needed for audit
- otherwise move to a clearer `archive/rejected` area

Decision:

- `archive only`

### E2. Old v1 community mentions

Files:

- `docs/archive/PRD_v1_archive.md`
- `docs/archive/ROADMAP_v1_archive.md`
- `docs/archive/EXECUTION_PLAN_v1_archive.md`

Decision:

- `keep archived`

## F. Keep as backlog, not as active residue

### F1. `M1` gated follow-up

Keep:

- `daily_basic`
- `stock_st`
- related screening integration

Why:

- These are explicitly accepted as open follow-up in `M1`, not accidental residue.

Decision:

- `keep as backlog`

### F2. `M3 / P3-03` alerting, `M5 / P3-05` optimization, `M6 / P3-06` data insights, `M7 / P3-02` recommendation

Why:

- These are still legitimate future capabilities as long as they stay aligned with the personal-tool product and are re-validated milestone by milestone.

Decision:

- `keep as backlog`

## G. Do not remove by mistake

These items may look suspicious by name, but they are aligned with the current mainline or accepted milestone work.

### G1. Selection-page `评分`

Files:

- `web/src/views/Selection.vue`

Meaning:

- this is result match score / ranking score, not community rating

Decision:

- `keep`

### G2. Backtest `report`

Files:

- `app/services/backtest_service.py`
- `tests/test_backtest_report_structure.py`

Meaning:

- this is structured backtest output, not `M6` report-generation residue

Decision:

- `keep`

### G3. Market task-health `alerts`

Files:

- `app/services/market_data_service.py`
- `app/api/routers/market_router.py`

Meaning:

- these are data freshness / fetch audit alerts, not user notification-system residue

Decision:

- `keep`

### G4. Patterns page and stock-detail pattern blocks

Files:

- `web/src/views/Patterns.vue`
- `web/src/views/StockDetail.vue`

Meaning:

- they are part of the core scan/verify analysis capability, not off-mainline social or AI scope

Decision:

- `keep`

### G5. M2 event tracking

Files:

- `app/api/routers/events_router.py`
- `app/services/event_service.py`
- `app/schemas/user_event_schema.py`
- `web/src/composables/useAnalytics.ts`

Meaning:

- this is the accepted `M2` milestone, not accidental residue

Decision:

- `keep`

## H. Recommended execution order

### Wave 0: release correctness and runtime safety

1. recover release correctness before any plan cleanup
2. align production DB under a controlled migration/stamp path
3. prove schema compatibility before the next feature release

### Wave 1: highest-value cuts

1. remove strategy social/public-library residue from runtime model/schema/query paths
2. cover every `Strategy` ORM read path, including API and scheduled jobs
3. stop runtime/schema mismatch first

### Wave 2: governance doc cleanup

1. retire `P3-04 策略社交` from the active plan-of-record
2. fix `M2` status drift in `docs/EXECUTION_PLAN.md` and `docs/README.md`
3. update docs to say explicitly that strategy social is not active scope

### Wave 3: navigation cleanup

1. demote/remove `Workspace` from top nav with safe `defaultHome` fallback
2. demote/shrink `Settings` without deleting the real settings contract
3. fix misleading `Attention` reminder wording

### Wave 4: noise cleanup

1. remove dead Dashboard styles
2. move strategy-social docs to clearer archive/rejected area

## I. One-line recommendation

If the goal is to stop carrying baggage, cut everything that is:

- not in the current PRD boundary
- not in the accepted milestone chain
- still able to change runtime/schema/release behavior today

That means the first things to cut are not docs.

The first things to cut are:

- strategy-social runtime fields and contracts
- all `Strategy` ORM read paths that still assume those fields
- misleading active navigation to non-mainline pages
