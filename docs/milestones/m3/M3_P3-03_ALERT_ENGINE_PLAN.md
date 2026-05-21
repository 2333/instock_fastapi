# M3 P3-03 参数化指标筛选与订阅提醒 Plan

> Status: closed baseline
> Last updated: 2026-04-24
> Owner: controller
> Source of truth: [docs/EXECUTION_PLAN.md](../../EXECUTION_PLAN.md)

> Historical slice: `M3 / P3-03 accepted and post-merge staging closed`

## 目标

以 `Pre-M3` 已通过的 release/runtime/doc baseline 为起点，交付一个面向普通用户的、可参数化的指标筛选与提醒闭环：

- 用户可以基于模板调整 `MACD`、`RSI`、`BOLL` 等指标参数
- 用户可以保存筛选器并在全市场手动运行
- 用户可以把已保存筛选器订阅为盘后提醒
- 系统以应用内通知返回新增命中结果

当前默认执行后端可以是 `SQL + TA-Lib`；未来允许切换到 `vbtpro` 或其他执行引擎，但不能改变用户保存的 authored definition。

## Source-of-truth 顺序

文档冲突时按以下顺序裁决：

1. `docs/PRD.md`
2. `docs/ROADMAP.md`
3. `docs/EXECUTION_PLAN.md`
4. 本计划
5. `docs/milestones/phase3/PHASE3_P3-03_ALERT_ENGINE.md`
6. `docs/milestones/phase3/PHASE3_P3-03_ALERT_ENGINE_IMPLEMENTATION.md`

## Canonical Model

M3 的主模型固定为以下四层，任何设计或实现都不得越界：

1. `Saved Screener`
   - 唯一 canonical truth source
   - 保存用户筛选意图、模板、参数、有限结构化条件和作用域
   - 所有“已保存筛选器 / 预警定义 / 模板复用”最终都锚定到这里
2. `Alert Subscription`
   - 只负责引用 `saved_screener_id + saved_screener_version`
   - 管理启停、频率、冷却、通知渠道和去重
   - 不得复制筛选 clauses，不得成为第二套 authored rule persistence
3. `Registry`
   - 唯一允许定义字段、参数、操作符、展示文案、默认值和 adapter 支持矩阵的地方
   - API metadata、前端表单、校验器和 adapter compile 行为都从它派生
4. `Adapter`
   - 只做 compile / execute
   - 当前默认 adapter 可基于 `SQL + TA-Lib`
   - 未来可增加 `vbtpro` adapter
   - 持久化层禁止出现 TA-Lib 名称、SQL 片段、vbtpro 表达式、Python lambda、用户自定义公式字符串

## 防漂移硬边界

- `Saved Screener` 是唯一 authored object；不得再新增第二套规则持久化真相源。
- `Alert Subscription` 不得复制筛选定义，只能绑定 `Saved Screener` 的不可变版本。
- `Registry` 必须是唯一字段目录；新增字段、参数或操作符时，同步更新 registry、公开 API contract、兼容说明和测试矩阵。
- 所有 persisted object 都必须带版本字段；至少包括 `schema_version`，并保留 authored snapshot / execution snapshot。
- M3 支持“用户自定义参数集”，不支持“用户自定义公式语言”。
- 逻辑能力先收敛到有限结构：只允许受控 clause 数量与有限 `ALL / ANY` 组合，不开放无限嵌套和脚本表达式。
- 切换执行引擎到 `vbtpro` 只能修改 adapter 与 capability matrix，不得要求重写 `Saved Screener` schema。

## Superseded / Legacy Models

以下模型或表述不再是 M3 目标，只能作为兼容或迁移输入：

- `alert_conditions(rule_type + threshold)`：`legacy baseline / superseded prototype`
- richer row model（`condition_type / operator / threshold / pattern_name / notify_channels`）：`prototype exploration`
- 单一 JSONB `condition` 持久化模型：`discarded prototype`
- `attention.alert_conditions`：`legacy residue / compatibility only`，不作为 truth source，不 dual-write
- `selection_conditions.params` 的 free-form `dict`：`legacy wrapper`，兼容期可保留，但长期 authored schema 应迁移到显式 canonical envelope
- `m3_alert_engine_baseline` migration：`legacy onboarding baseline only`，用于兼容已有 prototype 表，不代表 `M3-B` 应继续沿用 `alert_conditions(rule_type + threshold)` 作为主模型

## 当前交付分步

### `M3-A` 参数化筛选基线

目标：

