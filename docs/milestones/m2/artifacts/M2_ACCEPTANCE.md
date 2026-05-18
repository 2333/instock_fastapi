# M2 Acceptance Artifact

> Status: go
> Scope: first-wave `P3-01` authenticated user event tracking

## 验收清单

- [x] `user_events` migration 已新增并接到当前 head `stock_classification_metadata` 之后
- [x] `user_events` migration 已从 accepted existing-schema 起点完成 live upgrade / downgrade 验证
- [x] `POST /api/v1/events/track` 已接入路由
- [x] 非法 payload 返回拒绝
- [x] 写入失败不会阻塞主流程，接口返回 `202` + `persisted=false`
- [x] 5 个核心页面已接入首波 6 类事件
- [x] API 级完整事件序列已通过 SQL 查询验证
- [x] 后端 focused tests 通过
- [x] 前端 `typecheck` / `build` 通过
- [x] reviewer 给出最终 `go`

## 自动化验证

- 后端 focused suite:

```bash
ALEMBIC_LIVE_TEST_BASE_URL=postgresql://instock_m1:instock_m1_pass@127.0.0.1:55432/postgres SECRET_KEY=test-secret-key-at-least-32-characters .venv/bin/pytest tests/test_events_router.py tests/test_user_event_migration.py tests/test_auth_router.py tests/test_router_endpoints.py -q
```

结果:

- `26 passed, 1 warning`
- 其中包含首波 6 类事件的完整序列测试:
  - `tests/test_events_router.py::test_track_event_keeps_first_wave_sequence_queryable`
- 其中包含 live PostgreSQL migration test:
  - `tests/test_user_event_migration.py::test_user_event_migration_runs_live_against_postgres`

- reusable live migration wrapper:

```bash
ALEMBIC_LIVE_TEST_BASE_URL=postgresql://instock_m1:instock_m1_pass@127.0.0.1:55432/postgres SECRET_KEY=test-secret-key-at-least-32-characters .venv/bin/python scripts/run_m2_user_events_live_validation.py --json
```

结果:

- disposable DB 上已验证:
  - `stock_classification_metadata -> m2_user_events -> stock_classification_metadata`
  - `prepared_table_count=24`
  - `user_events` 列 / 索引 / 外键符合契约

- 前端 `typecheck`:

```bash
cd web && npm run typecheck
```

结果:

- 通过

- 前端生产构建:

```bash
cd web && npm run build
```

结果:

- 通过
- 现存 Sass `@import` 弃用 warning 与大 chunk warning 继续存在，但不是本次埋点改动引入

## 手工链路

建议手工链路:

1. 登录
2. 进入 `Dashboard`
3. 点击入口进入 `Selection`
4. 执行一次筛选
5. 打开个股详情并查看形态
6. 添加或移除关注
7. 进入 `Backtest` 并运行一次回测

本轮实际执行情况:

- API 级完整事件序列已通过 focused test 与 SQL 查询验证
- live Alembic migration 已在 disposable PostgreSQL 上完成验证
- 浏览器级手工链路尚未在本回合沙箱内完成自动化留痕；如需补齐 UI 级证据，优先按上述步骤在本地运行中的前后端环境执行

## Reviewer 结论

- reviewer 最终结论: `GO for M2 acceptance`
- 最后关闭的 blocker:
  - `stock_classification_metadata -> m2_user_events` 的 live Alembic 执行证据
- 复核通过的关键证据:
  - reusable live migration helper 可从 prepared existing-schema 边界执行 `stamp -> upgrade -> downgrade`
  - focused backend suite 启用 live PostgreSQL 校验后通过

## SQL 验证样本

已验证的查询口径:

```sql
SELECT user_id, event_type, page, event_data, created_at
FROM user_events
WHERE user_id = :user_id
ORDER BY created_at DESC;
```

完整序列验证口径:

```sql
SELECT event_type, page
FROM user_events
WHERE user_id = :user_id
ORDER BY id;
```

当前自动化验证覆盖的预期序列:

1. `page_view` / `/selection`
2. `dashboard_card_click` / `/`
3. `filter_run` / `/selection`
4. `backtest_run` / `/backtest`
5. `pattern_view` / `/stock/600519`
6. `attention_action` / `/attention`

## 回滚边界

当前回滚边界:

- Alembic revision:
  - `m2_user_events`
- 新增表 / 索引:
  - `user_events`
  - `ix_user_events_user_created`
  - `ix_user_events_event_type_created`
- 后端入口:
  - `app/api/routers/events_router.py`
  - `app/main.py`
  - `app/api/routers/__init__.py`
- 前端入口:
  - `web/src/composables/useAnalytics.ts`
  - `web/src/api/index.ts` 中的 `eventsApi.track`
  - `web/src/router/index.ts` 的 `analyticsPage` 路由与 `afterEach`
  - `Dashboard` / `Selection` / `Backtest` / `StockDetail` / `Attention` 页面接线点

回退动作:

1. 回退前端埋点调用与 `useAnalytics`
2. 移除 `/events/track` 路由与 service / schema / model
3. 回退 `m2_user_events` migration
4. 删除 `user_events` 表及其索引
