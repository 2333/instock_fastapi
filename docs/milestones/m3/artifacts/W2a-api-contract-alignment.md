# W2a API Contract Alignment

> Status: completed
> Owner: controller + `worker-runtime`
> Depends: `W1`, `W2`
> Last updated: 2026-04-21

## 目标

补齐 `Pre-M3` 中此前未显式覆盖的 API interface alignment：

- 修复线上已出现的 `500`
- 对齐 service return payload 与 declared response schema
- 把本轮 live sweep 固化成可重复脚本，避免再次依赖线上日志排错
- 关闭 `2026-04-21` review reopen 的 analytics `422` 与 legacy string-date fallback 残留

## Owned scope

- public read endpoints 的 response contract 对齐
- 已知 `date` query 到 PostgreSQL `date` bind 的参数类型一致性
- `indicators` / `fund-flow` service payload 与 response model 对齐
- malformed analytics payload 保持在 FastAPI `422` 路径
- legacy `trade_date` string fallback consumer sweep（`indicator_service` / `pattern_service`）
- non-mutating live API smoke 脚本与执行留痕

## Write set

- `app/services/date_utils.py`
- `app/services/indicator_service.py`
- `app/services/fund_flow_service.py`
- `app/services/pattern_service.py`
- `app/api/routers/indicator_router.py`
- `app/schemas/user_event_schema.py`
- focused API/service tests
- `tests/test_events_router.py`
- `tests/test_pattern_service.py`
- `scripts/smoke_api_contracts.py`
- 本 artifact

## Changed files

- `app/services/date_utils.py`
- `app/services/indicator_service.py`
- `app/services/fund_flow_service.py`
- `app/services/pattern_service.py`
- `app/api/routers/indicator_router.py`
- `app/schemas/user_event_schema.py`
- `tests/test_date_utils.py`
- `tests/test_events_router.py`
- `tests/test_stock_service.py`
- `tests/test_market_summary.py`
- `tests/test_service_queries.py`
- `tests/test_pattern_service.py`
- `scripts/smoke_api_contracts.py`

## Commands run

- `./.venv/bin/python -m pytest tests/test_date_utils.py tests/test_stock_service.py tests/test_market_summary.py tests/test_router_endpoints.py -q`
- `./.venv/bin/python -m pytest tests/test_selection_market_services.py tests/test_pattern_service.py tests/test_backtest_service.py -q`
- `./.venv/bin/python -m pytest tests/test_service_queries.py tests/test_router_endpoints.py tests/test_date_utils.py tests/test_stock_service.py tests/test_market_summary.py -q`
- `.venv/bin/python -m pytest tests/test_events_router.py tests/test_service_queries.py tests/test_pattern_service.py tests/test_date_utils.py -q`
- `VERSION=0.3.0 PYTHON_BIN=.venv/bin/python ./scripts/build_release_images.sh`
- `VERSION=0.3.0 PYTHON_BIN=.venv/bin/python PRE_M3_RELEASE_CLASS=non_schema ENV_FILE=.env POSTDEPLOY_SMOKE=1 ./scripts/deploy_release.sh`
- `python3 scripts/smoke_api_contracts.py --base-url http://localhost:8000`
- `docker logs --since 10m instock_app 2>&1 | rg -n "ERROR|Traceback|Unhandled exception|ResponseValidationError|500 Internal Server Error"`

## Results

- `trade_date_dt_param(...)` 已统一返回 `date` 对象，不再把 ISO 字符串直接绑定给 PostgreSQL `date` 参数。
- `/api/v1/stocks` 与 `/api/v1/market/summary` 已从线上 `500` 恢复为 `200`。
- `IndicatorService` 已按交易日聚合/pivot 指标行，并对齐到 `IndicatorResponse`：
  - `/api/v1/indicators`
  - `/api/v1/indicators/latest`
- `FundFlowService` 已把 `trade_date/symbol/name/net_amount_main` 对齐为 `FundFlowResponse`：
  - `/api/v1/fund-flow/{code}`
- `indicator_router` 为 `/indicators/latest` 补上了显式 `response_model`，接口文档与运行时返回保持一致。
- `UserEventTrackRequest` 现在对非对象 `event_data` 抛验证错误，坏 analytics payload 会稳定回到 `422` 而不是穿透到全局 `500`。
- `IndicatorService` 与 `PatternService` 现在会把 ISO 日期过滤参数规范化成 `YYYYMMDD`，避免 legacy `trade_date_dt IS NULL` 时继续走错误的字符串比较。
- 新增 `scripts/smoke_api_contracts.py`，当前覆盖 `59` 条 non-mutating API contract checks。
- live smoke 结果：`59 API contract checks passed`。
- prod app 日志未再出现 `ResponseValidationError`、`Unhandled exception` 或新的 `500`。
- 一次性 register 探针曾创建临时用户 `username='x'` / `email='bad-email'`，已当场删除，不留生产脏数据。
- reopened W2a focused suite 结果：`38 passed, 2 warnings`。
- reviewer 复核：`no findings`
- `code-review-expert` 复核：`no additional blocking findings`

## Live evidence summary

- public read endpoints：当前 representative sweep 全部返回 `200`
- protected endpoints：当前 representative sweep 全部返回预期 `401`
- safe public POST endpoints：
  - `/api/v1/strategies/run` 返回 `200`
  - `/api/v1/auth/login` invalid creds 返回 `401`
  - `/api/v1/auth/refresh` invalid token 返回 `401`

## Open risks

- 当前 smoke 以 non-mutating checks 为主，没有覆盖 authenticated happy-path 的端到端行为。
- legacy fallback 目前主要由 mocked query tests 覆盖，还没有用真实 PostgreSQL `trade_date_dt IS NULL` 数据做 integration 验证。
- `/api/v1/auth/register` 当前仍使用普通 `str` 邮箱字段，不会校验 email 格式；这不是本轮 `500` 根因，但属于输入契约偏松的遗留问题。
- 生产构建仍显示 `git_sha=local`，因为当前构建环境拿不到宿主机 git 信息。
- `Tushare token` 仍在启动日志里报错；与本轮接口对齐无直接关系，但仍是生产运行风险。

## Next step

1. 把本 artifact 与 `smoke_api_contracts.py` 纳入 `W4` 文档终扫，作为 `Pre-M3` 的接口基线证据。
2. 如果要进一步提升发布信心，下一轮补真实 PostgreSQL legacy-row integration coverage 和 authenticated happy-path smoke，而不是再扩大匿名 probe。
3. `W3` 继续做 residue cleanup；`M3` 仍需等 `W4/W5` 完成后再启动。

## Blocked by

- none currently

## Recovery note

- `2026-04-21` reopened analytics/date findings 已修复，并通过 reviewer + review-expert double review。
- 若从这里恢复，先运行 `python3 scripts/smoke_api_contracts.py --base-url http://localhost:8000`，确认当前线上 contract baseline 仍然为绿。
- 如果 smoke 脚本出现回退，先看 `instock_app` 日志中的 `ResponseValidationError` / SQL bind 错误，再决定是 runtime contract 漂移还是 schema 漂移。

## Handoff needed

- none currently