- 在 `Selection` 路径上建立参数化筛选主模型
- 首批支持 `MACD`、`RSI`、`BOLL`
- 支持普通用户模板化使用，高级模式支持参数微调

In Scope：

- `Saved Screener` canonical envelope
- `Registry` 与 metadata API
- `Selection` 手动运行与结果预览
- 默认 `SQL + TA-Lib` adapter
- `schema_version` / `definition_version` / `definition_hash`
- 保持现有 selection 保存/运行链路可兼容

Out Of Scope：

- 用户自定义公式语言
- 邮件通知
- 通知铃铛
- 5 分钟实时轮询
- Attention 快速设置
- dual-write `attention.alert_conditions`

当前状态：

- `S1` canonical envelope: completed
- `S2` versioned persistence: completed
- `S3` parameterized backend runtime (`RSI / MACD / BOLL`, `SQL + TA-Lib`): completed
- `S4` minimal Selection wiring + manual smoke: completed

已完成交付：

- `selection_conditions.params` 现在承载 canonical `Saved Screener`
- `schema_version / definition_version / definition_hash` 已进入后端持久化/读取 contract；当前前端保存请求继续显式提交 `definition + compat params`
- `/screening/metadata` 已成为 registry-backed contract
- `/selection`、`/screening/run`、`/selection/today-summary` 已可消费 canonical `definition`
- 默认参数继续兼容旧 contract；非默认参数已通过 backend runtime 生效
- Selection 页已接入 metadata 驱动的最小参数输入：`RSI period`、`MACD fast/slow/signal`、`BOLL period/stddev`
- Selection 页保存与运行已统一提交 `definition + compat filters`，saved condition 加载优先使用 canonical `definition`
- live smoke 已验证 `metadata -> save -> list -> today-summary -> run` 闭环
- schema lane 已补齐为单一 head，`alembic upgrade head` 在当前分支本地环境通过

`S4` stop condition：

- Selection 页能读取 registry metadata 并暴露最小参数输入
- 用户能创建至少 1 个带非默认参数的筛选器并手动运行
- `GET /selection/my-conditions` / `POST /screening/run` / 页面手工 smoke 三者口径一致
- reviewer + review-expert 通过后，才允许进入 `M3-B`

### `M3-B` 订阅提醒闭环

目标：

- 把 `Saved Screener` 订阅为盘后提醒
- 以“新增命中摘要”而不是噪声型逐条推送为默认形态

In Scope：

- `Alert Subscription`
- 盘后 scheduler / checker
- `Run / Hit / Notification`
- dedupe / cooldown
- 手工 smoke：保存筛选器 -> 手动运行 -> 创建订阅 -> 触发通知

当前下一步：

- `S1` backend subscription baseline: completed
- `S2` minimal Selection subscription entry: completed
- `S3` post-close scheduler/checker: completed
- `S4` M3-B acceptance smoke + review closure: completed
- Current gate: `M3` acceptance candidate; `M3-C` is post-acceptance entry polish unless explicitly re-scoped

`S1` 已完成交付：

- 新增 `alert_subscriptions / alert_runs / alert_run_hits`
- `Alert Subscription` 只 pin `selection_condition_id + definition_version + definition_hash`，不复制 screener clauses
- `notifications` 扩展 `subscription_id / alert_run_id / notification_type / dedupe_key`，新写路径不依赖 legacy `alert_conditions`
- 手动触发已复用现有 `SelectionService` runtime，并持久化 run/hit/summary notification
- 同一订阅、同一交易日、同一 definition hash 的重复触发会复用已有 run
- 跨日新增命中按上一条更早 trade_date run 比较；`cooldown_trade_days` 会抑制摘要通知但保留 run/hit
- 筛选器编辑、停用或删除会把对应订阅标记为 `stale`
- 验证：focused backend suite `52 passed, 1 warning`；`npm --prefix web run build` 通过；Alembic 当前 head 为 `m3_alert_subscription_baseline`

`S2` 目标：

- 在 `Selection` 已保存筛选器列表中提供最小订阅入口
- 用户可创建订阅、手动触发一次订阅、查看本次 run 摘要与站内通知摘要
- 不引入铃铛、邮件、Attention 快捷设置或实时轮询

`S2` 已完成交付：

- `web/src/api/index.ts` 新增 `alertSubscriptionApi`
- `Selection` 已保存条件列表新增 `订阅 / 已订阅 / 触发` 最小入口
- 触发后展示本次 run 的交易日、总命中数与新增命中数
- 验证：`npm --prefix web run build` 通过

`S3` 已完成交付：

