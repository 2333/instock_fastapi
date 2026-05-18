# Project Mainline Audit

> 分析/审计文档，不是当前主线推进入口。
> 当前状态、下一步和执行顺序请先看 `docs/EXECUTION_PLAN.md`。
> 本文记录的是 `2026-04-20` 的审计快照；如果与当前 `Pre-M3` 执行包冲突，以当前 route docs 为准。

> Date: 2026-04-20
> Scope: plan-of-record, milestone execution, runtime alignment, release-path drift

## 1. Source-of-truth order

When documents conflict, use this order:

1. `docs/PRD.md`
2. `docs/ROADMAP.md`
3. `docs/EXECUTION_PLAN.md`
4. active execution pack under `docs/milestones/m3/`
5. historical execution packs under `docs/milestones/m0/`, `m1/`, `m2/`
6. runtime code and deploy scripts
7. `docs/milestones/phase3/` and `phase4/` as design/archive assets only

Reason:

- `PRD` defines product identity and hard boundaries.
- `ROADMAP` defines phase intent.
- `EXECUTION_PLAN` is the active milestone-level source of truth.
- the active `Pre-M3` pack is the current execution-level source of truth.
- `phase3/` and `phase4/` explicitly state that they are not automatic go-signals for the current mainline.

## 2. Mainline flow

```text
PRD / ROADMAP
  ->
M0 boundary definition
  ->
M0 baseline freeze attempt
  ->
M0 rebaseline governance cleanup
  ->
M1 data-layer restart
  ->
M1 current-stage acceptance
  ->
M2 user-event kickoff and acceptance
  ->
Pre-M3 mainline alignment
  ->
M3 alerting
  ->
M5 parameter optimization
  ->
M6 data insights
  ->
M7 recommendation
```

Retired path:

```text
P3-04 strategy social
  -> historical rejected design only
```

Important branch in reality:

```text
M0 baseline freeze attempt
  -> merged content exceeded M0 boundary
  -> triggered M0 rebaseline
  -> mainline cleaned
  -> M1 restarted from cleaned baseline
```

## 3. Wide table

