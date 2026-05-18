# W1 Release Correctness

> Status: completed
> Owner: `worker-release`
> Depends: `W0`
> Last updated: 2026-04-22

## 目标

建立 release precheck、prod migration/stamp 路径与 postdeploy schema smoke，修复当前生产发布正确性缺口。

## Owned scope

- release precheck 与 prod deploy proof path
- prod revision / stamp / schema compatibility gate
- postdeploy schema smoke 与 artifact 留痕

## Write set

- `docs/deployment/release_workflow.md`
- `scripts/deploy_release.sh`
- `scripts/build_release_images.sh`
- `scripts/migration_live_validation.py`
- `Makefile` 的 release / smoke / precheck targets（仅在确有需要时）
- `alembic.ini`
- `alembic/env.py`
- `app/database.py`
- `app/main.py`
- dedicated release/bootstrap tests
- 本 artifact

## Do not edit in `W1`

- `app/models/stock_model.py`
- `app/schemas/strategy_schema.py`
- `app/api/routers/strategy_router.py`
- `app/jobs/tasks/strategy_task.py`
- `alembic/versions/`，除非 controller 明确解除 shared-file freeze
- `tests/conftest.py`，除非 controller 先记录 handoff

## 当前执行重点

- 明确“上线前生产库必须处于哪个 revision / stamp 状态”。
- 把 release workflow 从“镜像构建 + 容器重建”补成“predeploy proof + deploy + postdeploy smoke”。
- 在不引入 runtime fallback 的前提下，写清 prod schema compatibility 的验证路径。
- 把 `2026-04-21` 生产完整度审计暴露出的 `daily_bars` uniqueness drift 写实到 release baseline，不再把它留在运行时静默降级里。
- 关闭 `2026-04-21` review reopen 的 bootstrap finding：startup 不得再抢在 Alembic 前创建 `user_events` 这类受管表。

## Next actions

1. 审核现有 release docs / scripts / make targets，列出缺失的 migration/stamp/schema gate。
2. 判断 `scripts/migration_live_validation.py` 哪部分可复用为 disposable-db proof，哪部分仍缺 prod-side proof。
3. 只在本 lane 的 write set 内补齐 precheck、deploy gate 和 postdeploy smoke 路径。
4. 在 lift release restriction 之前，把 prod operator 必须提供的输入与证据写进本 artifact。

## Interruption-safe recovery

1. 先读 `PRE_M3_DECISION.md` 和 tracker，确认 `worker-release` 仍是当前 owner。
2. 回到本 artifact 的 `Next actions` / `Blocked by` / `Recovery note`，从上次停下的位置继续。
3. 如果下一步需要进入 runtime/model/schema 文件，停止实现，先记录 handoff。
4. 停手前更新 `Changed files`、`Commands run`、`Results`、`Open risks`、`Next step`、`Blocked by`、`Recovery note`。

## Handoff triggers

- 发现 release gate 只能通过修改 runtime/model/schema 才能成立。
- 发现必须新建或改写 `alembic/versions/` revision 才能继续。
- 发现必须进入 `tests/conftest.py` 或其他 shared fixture 才能补验证。

## 预期输出

- 明确生产库如何纳入 Alembic/stamp 或受控迁移路径
- 补足 release docs / scripts / gates
- 记录 prod predeploy 与 postdeploy 的验证步骤

## 当前恢复说明

- `2026-04-21` reopened bootstrap finding 已修复，当前 lane 已重新回到可恢复的 completed baseline。
- 如果此时中断，下一位接手者应先确认 `schema_contract` onboarding path 是否有新限制，再决定是继续推进 `W2b/W4` 还是补更强 staging 证明。

## Changed files