- 新增 `app.jobs.tasks.alert_subscription_task`
- scheduler 注册 `run_post_close_alerts`，盘后 `20:25`、`mon-fri`、`max_instances=1`
- checker 只加载 `active + post_close` 且目标交易日缺 run 的订阅，逐个复用 `AlertSubscriptionService.run_subscription`
- 目标交易日没有 `daily_bars` 或 active universe 存在 partial gap 时直接跳过，避免 `SelectionService` 的交互式日期回退或不完整数据导致误报
- 非交易日沿用 `should_skip_market_task`，保留统一强制运行开关
- 筛选器失效时会持久化订阅 `stale` 状态，批量任务继续处理其他订阅
- 应用启动后的 missed-run checker 在 market recovery 之后运行；只在已过 `20:25` 且 latest trade date 仍有缺失 run 时补跑一次，不做历史窗口扫描
- 订阅创建遇到唯一键竞争时返回稳定业务错误；订阅运行在写入前二次校验筛选器版本，避免过期 definition 生成 run/notification
- 验证：`tests/test_alert_subscription_runtime.py tests/test_scheduler.py tests/test_alert_schema_contract.py tests/test_router_endpoints.py` 通过，`46 passed`

`S4` stop condition：

- 端到端 smoke 覆盖：保存筛选器 -> 创建订阅 -> 手动触发 -> scheduler/checker -> notification
- reviewer 对 S1-S3 给出 no blocking findings
- `code-review-expert` 复核无 P0/P1
- 文档入口仍收敛在 `EXECUTION_PLAN.md` + 本文 + `m3/README.md`，不新开路线文档

`S4` 已完成交付：

- reviewer 复审结论：`APPROVE`，无新的 `P0/P1` blocking findings
- 关闭的 blocking：订阅不复制 screener definition、partial-gap readiness 防误跑、并发/事务空窗补强、startup recovery 先 market 后 alert
- 验证：`tests/test_alert_subscription_runtime.py tests/test_scheduler.py tests/test_alert_schema_contract.py tests/test_router_endpoints.py tests/test_selection_schema.py tests/test_screener_adapter.py tests/test_screener_runtime.py tests/test_selection_today_summary.py` 通过，`73 passed`
- 验证：`npm --prefix web run build` 通过
- 验证：`alembic heads && alembic current` 均为 `m3_alert_subscription_baseline (head)`

说明：以上为 `2026-04-24` S4 closure 记录。`2026-05-18` reviewer reopen 后发现并修复了两项 P1，当前准入判断以本节后续的 `2026-05-18` 验收与 PR 收口检查为准。

`2026-04-24` technical smoke：

- schema gate：`alembic heads && alembic current` 均为 `m3_alert_subscription_baseline (head)`
- focused regression：M3 focused suite `73 passed`
- frontend build：`npm --prefix web run build` 通过；保留既有 Sass deprecation / chunk size warnings
- isolated API smoke：`/health`、`/screening/metadata`、parameterized `/screening/run`、saved screener create、subscription create、manual run、notification list、duplicate same-day run dedupe、scheduler batch no-duplicate、stale after screener update 全部通过
- isolated API smoke 落库结果：`alert_runs=1`、`alert_run_hits=2`、`notifications=1`；同日重复 run 与 batch 后仍保持不重复
- configured DB read-only scheduler check：latest trade date 为 `20260420`，当前 `alert_subscriptions=0`、`alert_runs=0`、`notifications=0`
- configured DB readiness：`daily_bars` active universe coverage 为 `5199/5522`，存在 partial gap，因此真实 scheduler 会按设计 `skip`，不会生成误报通知

`2026-05-18` 验收与 PR 收口检查：