| Layer | Planned role | Planned state | Actual evidence | Mainline judgment | Drift / notes |
|------|--------------|---------------|-----------------|------------------|---------------|
| `PRD v2.0` | Product identity | Focus on `扫描 -> 筛选 -> 验证`; no community/social product | `PRD` says InStock is not a community platform and `社区 / 评论 / 排行榜` are never-do items | `active` | This is the hard boundary for all later milestones |
| `ROADMAP v2.0` | Phase intent | `Phase 0a -> 0b -> 1`, future phases only directional | `ROADMAP` keeps future planning lightweight and warns against over-planning | `active` | `ROADMAP` is high-level; milestone execution moved into `EXECUTION_PLAN` |
| `M0 boundary` | Define what belongs to baseline | Keep Phase 0/1 core; Phase 2/3 and M1 delayed | `M0_PR_BOUNDARY` says Phase 2/3 must be stripped from the M0 merge package | `historical but binding for rebaseline` | This is the document that explains why rebaseline became necessary |
| `M0 freeze` | Baseline merge | Freeze Phase 0/1 and stop using long branch as main carrier | `EXECUTION_PLAN` records M0 quick-suite, frontend build, dashboard smoke, then notes merged scope exceeded M0 boundary | `completed, then invalidated by scope drift` | The first freeze landed with too much extra scope |
| `M0 rebaseline` | Governance recovery | Bring `main` back to a true M0 state | `REBASELINE_M0_PLAN` and `TRACKER` show R0-R4 cleanup waves; `RB4-04` says runtime/docs were cleaned and staged for merge | `completed as governance background` | Rebaseline succeeded, but some runtime residue still survived into later code paths |
| `M1 restart plan` | Data-layer foundation | Alembic existing-schema path, Timescale, bounded data rehearsals | `M1_RESTART_PLAN` narrows scope to token-independent acceptance | `active historical milestone` | M1 explicitly accepts a non-empty-schema Alembic start, not a full empty-db baseline |
| `M1 current-stage acceptance` | Mark M1 done enough to unblock M2 | Accept token-independent scope, defer token-gated items | `W6-review` says `go for current-stage M1 acceptance`; `daily_basic` / `stock_st` remain gated follow-up | `completed with gated backlog` | Production DB was not part of this acceptance; only disposable DB validation was accepted |
| `M1 follow-up backlog` | Finish token-gated work later | `daily_basic`, `stock_st`, related screening integration | `EXECUTION_PLAN` and `M1_RESTART_PLAN` both keep these as non-blocking follow-up | `open backlog` | Correctly documented as non-blocking for M2 |
| `M2 kickoff plan` | First-wave event tracking | schema + API + frontend integration + reviewer gate | `M2_KICKOFF_PLAN` is marked `acceptance ready` | `active milestone pack` | This pack is internally consistent |
| `M2 acceptance` | Close first-wave tracking | live migration validation, focused tests, 5 pages, 6 events | `M2_ACCEPTANCE` is marked `go`; reviewer says `GO for M2 acceptance` | `completed` | At audit time, route docs had not yet been updated to reflect this acceptance |
| `EXECUTION_PLAN current-state line` | Mainline navigation | Should tell the current real position | at audit time it still said current route was `M2 / P3-01 kickoff 前` | `historically stale` | Later closed by `Pre-M3` doc-alignment work |
| `Phase 3 design docs` | Preserve future designs | design only, not auto-active | `phase3/README` explicitly says these docs do not mean current mainline should start them | `archive/design` | Several ideas from here leaked into runtime code |
| `Phase 4 docs` | Far-future planning | reference only | `phase4/README` says Phase 4 is not part of current decisions | `archive/design` | Should not drive implementation now |
| `Release workflow` | Safe version bump and prod deploy | merge-check -> bump -> build -> deploy -> smoke | `release_workflow.md` documents this; `Makefile:merge-check` validates CI + compose; deploy script recreates containers | `active but incomplete` | Missing hard gates for migration/stamp/schema compatibility |
| `Runtime strategy model` | Strategy persistence for personal tool | Should only carry personal-tool strategy fields unless M4 is explicitly active | `app/models/stock_model.py` still includes `is_public`, ratings, favorite/comment/view counts, `suitable_market` | `off-mainline residue` | This violates current PRD boundary and caused production schema mismatch |
| `Runtime strategy schema` | API contract | Should match active product scope | `app/schemas/strategy_schema.py` still exposes social fields in `StrategyResponse` | `off-mainline residue` | Another Phase 3 leak into active runtime |
| `Runtime strategy query path` | Load user strategies | Should query only columns that exist in active schema | `/strategies/my` does `select(Strategy)` | `buggy under current prod DB` | ORM auto-selects leaked social columns and triggers 500 on old schema |
| `Alembic revisions` | Schema-change source of truth | Every active data-contract change should have a migration | only M1 core, M1 required facts, stock metadata, and M2 user events revisions exist | `partially aligned` | There is no migration in repo for strategy-social columns, which confirms they were never legit mainline schema work |

## 4. Timeline of how the project actually moved

### A. Product and execution anchor

- `PRD` fixed the product as a personal A-share research tool and explicitly excluded community/social directions.
- `ROADMAP` translated that into `Phase 0a -> 0b -> 1` and kept later phases directional.
- `EXECUTION_PLAN` later converted that into milestone execution: `M0 -> M1 -> M2 -> M7`.

### B. M0 first pass

- Phase 0/1 baseline work was gathered and validated.
- Dashboard, Selection, Backtest, Attention, and stock-detail chains were smoke-tested.
- But the initial merge package carried extra Phase 2 / Phase 3 / M1 assets beyond the approved M0 boundary.

### C. M0 rebaseline

- Rebaseline was launched because merged scope exceeded the agreed M0 boundary.
- Governance work moved in waves:
  - `R0` snapshot
  - `R1` keep/remove/hold matrix
  - `R2` runtime closure
  - `R3` code cleanup
  - `R4` regression and document finalization
- This restored the mainline conceptually, but not every historical residue was purged from later code.

### D. M1 restart

- M1 restarted from the cleaned baseline.
- Scope was narrowed intentionally:
  - accept Alembic existing-schema path
  - accept token-independent `daily_bars` and local `technical_factors`
  - defer `daily_basic` and `stock_st`
- Reviewer signed off current-stage M1 acceptance, with token-dependent items explicitly gated.

### E. M2 execution

- M2 defined a strict first-wave event-tracking pack:
  - event whitelist
  - `user_events` migration
  - `/events/track`
  - 5 pages
  - 6 events
  - reviewer gate
- M2 acceptance artifacts show the milestone itself is complete and reviewer-approved.

### F. Production release reality

