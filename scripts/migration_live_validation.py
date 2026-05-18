#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from psycopg2 import sql
from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

from app.models.stock_model import Base

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI_PATH = REPO_ROOT / "alembic.ini"
LIVE_VALIDATION_BASE_URL_ENV = "ALEMBIC_LIVE_TEST_BASE_URL"
LIVE_VALIDATION_MAINTENANCE_DB_ENV = "ALEMBIC_LIVE_TEST_MAINTENANCE_DB"
ACCEPTED_EXISTING_SCHEMA_START = "stock_classification_metadata"
M2_USER_EVENTS_REVISION = "m2_user_events"
PREPARED_EXISTING_SCHEMA_EXCLUDED_TABLES = frozenset({"user_events"})
PREPARED_EXISTING_SCHEMA_BOUNDARY = (
    "create current SQLAlchemy metadata except user_events, then stamp "
    "stock_classification_metadata before running Alembic"
)
EXPECTED_USER_EVENTS_INDEXES = (
    "ix_user_events_event_type_created",
    "ix_user_events_user_created",
)
EXPECTED_USER_EVENTS_COLUMNS = (
    "id",
    "user_id",
    "event_type",
    "event_version",
    "page",
    "referrer",
    "event_data",
    "created_at",
)


@dataclass(frozen=True, slots=True)
class MigrationLiveValidationResult:
    database_name: str
    prepared_schema_boundary: str
    stamped_revision: str
    upgraded_revision: str
    downgraded_revision: str
    prepared_table_count: int
    user_events_columns: tuple[str, ...]
    user_events_indexes: tuple[str, ...]
    user_events_foreign_keys: tuple[str, ...]


def resolve_live_validation_base_url(explicit_url: str | None = None) -> str:
    raw_url = explicit_url or os.getenv(LIVE_VALIDATION_BASE_URL_ENV)
    if not raw_url:
        raise ValueError(
            f"Set {LIVE_VALIDATION_BASE_URL_ENV} to a disposable PostgreSQL URL "
            "with CREATE DATABASE privilege."
        )

    return _normalize_sync_url(raw_url).render_as_string(hide_password=False)


def validate_m2_user_events_migration(
    base_url: str | None = None,
) -> MigrationLiveValidationResult:
    normalized_base_url = resolve_live_validation_base_url(base_url)

    with temporary_postgres_database(
        normalized_base_url,
        prefix="m2_user_events_live",
    ) as (database_name, temporary_sync_url):
        prepared_table_count = prepare_accepted_existing_schema_start(temporary_sync_url)

        _run_alembic(temporary_sync_url, "stamp", ACCEPTED_EXISTING_SCHEMA_START)
        stamped_revision = current_alembic_revision(temporary_sync_url)
        if stamped_revision != ACCEPTED_EXISTING_SCHEMA_START:
            raise AssertionError(
                "Prepared database was not stamped to the accepted existing-schema start: "
                f"{stamped_revision!r}"
            )

        _run_alembic(temporary_sync_url, "upgrade", M2_USER_EVENTS_REVISION)
        upgraded_revision = current_alembic_revision(temporary_sync_url)
        if upgraded_revision != M2_USER_EVENTS_REVISION:
            raise AssertionError(
                "Alembic did not reach the target M2 revision: "
                f"{upgraded_revision!r}"
            )

        user_events_columns, user_events_indexes, user_events_foreign_keys = (
            inspect_user_events_contract(temporary_sync_url)
        )

        _run_alembic(temporary_sync_url, "downgrade", ACCEPTED_EXISTING_SCHEMA_START)
        downgraded_revision = current_alembic_revision(temporary_sync_url)
        if downgraded_revision != ACCEPTED_EXISTING_SCHEMA_START:
            raise AssertionError(
                "Alembic did not downgrade back to the accepted existing-schema start: "
                f"{downgraded_revision!r}"
            )

        table_names = set(_inspector(temporary_sync_url).get_table_names())
        if "user_events" in table_names:
            raise AssertionError(
                "user_events still exists after downgrade back to "
                f"{ACCEPTED_EXISTING_SCHEMA_START}"
            )

        return MigrationLiveValidationResult(
            database_name=database_name,
            prepared_schema_boundary=PREPARED_EXISTING_SCHEMA_BOUNDARY,
            stamped_revision=stamped_revision,
            upgraded_revision=upgraded_revision,
            downgraded_revision=downgraded_revision,
            prepared_table_count=prepared_table_count,
            user_events_columns=user_events_columns,
            user_events_indexes=user_events_indexes,
            user_events_foreign_keys=user_events_foreign_keys,
        )


