# Release Workflow

This project uses a lightweight release workflow suitable for a solo-maintained
full-stack application.

## Status Note (2026-04-20)

This document is still the baseline release checklist, but it is not sufficient
by itself to prove production safety after the `0.3.0` incident.

`W1` is already approved as the active release/bootstrap baseline, but
schema-/ORM-contract-changing releases are still conditional: they must follow
the `Pre-M3` release-correctness gate and can proceed only when the selected
target database is under Alembic control and the gate passes.

## Current Gate Rule

Follow `docs/milestones/m3/PRE_M3_DECISION.md` as the live gate record.

- `GO`: doc-only or non-schema operational releases, but only after checking the
  current decision record first
- `GO`: schema-/ORM-contract-changing releases only when the selected target
  database is under Alembic control and the `schema_contract` gate passes
- `NO-GO`: bypassing `scripts/release_precheck.py` or treating the legacy
  merge/deploy commands below as sufficient release proof for schema-changing
  releases
- `NO-GO`: assuming production can take a schema-contract release just because
  `W1` is approved; the target database state must still satisfy the gate

## One-Time Schema Onboarding For A Real Target DB

Use this operator path only for an existing target database that is not yet
under Alembic control.

The onboarding script does two things:

- audits the live database against the current SQLAlchemy/Alembic `head`
  boundary and records blocking vs informational drift
- stamps `head` only after that audit passes, so the `alembic_version` record is
  truthful for the real database state

Recommended evidence path:

```bash
docs/milestones/m3/artifacts/W1-prod-schema-onboarding-YYYY-MM-DD.json
```

Audit first:

```bash
make prod-schema-onboarding-audit \
  ENV_FILE=prod.env \
  SCHEMA_ONBOARDING_EVIDENCE_FILE=docs/milestones/m3/artifacts/W1-prod-schema-onboarding-YYYY-MM-DD.json
```

If the audit fails, do not stamp. Align the target DB boundary first, rerun the
audit, and keep the JSON evidence with the operator record.

Stamp only after the audit passes:

```bash
make prod-schema-onboarding-stamp \
  ENV_FILE=prod.env \
  SCHEMA_ONBOARDING_EVIDENCE_FILE=docs/milestones/m3/artifacts/W1-prod-schema-onboarding-YYYY-MM-DD.json
```

The JSON evidence is reusable for:

- `W1` release/schema correctness proof that the real target DB was audited
  before onboarding
- `W5` validation records that need the exact pre-release schema boundary and
  any remaining non-blocking residue called out explicitly

Important rules:

- this path is for unstamped databases only
- if `alembic_version` already exists but is not at `head`, use the normal
  `schema_contract` precheck/upgrade path instead of restamping
- extra legacy columns/tables can be recorded as evidence, but missing required
  tables/columns/indexes/constraints/foreign keys are blockers
- do not treat a successful image build or smoke test as a substitute for this
  onboarding audit

## Environment Model

- `dev`: long-lived environment for daily front/back-end collaboration
- `prod`: long-lived production environment
- `staging`: temporary environment, started only for higher-risk verification

Do not keep staging running by default.

## Version Source Of Truth

Repository versioning is driven by the root `VERSION` file and synced to:

- `pyproject.toml`
- `web/package.json`
- `web/package-lock.json`

Use these commands:

```bash
make version-show
make version-check
make version-bump-patch
make version-bump-minor
make version-bump-major
```

## Version Bump Convention

Run the version bump when the branch is ready to merge back to the mainline, not
for every local commit.

- `patch`: bug fixes, small improvements, refactors, crawler/data-source fixes
- `minor`: backward-compatible features, new pages, new APIs, new tasks/capabilities
- `major`: breaking API/config/data-contract changes

If uncertain, choose `patch`.

## Pre-Merge Checklist

Before merging a branch:

1. Stop temporary staging if it was only used for verification.
2. Run `make merge-check`.
3. Choose and run one version bump command.
4. Review the diff for environment or deployment changes carefully.
5. Merge to the mainline branch.

## Production Release

Do not use this section to bypass the current gate rule above.

After the merge lands:

```bash
make prod-build-version VERSION=x.y.z
make prod-release-precheck PRE_M3_RELEASE_CLASS=non_schema ENV_FILE=.env
make prod-deploy-version VERSION=x.y.z PRE_M3_RELEASE_CLASS=non_schema ENV_FILE=.env
make prod-smoke
```

For schema-/ORM-contract-changing releases, the operator inputs must be
explicit and the current gate must already permit the release:

```bash
make prod-release-precheck \
  PRE_M3_RELEASE_CLASS=schema_contract \
  PRE_M3_APPLY_DB_UPGRADE=1 \
  ENV_FILE=prod.env

make prod-deploy-version \
  VERSION=x.y.z \
  PRE_M3_RELEASE_CLASS=schema_contract \
  PRE_M3_APPLY_DB_UPGRADE=1 \
  ENV_FILE=prod.env
```

If the target DB is not yet under Alembic control, stop here and run the
one-time schema onboarding path above before attempting `schema_contract`
precheck or deploy.

If the release changes data shape, scheduler behavior, or backfill logic, bring
up staging before production deployment and validate there first.

For post-merge or release-candidate staging, prefer release-image staging over
local rebuild staging:

```bash
make backup-prod-db
make STAGING_POSTGRES_PORT=5544 restore-staging-db BACKUP=backups/postgres/instock_YYYYmmdd_HHMMSS.dump
make VERSION=x.y.z APP_GIT_SHA=<sha> STAGING_POSTGRES_PORT=5544 STAGING_SCHEDULER_ENABLED=true staging-release-up
docker compose -p instock_staging -f docker-compose.staging.release.yml exec -T app sh -lc 'uv run alembic upgrade head && uv run alembic current'
make STAGING_POSTGRES_PORT=5544 staging-smoke
python3 scripts/smoke_api_contracts.py --base-url http://localhost:8002
python3 scripts/smoke_m3_alert_flow.py --base-url http://localhost:8002
```

Record the backup source, image version, Alembic head, API contract result,
business smoke result, and scheduler/readiness result. A healthy container alone
does not prove scheduler/data-shape changes are ready.