- Production release workflow bumped version and recreated containers.
- But the deploy path did not run or verify DB migrations.
- Production DB is not under Alembic control, so code version, migration version, and actual schema state were not locked together.
- This exposed two separate mismatches:
  - `user_events` M2 schema not applied in production
  - `strategies` social fields expected by runtime code but absent in production DB

## 5. Where the project is right now

There are two different “current positions”, and they must be separated:

### A. Product / milestone position

Current intended mainline position is:

`M2 accepted -> Pre-M3 alignment -> reviewer go -> M3`

Reason:

- `M1` current stage is accepted.
- `M2` acceptance artifact is `go`.
- Phase 3 / Phase 4 docs are not active by default.

### B. Engineering / runtime position

Current engineering reality is:

`M2 accepted in milestone artifacts, but production release path is not clean enough to safely move on to M3`

Reason:

1. release flow does not enforce DB migration/stamp/schema gates
2. production DB is not Alembic-managed
3. active runtime still contains off-mainline Phase 3 strategy-social residue
4. at audit time, the route docs had not yet been fully realigned to the `Pre-M3` execution package

## 6. Confirmed drift items

### Drift 1: execution status drift

- At the time of this audit, `EXECUTION_PLAN` still said the project was at `M2 kickoff 前`
- while `M2_KICKOFF_PLAN` was already `acceptance ready`
- and `M2_ACCEPTANCE` was already `go`

Impact:

- anyone reading only `EXECUTION_PLAN` at that point would believe M2 had not been executed yet

Status:

- closed later by `Pre-M3` doc-alignment work; kept here as historical audit evidence

### Drift 2: product-boundary drift

- current `PRD` forbids community/social scope
- but active runtime `Strategy` model and `StrategyResponse` still contain social fields

Impact:

- product scope is no longer faithfully represented by active runtime code
- these fields also create schema expectations that production DB does not satisfy

### Drift 3: release-process drift

- release docs and scripts handle image build/deploy
- but do not hard-gate schema migration/stamp/compatibility

Impact:

- code release can outpace DB reality
- exactly what happened in production during `0.3.0`

### Drift 4: Alembic-boundary drift

- M1 explicitly accepted an existing-schema Alembic path
- but production DB was never fully brought under that contract

Impact:

- disposable-db validation passed
- production still had no shared revision truth

## 7. Recommended next-plan sequence

This was the recommended next-plan sequence at audit time. For the current live route, always defer to `docs/EXECUTION_PLAN.md` and the active `Pre-M3` pack.

### Step 1. Recover release correctness before starting M3

Do not move into M3 while production is in schema-drift state.

Required actions:

1. stop the current production 500 path
2. align production DB under a controlled migration/stamp strategy
3. prove prod schema compatibility before next feature release

### Step 2. Clean mainline residue

Remove or isolate off-mainline strategy-social residue from active runtime:

1. `Strategy` ORM social fields
2. `StrategyResponse` social fields
3. any query path that assumes M4 social schema before M4 is explicitly active

This is required to bring runtime back in line with the current PRD.

### Step 3. Fix governance docs

Update mainline navigation docs so one person reading the repo can answer “where are we now?” without inference:

1. `EXECUTION_PLAN` current-state line should move from `M2 kickoff 前` to `M2 accepted`
2. next-active milestone should be marked as `M3`, but blocked on release-path cleanup
3. explicitly record that `M4` strategy-social is not active runtime scope yet

### Step 4. Harden release workflow

Release workflow needs three new hard gates:

1. deploy-precheck: active models with schema changes must have matching Alembic revisions
2. prod-predeploy: database must be stamped/upgraded to target revision
3. prod-postdeploy: schema compatibility smoke must run before release is accepted

### Step 5. Start M3 only after the above are green

Once release correctness and runtime boundary are repaired, the next mainline milestone is:

`M3 / P3-03 预警规则与通知`

Not:

- `M4` strategy social
- `Phase 4`
- ad-hoc continuation of historical Phase 3 draft work

## 8. Bottom-line conclusion

The project does have a valid mainline, and it is not directionless.

The real chain is:

`PRD / ROADMAP -> M0 boundary -> M0 rebaseline -> M1 current-stage acceptance -> M2 acceptance -> next should be M3`

The current problem is not “no plan”.

The current problem is:

1. some historical Phase 3 ideas leaked back into active runtime
2. release engineering did not keep code/schema/prod state locked together
3. mainline status docs were not updated after M2 acceptance

So the right move is not to invent a new roadmap.

The right move is:

`repair mainline alignment -> restore release correctness -> then continue from M3`
