# W2 Migration Validation

> Owner: controller
> Status: go
> Scope: `user_events` schema + Alembic chain

## 变更内容

- 新增 revision: `m2_user_events`
- `down_revision`: `stock_classification_metadata`
- 新增 reusable live-validation helper:
  - `scripts/migration_live_validation.py`
  - `scripts/run_m2_user_events_live_validation.py`
- 新增表:
  - `user_events`
- 新增索引:
  - `ix_user_events_user_created`
  - `ix_user_events_event_type_created`

## 验证命令

```bash
.venv/bin/pytest tests/test_user_event_migration.py -q
.venv/bin/alembic -c alembic.ini history
ALEMBIC_LIVE_TEST_BASE_URL=postgresql://instock_m1:instock_m1_pass@127.0.0.1:55432/postgres SECRET_KEY=test-secret-key-at-least-32-characters .venv/bin/pytest tests/test_user_event_migration.py -q
ALEMBIC_LIVE_TEST_BASE_URL=postgresql://instock_m1:instock_m1_pass@127.0.0.1:55432/postgres SECRET_KEY=test-secret-key-at-least-32-characters .venv/bin/python scripts/run_m2_user_events_live_validation.py --json
```

## 验证结果

- `tests/test_user_event_migration.py` 通过
- Alembic chain:

```text
stock_classification_metadata -> m2_user_events (head), m2 user events
m1_required_fact_tables -> stock_classification_metadata, stock classification metadata
m1_core_fact_timescale -> m1_required_fact_tables, m1 required fact tables
<base> -> m1_core_fact_timescale, m1 core fact timescale
```

- live PostgreSQL 验证已通过，边界遵守 `M1` 已接受的 existing-schema `stamp/document` 策略:
  - 在 disposable PostgreSQL `127.0.0.1:55432` 上临时创建独立数据库
  - 先准备“当前 metadata 去掉 `user_events`”的 pre-M2 schema
  - 将该状态显式 stamp 到 `stock_classification_metadata`
  - 执行 Alembic `upgrade m2_user_events`
  - 再执行 `downgrade stock_classification_metadata`
- live wrapper 输出已验证:
  - `stamped_revision=stock_classification_metadata`
  - `upgraded_revision=m2_user_events`
  - `downgraded_revision=stock_classification_metadata`
  - `prepared_table_count=24`
  - `user_events` 列、索引、外键均符合契约

## 注意事项

- 当前应用启动仍会在 `app/database.py` 中执行 `create_all()`；因此 migration gate 不能以“应用能启动”替代 Alembic live execution
- 本轮未把现有链路伪装成 empty-database baseline，仍严格遵守 `M1` 既有 existing-schema 起点边界
- `tests/test_user_event_migration.py` 默认可在本地快速执行；只有显式设置 `ALEMBIC_LIVE_TEST_BASE_URL` 时才会打开 live PostgreSQL 验证