- 当前结论：`M3` 保持最小验收候选；`2026-05-18` reviewer reopen 的 P1 已修复并通过 focused regression、release gate、merge gate 与最终 reviewer 复审；进入 PR 前仅剩远端 PR 状态确认与提交。
- 本地代码卫生：`git diff --check` 通过。
- schema head：`./.venv/bin/alembic heads` 返回单一 head `m3_alert_subscription_baseline (head)`。
- M3 focused regression：`tests/test_alert_subscription_runtime.py tests/test_scheduler.py tests/test_alert_schema_contract.py tests/test_router_endpoints.py tests/test_selection_schema.py tests/test_screener_adapter.py tests/test_screener_runtime.py tests/test_selection_today_summary.py -q` 通过，`73 passed, 1 warning`。
- 全量后端回归：`./.venv/bin/pytest -q` 通过，`291 passed, 1 skipped, 2 warnings`。
- 前端构建：`npm --prefix web run build` 通过；保留既有 Sass deprecation warnings 与 charts vendor chunk size warning。
- P1 修复回归：`tests/test_alert_subscription_runtime.py tests/test_scheduler.py tests/services/test_selection_service_provider.py tests/test_selection_market_services.py tests/test_router_endpoints.py tests/test_indicator_pattern_quality.py -q` 通过，`56 passed, 1 warning`。
- P1 修复静态检查：`ruff check app/services/selection_service.py app/api/routers/selection_router.py app/jobs/tasks/alert_subscription_task.py tests/services/test_selection_service_provider.py tests/test_alert_subscription_runtime.py tests/test_router_endpoints.py tests/test_scheduler.py` 通过。
- P1 closure：`SelectionService.run_selection()` 不再接受或调用 provider runtime；`/selection` 与 `/screening/run` 和订阅运行均走 canonical `BaselineSQLScreenerRuntime` adapter。
- P1 closure：盘后 alert checker 会先判断 due subscriptions 是否使用 active `pattern` rule；存在 pattern rule 时同步校验 `pattern_recognition` 对目标交易日的完整完成审计，审计 metrics 必须包含 `expected/evaluated/skipped_insufficient_history/failed/matched_stocks/patterns` 且 `failed=0`、`evaluated+skipped>=expected`。`patterns` 表仅表示命中结果，0 命中不再被误判为 partial gap；同日重跑前会清理旧命中，避免 0-hit rerun 后旧 `patterns` 残留误触发。
- final review：reviewer 复核当前 pattern readiness delta 后结论为无新的 `P0/P1/P2`，允许进入 PR。
- 远端 PR 状态：`gh pr status` 当前因本机代理 `127.0.0.1:7890` 连接失败，尚未验证。提交 PR 前必须恢复 GitHub 访问后确认是否已有 PR、CI 状态和 review 状态。
- release gate：`PRE_M3_RELEASE_CLASS=schema_contract make prod-release-precheck` 通过，`expected_revision=current_revision=m3_alert_subscription_baseline`，`upgraded=no`。
- merge gate：`make merge-check` 通过，覆盖 version sync、backend CI、frontend `npm ci/typecheck/build` 和 deploy/dev/staging compose config validation。
- 数据 readiness：真实 scheduler 的正确行为取决于 `daily_bars` coverage；使用 pattern rule 的订阅还取决于 `pattern_recognition` 完成审计。如 `daily_bars` partial gap 或缺少 pattern 评估完成审计，应按当前设计 skip，不能用交互式日期回退或不完整数据生成误报/假阴性。

`2026-05-20` post-merge staging closure：

- release artifact staging：新增 `docker-compose.staging.release.yml` 与 `make staging-release-*`，使用 `instock/instock-app:0.4.1`、`instock/instock-frontend:0.4.1` 验证生产同 tag 镜像，不再用 `:staging + bind mount` 作为 M3 收尾证据。
- snapshot source：`make backup-prod-db` 生成 `backups/postgres/instock_20260520_102137.dump`；`STAGING_POSTGRES_PORT=5544 make restore-staging-db BACKUP=...` 恢复到隔离 staging DB。
- staging env：`STAGING_POSTGRES_PORT=5544`、backend `8002`、frontend `3003`、`STAGING_SCHEDULER_ENABLED=true`；`/health` 与 `/api/v1/info` 均返回 `version=0.4.1`。
- schema drift closure：0.4.0 release-image staging 首次暴露生产快照缺少 `alert_runs.definition_snapshot`、`notifications.alert_condition_id / notification_type / dedupe_key / ts_code`，且 legacy `notifications.type` 仍为 `NOT NULL`。已通过 `m3_alert_run_definition_snapshot`、`m3_notification_schema_reconcile`、`m3_notification_legacy_type_nullable` 三个 idempotent 迁移修复。
- runtime closure：`AlertSubscriptionService.run_subscription()` 的 `IntegrityError` recovery 先缓存 subscription identity，避免 rollback 后访问 expired async ORM 属性触发 `MissingGreenlet`。
- automated checks：M3 focused tests `31 passed`；`make merge-check` 通过，覆盖 version sync、backend CI、frontend `npm ci/typecheck/build` 与 deploy/dev/staging compose config；全量后端为 `294 passed, 1 skipped`，覆盖率 `73.22%`。
- API contract：`python3 scripts/smoke_api_contracts.py --base-url http://localhost:8002` 通过，`59 API contract checks passed`。
- authenticated M3 smoke：新增 `scripts/smoke_m3_alert_flow.py`；staging 上完成注册/登录、metadata、RSI 非默认参数筛选、pattern=DOJI 筛选、两条订阅、手动触发、通知摘要、同日 dedupe、编辑后 stale。证据：`trade_date=20260514`、`rsi_match_count=5`、`pattern_match_count=5`、`deduped_run_id=3`、`stale_status=stale`。
- scheduler/readiness：服务日志确认 `Scheduler started`；直接调用 scheduler 注册同源入口 `app.jobs.tasks.alert_subscription_task.run(date="20260514")` 返回 `status=skipped`、`reason=trade_date_partial_gap`、`coverage.expected_count=5524`、`covered_count=5203`，没有回退旧交易日，也没有生成误报通知。
- final status：`M3 / P3-03` 最小闭环已完成 post-merge staging 收尾；`M3-C` 快捷入口、铃铛、邮件与 Attention 快捷入口继续作为验收后增强项，不阻塞主线进入 `M5 / P3-05`。

