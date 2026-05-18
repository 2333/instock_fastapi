# W2b Data Completeness Alignment

> Status: completed
> Owner: controller + `worker-runtime`
> Depends: `W1`, `W2a`
> Last updated: 2026-04-22

> `2026-04-21` reviewer reopen 的 canonical BaoStock code regression 已关闭：
> `build_baostock_code()` 现在把带交易所信息的 `ts_code` 作为权威输入，task/backfill path 与 focused tests 已对齐。
> 当前 `W2b` 的 scheduler partial-gap detection 与 bounded explicit-window partial-gap backfill 两个子切片都已完成并通过双 review。
> `2026-04-22` 已按主线决策将 historical backfill 从 `Pre-M3` blocker 与 `fetch_daily_task` 日常任务模块中移出，因此本 wave 以 active-path baseline truthfully 关闭。
> `2026-04-22` reviewer reopen 的两个 follow-up finding（跨窗口状态过滤、BaoStock unsupported target selection）也已修复；复审结果为 `No findings`。
> `2026-04-22` release/schema lane 已在真实目标库补齐 `daily_bars` uniqueness contract；`fetch_daily_task.py` 中的 compatibility downgrade 已删除，active runtime 现以 upsert-only contract 运行。

## 目标

把 `2026-04-21` 生产日线完整度检查与 BaoStock 补数中暴露出的 market-data integrity 问题收口为一个 truthfully recorded lane，避免它们继续作为“脚本之外的隐性运维知识”存在。

当前要写实并收口的不是单一 bug，而是一组相互关联的 blind spots：

- scheduler / recovery 只能看 `MAX(trade_date)`，看不到 partial-gap 断更
- BaoStock source contract 的当前 narrowed slice 已统一；更宽的数据完整性 blind spot 仍待后续收口
- backfill 目标筛选只能修“整窗全缺”，修不了“窗口内部分交易日缺失”
- 测试与治理还没有覆盖这些故障模式

## Owned scope

- `daily_bars` partial-gap detection 的 failure mode 与 detection model
- BaoStock code canonical form、supported / unsupported universe policy、异常码 inventory
- partial-gap backfill 的目标定义、dry-run / execute 语义与审计留痕要求
- 数据完整性相关 fault-mode tests 与最小治理门槛

## Write set

- `app/jobs/tasks/fetch_daily_task.py`
- `tests/test_fetch_tasks.py`
- 本 artifact

## 当前执行重点

1. 保持 canonical BaoStock helper + taxonomy split 作为已完成 baseline，不再允许 `ts_code` 被冲突 `symbol/exchange` 覆盖。
2. 保持 `303` 个 BaoStock unsupported BJ universe 与 `22` 个 `no_source_but_db_present` anomaly 明确区分，不再混写。
3. 已完成的 scheduler 子切片：当日 `daily_bars` 已到目标 trade_date 但 BaoStock-supported active `SH/SZ/SSE/SZSE` 覆盖仍不完整时，仍触发 recover。
4. 当前切片已实现 bounded explicit-window partial-gap target selection，只接入 `run_daily_bars_backfill_window(...)`。
5. 当前切片保留现有 `backfill_daily_state`、`code_limit`、explicit source policy 与 no-fallback 约束；historical backfill 不再属于此 wave 的 active scope。

## Evidence captured on 2026-04-21

- Audit window: `2026-04-01` to `2026-04-21`, with BaoStock latest available trade date observed as `2026-04-20`.
- Production had `21985` April rows before repair and effectively stopped advancing after `2026-04-07`.
- BaoStock-supported stock universe in the window: `25949`.
- BaoStock unsupported universe in the window: `303` BJ codes.
- Stocks with BaoStock source rows in the window: `6658`.
- Missing rows repaired from BaoStock baseline: `65750`.
- Stocks with `no_source_but_db_present` anomalies: `22`.
- April rows after repair: `87735`.

Primary evidence files:

- `logs/baostock_completeness_april_20260421_dryrun.json`
- `logs/baostock_completeness_april_20260421_execute.json`

## Failure bundle

### 1. Scheduler / recovery blind spot

- Current recovery only checks whether each required table's `MAX(trade_date)` equals the target trade date. [app/jobs/scheduler.py](/Users/zhangkai/projects/instock_fastapi/app/jobs/scheduler.py:45)
- This cannot detect “same trade date exists, but only a subset of stocks was updated”.
- Current tests only cover “latest trade date is stale vs current”, not partial-gap coverage loss. [tests/test_scheduler.py](/Users/zhangkai/projects/instock_fastapi/tests/test_scheduler.py:47)

Current slice status:

- `done` for current-day `daily_bars` scheduler recovery: a coverage-based signal now complements `MAX(trade_date)` when `latest_trade_date == today`
- focused regression tests now cover incomplete coverage, full coverage, and mixed-format/legacy-code boundaries
- `done` for bounded explicit-window partial-gap backfill on `run_daily_bars_backfill_window(...)`
- historical backfill / progress semantics 已退出 `Pre-M3` active scope，不再构成当前 wave 的 blocker