- `app/database.py`
- `app/main.py`
- `tests/test_release_bootstrap_correctness.py`
- `docs/deployment/release_workflow.md`
- `scripts/release_precheck.py`
- `scripts/release_schema_onboarding.py`
- `scripts/pre_m3_schema_onboarding_20260422.sql`
- `scripts/deploy_release.sh`
- `scripts/build_release_images.sh`
- `Makefile`
- `tests/test_release_precheck.py`
- `tests/test_release_schema_onboarding.py`

## Commands run

- `.venv/bin/pytest tests/test_release_bootstrap_correctness.py -q`
- `.venv/bin/pytest tests/test_release_precheck.py -q`
- `.venv/bin/pytest tests/test_user_event_migration.py::test_user_event_model_exposes_contract_columns_and_indexes -q`
- `.venv/bin/pytest tests/test_release_precheck.py -q`
- `.venv/bin/python scripts/release_precheck.py --release-class non_schema --env-file .env`
- `.venv/bin/python -m pytest tests/test_release_precheck.py tests/test_strategy_runtime_schema_alignment.py tests/test_router_endpoints.py -q`
- `.venv/bin/python -m py_compile scripts/release_schema_onboarding.py scripts/release_precheck.py`
- `.venv/bin/python -m pytest tests/test_release_schema_onboarding.py tests/test_release_precheck.py -q`
- `.venv/bin/python scripts/release_schema_onboarding.py --env-file .env --evidence-file docs/milestones/m3/artifacts/W1-prod-schema-onboarding-2026-04-22.json`
- `SYNC_DATABASE_URL=postgresql+psycopg2://instock:instock_pass@localhost:5432/instock DATABASE_URL=postgresql+asyncpg://instock:instock_pass@localhost:5432/instock SECRET_KEY=... ./.venv/bin/python scripts/release_schema_onboarding.py --env-file .env --apply-stamp --evidence-file docs/milestones/m3/artifacts/W1-prod-schema-onboarding-2026-04-22.json`
- `.venv/bin/python scripts/release_precheck.py --release-class schema_contract --env-file .env`

## Results

- 新增了 `scripts/release_schema_onboarding.py`，用于对真实目标库执行 one-time schema onboarding audit / evidence / truthful stamp；它会先按当前 SQLAlchemy/Alembic head boundary 审计 blocker 与 warning，再决定是否允许 stamp。
- `Makefile` 已新增 `prod-schema-onboarding-audit` / `prod-schema-onboarding-stamp` / `prod-release-precheck` 目标，operator 可以按 `ENV_FILE` 显式执行 onboarding 和 release gate。
- `scripts/release_precheck.py` 现在会在遇到 unstamped target DB 时显式指向 `scripts/release_schema_onboarding.py`，不再只给出笼统失败。
- `init_db()` no longer imports ORM metadata or runs `create_all()`. Startup bootstrap is now a non-destructive connectivity check, so it no longer pre-creates Alembic-managed tables such as `user_events` before migrations.
- `app` startup log now says `Database connectivity verified`, which matches the new non-schema-mutating bootstrap behavior.
- Added dedicated bootstrap/release tests proving:
  - startup bootstrap on an empty database does not create `user_events` or any other ORM table
  - FastAPI lifespan still awaits bootstrap and shutdown hooks normally after the change
