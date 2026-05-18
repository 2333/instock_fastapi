#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alembic.config import Config
from alembic.script import ScriptDirectory

from scripts.migration_live_validation import _run_alembic, current_alembic_revision

ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
RELEASE_CLASS_NON_SCHEMA = "non_schema"
RELEASE_CLASS_SCHEMA_CONTRACT = "schema_contract"


@dataclass(frozen=True)
class ReleasePrecheckResult:
    release_class: str
    expected_revision: str | None
    current_revision: str | None
    upgraded: bool
    message: str


def expected_head_revision() -> str:
    config = Config(str(ALEMBIC_INI_PATH))
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def load_env_overrides(env_file: str | None = None) -> dict[str, str]:
    if not env_file:
        return {}

    path = Path(env_file)
    if not path.exists():
        raise FileNotFoundError(f"Env file does not exist: {env_file}")

    overrides: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        overrides[key.strip()] = value.strip().strip("'").strip('"')
    return overrides


def resolve_sync_url(
    explicit_sync_url: str | None = None, *, env_file: str | None = None
) -> str:
    if explicit_sync_url:
        return explicit_sync_url

    env = dict(os.environ)
    env.update(load_env_overrides(env_file))

    sync_url = env.get("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    db_user = env.get("POSTGRES_USER") or env.get("DB_USER") or "postgres"
    db_password = env.get("POSTGRES_PASSWORD") or env.get("DB_PASSWORD") or "postgres"
    db_host = env.get("POSTGRES_HOST") or env.get("DB_HOST") or "localhost"
    db_port = env.get("POSTGRES_PORT") or env.get("DB_PORT") or "5432"
    db_name = env.get("POSTGRES_DB") or env.get("DB_NAME") or "instockdb"
    return (
        f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )


def run_release_precheck(
    *,
    release_class: str,
    sync_url: str | None = None,
    env_file: str | None = None,
    apply_db_upgrade: bool = False,
) -> ReleasePrecheckResult:
    if release_class == RELEASE_CLASS_NON_SCHEMA:
        return ReleasePrecheckResult(
            release_class=release_class,
            expected_revision=None,
            current_revision=None,
            upgraded=False,
            message=(
                "non-schema release: DB revision gate skipped by explicit "
                "PRE_M3 release classification"
            ),
        )

    if release_class != RELEASE_CLASS_SCHEMA_CONTRACT:
        raise ValueError(f"Unsupported release_class: {release_class!r}")

    resolved_sync_url = resolve_sync_url(sync_url, env_file=env_file)
    target_revision = expected_head_revision()
    upgraded = False

    try:
        current_revision = current_alembic_revision(resolved_sync_url)
    except AssertionError as exc:
        raise RuntimeError(
            "schema-contract release is blocked: target database is not under "
            "Alembic control. Run scripts/release_schema_onboarding.py to audit "
            "the real target DB boundary and stamp head truthfully before deploy."
        ) from exc

    if current_revision != target_revision:
        if not apply_db_upgrade:
            raise RuntimeError(
                "schema-contract release is blocked: database revision "
                f"{current_revision!r} is not at head {target_revision!r}. "
                "Run the predeploy upgrade path first."
            )
        _run_alembic(resolved_sync_url, "upgrade", target_revision)
        upgraded = True
        current_revision = current_alembic_revision(resolved_sync_url)
        if current_revision != target_revision:
            raise RuntimeError(
                "schema-contract release is blocked: Alembic upgrade did not "
                f"reach head {target_revision!r}."
            )

    return ReleasePrecheckResult(
        release_class=release_class,
        expected_revision=target_revision,
        current_revision=current_revision,
        upgraded=upgraded,
        message=(
            f"schema-contract release gate passed at revision {current_revision!r}"
            + (" after upgrade" if upgraded else "")
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-M3 release gate for production deployment."
    )
    parser.add_argument(
        "--release-class",
        choices=(RELEASE_CLASS_NON_SCHEMA, RELEASE_CLASS_SCHEMA_CONTRACT),
        required=True,
        help="Classify the release before deployment.",
    )
    parser.add_argument(
        "--sync-url",
        default=None,
        help="Override SYNC_DATABASE_URL for the release gate check.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Load DB settings from this env file before resolving the sync URL.",
    )
    parser.add_argument(
        "--apply-db-upgrade",
        action="store_true",
        help="Run alembic upgrade head before deploy for schema-contract releases.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_release_precheck(
        release_class=args.release_class,
        sync_url=args.sync_url,
        env_file=args.env_file,
        apply_db_upgrade=args.apply_db_upgrade,
    )
    print(result.message)
    if result.expected_revision:
        print(f"expected_revision={result.expected_revision}")
    if result.current_revision:
        print(f"current_revision={result.current_revision}")
    print(f"upgraded={'yes' if result.upgraded else 'no'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