### M3 验收 / PR 成功标准

- `Saved Screener` 仍是唯一 authored truth source，`Alert Subscription` 只 pin `selection_condition_id + definition_version + definition_hash`，不得复制筛选 clauses。
- `Registry` 继续作为字段、参数、操作符、展示文案和 adapter 支持矩阵的唯一目录。
- 默认 adapter 可执行首批 `RSI / MACD / BOLL` 参数化条件；持久化层不得出现 SQL 片段、TA-Lib 名称、Python lambda 或用户自定义公式字符串。
- Selection 页面可完成 metadata 读取、非默认参数保存、手动运行、订阅创建、手动触发和站内通知摘要查看。
- Scheduler 盘后任务只在目标交易日数据完整时运行；数据缺失或 partial gap 必须 skip。
- 自动化验证至少覆盖：全量后端 pytest、M3 focused suite、前端 build、Alembic single-head/current、release precheck。
- 文档入口只保留 `EXECUTION_PLAN.md`、`docs/milestones/m3/README.md`、本计划作为当前路线真相；phase3/phase4 文档仅作设计资产。
- PR 必须明确纳入 untracked 的 M2/M3 migrations、services、routers、tests、scripts 与文档整理文件，避免遗漏新增文件。

### `M3-C` 快捷提醒与入口收敛

目标：

- 从选股结果或单股场景一键创建订阅
- 仍然复用 `Saved Screener + Alert Subscription` 主模型

状态：

- `M3-C` 不阻塞当前 `M3` 最小验收
- 只有在用户明确要求继续打磨入口时启动
- 不新增第二套 authored rule model，不接邮件/铃铛/实时轮询

## 当前写集分工

### Docs / scope freeze

- owner: controller / planner
- write set:
  - `docs/EXECUTION_PLAN.md`
  - `docs/README.md`
  - `docs/milestones/README.md`
  - `docs/milestones/m3/README.md`
  - `docs/milestones/m3/M3_P3-03_ALERT_ENGINE_PLAN.md`
  - `docs/milestones/phase3/PHASE3_P3-03_ALERT_ENGINE*.md`
  - `docs/architecture/system_architecture.md`

### Schema / contract

- owner: coder-schema
- write set:
  - canonical `Saved Screener` envelope on top of existing screening save path
  - compat read/write contract for existing `selection_conditions.params`
  - schema tests

### Registry / API

- owner: coder-runtime
- write set:
  - template / registry metadata API
  - manual screening run API
  - preset save / list API

### Adapter / scheduler

- owner: coder-runtime
- write set:
  - default `SQL + TA-Lib` execution adapter
  - focused runtime tests
  - post-close alert subscription task
  - scheduler registration and task tests

## 第一切片停止条件

- `Saved Screener` canonical schema 冻结，且文档中不存在第二套 authored rule model
- `Registry` 已覆盖首批 `MACD / RSI / BOLL`，并暴露 metadata contract
- 用户可手动保存筛选器并运行一次全市场筛选
- legacy flat `params` 入参可被 canonicalize，读取时仍返回 compat 投影
- 当前默认 adapter 可执行；future `vbtpro` 入口已通过接口边界写实，但不要求本切片实现
- focused tests 通过
- 至少 1 条手工 smoke 留痕完成

## 验证

- `alembic upgrade head`
- focused schema / API / adapter tests
- 手工 smoke：
  - 读取 registry metadata
  - 创建一个带参数的 `Saved Screener`
  - 手动运行并验证命中结果
  - 验证 `GET /selection/my-conditions` 同时返回 canonical `definition` 与 compat `params`
  - 验证 `GET /selection/today-summary` 仍能读取并执行