- Focused verification for the reopened W1 finding passed: bootstrap suite `2 passed`, release precheck suite `7 passed`, user-event contract unit check `1 passed`.
- reviewer 复核：`no findings`
- `code-review-expert` 复核：`no additional blocking findings`
- 新增了可执行的 `scripts/release_precheck.py`，把 release class 明确分成 `non_schema` 与 `schema_contract`。
- `release_precheck` 现在显式读取 `ENV_FILE`，不再偷用仓库默认 `.env` 作为 host-side precheck 配置源。
- `release_precheck` 现在把 `ENV_FILE` 视为权威输入；当宿主机环境与 `ENV_FILE` 冲突时，以 `ENV_FILE` 为准，避免 host-side stale env 静默指向错误数据库。
- `prod-deploy-version` 现在要求显式传入 `PRE_M3_RELEASE_CLASS`；未分类的发布直接 hard fail。
- `schema_contract` 发布会在 deploy 前检查目标数据库是否已纳入 Alembic 且位于 `head`；若带 `PRE_M3_APPLY_DB_UPGRADE=1`，会先执行 `alembic upgrade head`。
- deploy 路径不再先手工 `rm -f` 线上容器；改为直接走 `docker compose up -d --force-recreate --remove-orphans`，避免在 smoke 前主动把现网打空。
- deploy 后会自动执行 `docker_smoke.sh`；`schema_contract` 发布还会再次运行 release precheck，形成前后双 gate。
- `docs/deployment/release_workflow.md` 已写回新版 operator 命令链，明确了 `PRE_M3_RELEASE_CLASS` / `PRE_M3_APPLY_DB_UPGRADE` / `ENV_FILE` 的输入。
- dedicated release suite 结果：`7 passed, 2 warnings`。
- cross-lane focused regression 结果：`23 passed, 2 warnings`。
- `2026-04-22` 已创建真实目标库备份：`backups/postgres/pre_m3_schema_onboard_20260422_133642.dump`。
- `2026-04-22` rehearsal clone 已完整通过：onboarding audit `0 blocker`、truthful stamp 到 `m2_user_events`、`schema_contract` precheck 通过。
- `2026-04-22` 真实目标库已完成 `scripts/pre_m3_schema_onboarding_20260422.sql` 对齐，并通过：
  - `scripts/release_schema_onboarding.py --env-file .env --evidence-file docs/milestones/m3/artifacts/W1-prod-schema-onboarding-2026-04-22.json`
  - truthful stamp 到 `m2_user_events`
  - `./.venv/bin/python scripts/release_precheck.py --release-class schema_contract --env-file .env`
- `schema_contract` 发布路径现已从“文档存在但真实目标库会失败”升级为“真实目标库已通过 truthful onboarding + precheck”的 active baseline。

## Open risks

- Any dev/test workflow that still assumes `app.database.init_db()` will auto-create ORM tables must switch to migrations or explicit test fixture setup; this change removes the runtime fallback by design.
- 这次关闭的是 one-time onboarding/stamp 与 `schema_contract` precheck 路径；未来真正 schema-changing 发布仍需要按 `PRE_M3_APPLY_DB_UPGRADE=1` 的标准 upgrade/deploy 路径执行，而不是重新 stamp。
- `docker compose up --force-recreate` 仍会重建 app/frontend 容器；虽然已经移除了“先删容器”的更危险动作，但真正的零停机发布不在本轮范围内。
- `W4` 仍需把这套命令链回写到最终主线文档收口。
- 当前 onboarding audit 仍会保留 legacy extra tables/columns/indexes 作为 warning evidence；这不是 blocker，但后续若要继续精简边界，应以 migration/path 演进而不是手工忽略的方式推进。

## Next step

- Keep the new bootstrap behavior as the active W1 release baseline; the reopened bootstrap finding is now closed by focused tests + reviewer + review-expert double review.
- 作为当前 `Pre-M3` 的 release baseline 保持生效，供 `W4` 文档终扫引用。
- 后续 schema-changing 发布一律走 `prod-release-precheck` / `prod-deploy-version` 的 `schema_contract` operator 路径，不再重复一次性 onboarding。
- 将真实目标库的 onboarding evidence 与 `W5` 裁决对齐，作为允许启动 `M3` 的 release proof。

## Blocked by

- none currently

## Recovery note

- `2026-04-21` reopened bootstrap finding is fixed in code, covered by dedicated tests, and has passed reviewer + review-expert double review.
- 若从这里恢复，先读 `PRE_M3_DECISION.md` 确认 release eligibility 是否又有新的限制变更。

## Handoff needed

- none currently

## Required records

- Commands run
- Results
- Open risks
- Next step
- Blocked by
- Recovery note
- Handoff needed