### 2. BaoStock source-contract anomalies

- The April completeness script constructs exchange-qualified BaoStock codes such as `sz.000001` / `sh.600000`. [scripts/check_april_baostock_completeness.py](/Users/zhangkai/projects/instock_fastapi/scripts/check_april_baostock_completeness.py:47)
- The current task path and bounded backfill path now use the same canonical helper, so exchange-qualified BaoStock codes are no longer split across two rules. [app/jobs/tasks/fetch_daily_task.py](/Users/zhangkai/projects/instock_fastapi/app/jobs/tasks/fetch_daily_task.py:57)
- Existing focused tests now cover both explicit BaoStock-source calls and conflicting-input canonicalization, instead of codifying bare-symbol behavior. [tests/test_fetch_tasks.py](/Users/zhangkai/projects/instock_fastapi/tests/test_fetch_tasks.py:851)
- The `2026-04-21` execute report also showed:
  - `303` BaoStock unsupported BJ codes
  - `22` `no_source_but_db_present` anomalies such as `102268.SZ`

Required closure for this subsection:

- keep one canonical BaoStock code contract for all task paths
- keep `unsupported universe` and `contract anomaly` split
- create an explicit anomaly inventory / manual disposition note for the 22 codes

### 3. Partial-gap backfill limitation

- 历史问题是：旧的 bounded repair 只能识别整窗全缺，看不到“窗口内部分交易日缺失”的 partial-gap。
- 这会让类似“数据停在 `2026-04-07`，但后续交易日缺失”的问题无法通过标准 bounded repair 路径识别，必须依赖单独审计脚本人工发现。

Required closure for this subsection:

- define partial-gap target selection against a trustworthy baseline
- preserve dry-run / execute separation and idempotent writes
- ensure audit output distinguishes `missing`, `unsupported`, and `db-only anomaly`

### 4. Fault-mode verification gap

- Existing PRE-M3 focused tests cover release, strategy runtime, and representative API contracts, but not these market-data fault modes.
- Current suite does not yet prove:
  - production schema drift can be detected before runtime upsert downgrade
  - partial-gap stale data triggers recovery / alerting
  - BaoStock code contract stays canonical across task paths
  - unsupported/anomaly inventories stay distinct and reviewable

Required closure for this subsection:

- add dedicated fault-mode tests for scheduler, backfill target selection, and BaoStock contract handling
- record the required prod audit evidence and re-run commands in this artifact

## Historical audit commands

- `.venv/bin/python scripts/check_april_baostock_completeness.py --start-date 20260401 --end-date 20260421 --report-path logs/baostock_completeness_april_20260421_dryrun.json`
- `.venv/bin/python scripts/check_april_baostock_completeness.py --start-date 20260401 --end-date 20260421 --execute --report-path logs/baostock_completeness_april_20260421_execute.json`

## Results

- A new PRE-M3 lane is now required; the existing `W1/W2/W2a/W3/W4` structure did not truthfully own these failure modes.
- `fetch_daily_task.py` now exposes one canonical BaoStock code rule for task paths: only `SH/SZ` exchange-qualified codes (`sh.600000`, `sz.000001`) are passed into BaoStock calls; unsupported `BJ` remains outside the BaoStock-supported universe.
- The current narrowed W2b reopen additionally fixed the conflicting-input regression: dotted `ts_code` now wins over stale `symbol/exchange`, and the focused no-fallback BaoStock regression is isolated again.
- The April completeness audit script now reuses that same canonical code helper instead of maintaining a divergent local rule.
- The audit script taxonomy now keeps:
  - `unsupported_universe_*` for unsupported universe entries such as `BJ`
  - `contract_anomalies` for `no_source_but_db_present`
  - `details` for the remaining completeness statuses without duplicating contract anomalies
- `scheduler.py` now supplements `MAX(trade_date)` with a coverage-based partial-gap signal for `daily_bars`: when today's trade date is present but the supported active SH/SZ/SSE/SZSE universe is still not fully covered, `recover_missed_market_jobs()` will still rerun `fetch_daily_data`.
- The scheduler coverage query now normalizes mixed `YYYYMMDD` / `YYYY-MM-DD` `list_date` and `delist_date` values before comparison, so legacy migrated rows do not create false partial-gap signals.
- Focused W2b scheduler tests now cover:
  - latest trade date equals today but coverage is incomplete -> recover
  - coverage complete -> no recover
  - active-universe counting excludes `BJ` / ETF / future-listed rows
  - mixed-format listing/delisting dates, mixed-format covered `trade_date`, and legacy `SSE` / `SZSE` codes are still counted correctly