def prepare_accepted_existing_schema_start(sync_url: str) -> int:
    metadata = _current_schema_metadata_without(PREPARED_EXISTING_SCHEMA_EXCLUDED_TABLES)

    # This is the accepted existing-schema start for M2 live validation. We are
    # intentionally not replaying the full historical migration chain from an
    # empty database; we prepare the current audited schema except `user_events`
    # and stamp that state to `stock_classification_metadata` before Alembic runs.
    engine = create_engine(sync_url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            metadata.create_all(bind=connection)
    finally:
        engine.dispose()

    table_names = set(_inspector(sync_url).get_table_names())
    if "user_events" in table_names:
        raise AssertionError("Prepared existing-schema start must not include user_events")

    missing_tables = set(metadata.tables) - table_names
    if missing_tables:
        raise AssertionError(
            "Prepared existing-schema start is missing tables: "
            f"{sorted(missing_tables)!r}"
        )

    return len(metadata.tables)


def inspect_user_events_contract(
    sync_url: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    inspector = _inspector(sync_url)
    table_names = set(inspector.get_table_names())
    if "user_events" not in table_names:
        raise AssertionError("Alembic upgrade did not create user_events")

    columns = {column["name"]: column for column in inspector.get_columns("user_events")}
    if tuple(columns) != EXPECTED_USER_EVENTS_COLUMNS:
        raise AssertionError(
            "user_events columns do not match the expected contract: "
            f"{tuple(columns)!r}"
        )

    _assert_varchar_length(columns["event_type"], 50)
    _assert_varchar_length(columns["page"], 120)
    _assert_varchar_length(columns["referrer"], 255)

    if columns["user_id"]["nullable"] or columns["event_type"]["nullable"]:
        raise AssertionError("user_events non-nullable contract columns became nullable")
    if columns["event_version"]["nullable"] or columns["page"]["nullable"]:
        raise AssertionError("user_events non-nullable contract columns became nullable")
    if columns["created_at"]["nullable"]:
        raise AssertionError("user_events.created_at must be non-nullable")
    if not isinstance(columns["event_data"]["type"], JSONB):
        raise AssertionError("user_events.event_data must use PostgreSQL JSONB")

    indexes = tuple(sorted(index["name"] for index in inspector.get_indexes("user_events")))
    if indexes != EXPECTED_USER_EVENTS_INDEXES:
        raise AssertionError(
            "user_events indexes do not match the expected contract: "
            f"{indexes!r}"
        )

    foreign_keys = tuple(
        sorted(
            ",".join(foreign_key["constrained_columns"])
            + "->"
            + foreign_key["referred_table"]
            + "."
            + ",".join(foreign_key["referred_columns"])
            for foreign_key in inspector.get_foreign_keys("user_events")
        )
    )
    if foreign_keys != ("user_id->users.id",):
        raise AssertionError(
            "user_events foreign keys do not match the expected contract: "
            f"{foreign_keys!r}"
        )

    primary_key = inspector.get_pk_constraint("user_events")["constrained_columns"]
    if primary_key != ["id"]:
        raise AssertionError(
            "user_events primary key changed from the expected single-column id: "
            f"{primary_key!r}"
        )

    return tuple(columns), indexes, foreign_keys


def current_alembic_revision(sync_url: str) -> str:
    engine = create_engine(sync_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            table_names = set(inspect(connection).get_table_names())
            if "alembic_version" not in table_names:
                raise AssertionError("alembic_version is missing after Alembic execution")
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()


@contextmanager
def temporary_postgres_database(
    base_url: str,
    prefix: str,
) -> Iterator[tuple[str, str]]:
    normalized_base_url = _normalize_sync_url(base_url)
    maintenance_db = os.getenv(LIVE_VALIDATION_MAINTENANCE_DB_ENV, "postgres")
    database_name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    admin_dsn = _psycopg_dsn(
        normalized_base_url.set(drivername="postgresql", database=maintenance_db)
    )

    connection = psycopg2.connect(admin_dsn)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )
    finally:
        connection.close()

    temporary_sync_url = normalized_base_url.set(database=database_name).render_as_string(
        hide_password=False
    )

    try:
        yield database_name, temporary_sync_url
    finally:
        connection = psycopg2.connect(admin_dsn)
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                    """,
                    (database_name,),
                )
                cursor.execute(
                    sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
                )
        finally:
            connection.close()


def _run_alembic(sync_url: str, *args: str) -> None:
    command = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(ALEMBIC_INI_PATH),
        *args,
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=_alembic_environment(sync_url),
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Alembic command failed:\n"
            f"command={' '.join(command)}\n"
            f"stdout=\n{completed.stdout}\n"
            f"stderr=\n{completed.stderr}"
        )


def _alembic_environment(sync_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env["SECRET_KEY"] = env.get(
        "SECRET_KEY",
        "migration-live-validation-secret-key-1234567890",
    )
    env["SYNC_DATABASE_URL"] = sync_url
    env["DATABASE_URL"] = (
        make_url(sync_url)
        .set(drivername="postgresql+asyncpg")
        .render_as_string(hide_password=False)
    )
    existing_pythonpath = env.get("PYTHONPATH")
    repo_root = str(REPO_ROOT)
    env["PYTHONPATH"] = (
        repo_root if not existing_pythonpath else f"{repo_root}{os.pathsep}{existing_pythonpath}"
    )
    env.setdefault("DEBUG", "false")
    env.setdefault("SCHEDULER_ENABLED", "false")
    return env


def _current_schema_metadata_without(excluded_tables: set[str] | frozenset[str]) -> MetaData:
    available_tables = set(Base.metadata.tables)
    unknown_tables = set(excluded_tables) - available_tables
    if unknown_tables:
        raise ValueError(f"Unknown excluded tables: {sorted(unknown_tables)!r}")

    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name in excluded_tables:
            continue
        table.to_metadata(metadata)
    return metadata


def _normalize_sync_url(raw_url: str) -> URL:
    url = make_url(raw_url)
    if url.get_backend_name() not in {"postgresql", "postgres"}:
        raise ValueError(f"Live validation requires PostgreSQL, got {url.drivername!r}")
    if not url.database:
        raise ValueError("Live validation requires a PostgreSQL URL with a database name")
    return url.set(drivername="postgresql+psycopg2")


def _psycopg_dsn(url: URL) -> str:
    return url.render_as_string(hide_password=False)


def _inspector(sync_url: str):
    engine = create_engine(sync_url, poolclass=NullPool)
    try:
        return inspect(engine)
    finally:
        engine.dispose()


def _assert_varchar_length(column: dict, expected_length: int) -> None:
    actual_length = getattr(column["type"], "length", None)
    if actual_length != expected_length:
        raise AssertionError(
            f"{column['name']} length changed: expected {expected_length}, got {actual_length}"
        )
