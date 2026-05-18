# W2 Runtime-Schema Alignment

> Status: completed
> Owner: `worker-runtime`
> Depends: `W0`
> Last updated: 2026-04-20

## 目标

清理 active runtime 中不属于当前 `PRD` 主线的 `Strategy` residue，并覆盖所有 ORM 读路径与 focused tests。

## Owned scope

- `Strategy` ORM / schema / router / task 的主线收口
- 所有会 materialize `Strategy` 的 ORM read paths
- focused strategy tests

## Write set

- `app/models/stock_model.py`
- `app/schemas/strategy_schema.py`
- `app/api/routers/strategy_router.py`
- `app/jobs/tasks/strategy_task.py`
- dedicated strategy-focused tests
- 本 artifact

## Do not edit in `W2`

- `docs/deployment/release_workflow.md`
- `scripts/deploy_release.sh`
- `scripts/build_release_images.sh`
- `scripts/migration_live_validation.py`
- `Makefile` 的 release / smoke / precheck targets
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/`，除非 controller 明确解除 shared-file freeze
- `tests/conftest.py`，除非 controller 先记录 handoff

## Closure dependency

- `W2` 可以先做 runtime residue 清理与 focused tests，但整体 closure 仍依赖 `W1` 先冻结 release gate。

## Next actions

1. 盘点所有 `select(Strategy)`、`StrategyResponse` 序列化与后台任务读取路径。
2. 在不增加 fallback 字段、不过度兼容旧 schema 的前提下，把 model / schema 收口到当前主线契约。
3. 把 API 读路径和后台任务一起改，避免只修接口不修异步任务。
4. 在 owned write set 内补 focused tests，证明 leaked social/public-library fields 不再参与 active runtime contract。

## Interruption-safe recovery

1. 先读 `PRE_M3_DECISION.md` 和 tracker，确认 `worker-runtime` 仍是当前 owner，且 `W1` gate 约束没有变化。
2. 回到本 artifact 的 `Next actions` / `Blocked by` / `Recovery note`，从最后一次成功的 runtime file 继续。
3. 如果下一步需要 release/deploy 文件或 migration head 变更，先停止并记录 handoff。
4. 停手前更新 `Changed files`、`Commands run`、`Results`、`Open risks`、`Next step`、`Blocked by`、`Recovery note`。

## Handoff triggers

- 发现 release restriction 无法仅靠 W1 lane 解决，必须动 release/deploy gate。
- 发现修复需要新增或改写 migration revision。
- 发现必须进入 `tests/conftest.py` 或其他 shared fixture 才能完成 focused tests。

## 必查范围

- `app/models/stock_model.py`
- `app/schemas/strategy_schema.py`
- `app/api/routers/strategy_router.py`
- `app/jobs/tasks/strategy_task.py`

## 当前恢复说明

- 当前 lane 的第一批 runtime/schema 修复与 focused tests 已完成，正在等待 reviewer gate。
- 如果此时中断，下一位接手者应先看 reviewer findings；若没有新增 findings，可直接以本 artifact 为基础准备 `W3`。

## Changed files

- `app/models/stock_model.py`
- `app/schemas/strategy_schema.py`
- `app/api/routers/strategy_router.py`
- `app/jobs/tasks/strategy_task.py`
- `tests/test_strategy_runtime_schema_alignment.py`
- `tests/test_router_endpoints.py`

## Commands run

- `.venv/bin/pytest tests/test_strategy_runtime_schema_alignment.py -q`
- `.venv/bin/pytest tests/test_router_endpoints.py -q -k strategy`
- `.venv/bin/pytest tests/test_strategy_runtime_schema_alignment.py tests/test_strategy_selection_bridge.py tests/test_router_endpoints.py -q`
- `.venv/bin/python -m pytest tests/test_release_precheck.py tests/test_strategy_runtime_schema_alignment.py tests/test_router_endpoints.py -q`

## Results

- `Strategy` ORM model 已移除不属于当前主线的社交 / 公共策略库残留字段。
- `StrategyResponse` 已同步收口到当前 active contract。
- `/strategies/my` 等 ORM 读取路径已改为核心字段 `load_only(...)` 读取，不再 materialize 已删除 residue。
- `strategy_task` 已切到核心字段读取，并移除了“没有策略时自动造一个默认策略”的 runtime bootstrap。
- update 路径新增了重复名称预检查；同一用户将策略改名为已存在名称时，返回受控 `400`，不再把唯一约束错误冒泡成 `500`。
- delete 路径现在会先删除该策略的 `strategy_results` 子记录，并把 `backtest_results.strategy_id` 置空后再删除策略；已执行过的策略不再因为历史结果 FK 约束导致 `500`。
- focused suite 结果：`21 passed, 1 warning`。
- cross-lane focused regression 结果：`23 passed, 2 warnings`。

## Open risks

- 这是 focused strategy slice 验证，不是全仓回归；主线其余接口未在本 lane 中复验。
- 这是应用层预检查 + 子表显式删除，不是 DB 级 cascade；在高并发重命名竞争下，唯一约束最终仍由数据库兜底。
- 删除策略会同时硬删其历史 `strategy_results`；这符合当前个人工具主线，但如果后面要保留历史结果，需要另做产品决策。
- 若仓库里还有本次 write set 之外的 `Strategy` ORM read path，它们不在这轮改动范围内。

## Next step

- `W2` 已通过 reviewer gate，可作为 `W3` residue cleanup 的 runtime baseline。
- 后续若还有 `Strategy` 相关变更，必须基于当前最小 contract 继续，而不是重新引回已退役 residue。

## Blocked by

- none currently

## Recovery note

- reviewer 已给出 `GO`，当前 runtime/schema baseline 已冻结。
- 若从这里恢复，先读 tracker/decision 确认后续 work 是否已经进入 `W3` 或 `W4`。

## Handoff needed

- none currently

## Required records

- Changed files
- Commands run
- Results
- Open risks
- Next step
- Blocked by
- Recovery note
- Handoff needed