- `reviewer` 对当前 scheduler slice 给出 `no findings`，`code-review-expert` 复核也未发现新的 blocking issue。
- `fetch_daily_task.py` 的 bounded backfill path 现在能识别 explicit-window partial-gap 与 full-gap target，并保持 full-coverage 不入选。
- bounded partial-gap selector 现在使用真实交易日历而不是工作日近似；交易日历为空时会显式失败，不再伪装成“没有目标”。
- execute path 现在按窗口闭合度而不是 `saved > 0` 决定 `partial/done`，窗口未闭合不会被提前写成 terminal `done`。
- bounded explicit-window repair 现在按窗口上下文过滤 `backfill_daily_state`，不会再被同一 `ts_code` 的其他窗口历史状态误伤。
- 当 `source="baostock"` 时，selector 会在 target selection 阶段直接排除 `BJ` / ETF 这类 BaoStock 明知不支持的标的，不再把 unsupported universe 混写成 active-path `nodata`。
- Focused W2b backfill tests now cover:
  - partial-gap target selection alongside full-gap/full-coverage discrimination
  - dry-run 不创建 `backfill_daily_state`
  - non-trading-day exclusion from expected-days
  - mixed-format `daily_bars.trade_date`
  - mixed-format `list_date/delist_date` filter normalization
  - empty trading calendar 显式失败
  - execute path 在窗口未闭合时保持 `partial` 并允许后续 rerun
- `reviewer` 对当前 bounded backfill slice 给出 `no findings`，`code-review-expert` 复核也未发现新的 blocking issue。
- `fetch_daily_task.py` 中的 `run_historical_backfill()` 及其专属 helper 已删除，硬编码 `2020-2025` 入口脚本也已退役；历史补数未来若需要，改走外部临时能力。
- `save_daily_bars(...)` 与 `save_daily_bars_batch(...)` 现已移除 runtime compatibility downgrade：当 `uq_daily_bars_ts_code_trade_date_dt` 不存在时会显式 rollback + raise，而不是静默降级到逐行兼容写入。
- focused regressions 已补齐：
  - 缺失 `uq_daily_bars_ts_code_trade_date_dt` 时，单条写入会显式失败
  - 缺失 `uq_daily_bars_ts_code_trade_date_dt` 时，batch 写入会显式失败
- `2026-04-22` 真实目标库已补齐 `uq_daily_bars_ts_code_trade_date_dt` 与 `ix_daily_bars_trade_date_dt`，因此 `W2b` 的 active runtime baseline 与 live schema contract 已重新对齐。

## Changed files

- `app/jobs/tasks/fetch_daily_task.py`
- `scripts/backfill_2020_2025.py`（deleted）
- `tests/test_fetch_tasks.py`
- `scripts/pre_m3_schema_onboarding_20260422.sql`
- 本 artifact

## Commands run

- `.venv/bin/python -m pytest tests/test_scheduler.py -q`
- `.venv/bin/python -m pytest tests/test_api.py -k 'task_health or should_recover_market_job' -q`
- `uv run --python 3.12 pytest -q tests/test_fetch_tasks.py::test_fetch_daily_bars_uses_explicit_baostock_source tests/test_fetch_tasks.py::test_fetch_daily_bars_does_not_fallback_when_baostock_returns_empty tests/test_fetch_tasks.py::test_daily_bars_backfill_window_uses_explicit_baostock_source tests/test_fetch_tasks.py::test_daily_bars_backfill_window_does_not_fallback_from_baostock tests/test_fetch_tasks.py::test_build_baostock_code_uses_exchange_qualified_sh_sz_and_rejects_bj tests/test_fetch_tasks.py::test_build_baostock_code_prefers_canonical_ts_code_over_conflicting_fields`
- `.venv/bin/python -m pytest tests/test_fetch_tasks.py -q`
- `.venv/bin/python -m pytest tests/test_scheduler.py -q`
- `uv run pytest -q tests/test_fetch_tasks.py`
- `rg -n "run_historical_backfill|backfill_2020_2025|BACKFILL_START_DATE|BACKFILL_END_DATE|BACKFILL_BATCH_SIZE|BACKFILL_ITEM_SLEEP|_get_backfill_progress\(|_get_backfill_targets\(" app scripts tests docs`
- `./.venv/bin/python -m pytest tests/test_fetch_tasks.py -k 'compatibility_downgrade' -q`

## Open risks

- `backfill_daily_state` 仍然只按 `ts_code` 记账，不带 window/source 维度；这不是当前 active-path 子切片新引入的问题，但如果未来要做外部历史补数能力，需要重新设计状态模型。

## Next step

- Preserve the current scheduler partial-gap detection implementation as the approved W2b baseline.
- Preserve the current bounded explicit-window partial-gap backfill implementation as the approved W2b baseline.
- Enter `W4` and summarize W2b as closed on active-path scope; if historical backfill is needed later, reopen it as an external temporary capability rather than a daily-task follow-up.

## Blocked by

- none

## Recovery note

- If this lane is resumed later, read the latest execute report first, then confirm the numbers still match the production truth before updating implementation or tests.
- Do not treat `W4` as the place to plan these fixes; `W4` should only summarize `W2b` after this artifact has real closure evidence.

## Handoff needed

- none currently
