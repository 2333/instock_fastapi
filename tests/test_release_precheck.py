from unittest.mock import patch

import pytest

from scripts.release_precheck import (
    RELEASE_CLASS_NON_SCHEMA,
    RELEASE_CLASS_SCHEMA_CONTRACT,
    load_env_overrides,
    resolve_sync_url,
    run_release_precheck,
)


def test_non_schema_release_skips_db_revision_gate():
    result = run_release_precheck(release_class=RELEASE_CLASS_NON_SCHEMA)

    assert result.release_class == RELEASE_CLASS_NON_SCHEMA
    assert result.expected_revision is None
    assert result.current_revision is None
    assert result.upgraded is False
    assert "skipped" in result.message


def test_schema_contract_release_fails_when_database_is_not_alembic_managed():
    with patch(
        "scripts.release_precheck.current_alembic_revision",
        side_effect=AssertionError("alembic_version is missing"),
    ):
        with pytest.raises(
            RuntimeError,
            match="not under Alembic control.*release_schema_onboarding.py",
        ):
            run_release_precheck(
                release_class=RELEASE_CLASS_SCHEMA_CONTRACT,
                sync_url="postgresql+psycopg2://user:pass@localhost/db",
            )


def test_schema_contract_release_requires_head_before_deploy():
    with (
        patch("scripts.release_precheck.expected_head_revision", return_value="m2_user_events"),
        patch(
            "scripts.release_precheck.current_alembic_revision",
            return_value="stock_classification_metadata",
        ),
    ):
        with pytest.raises(RuntimeError, match="is not at head"):
            run_release_precheck(
                release_class=RELEASE_CLASS_SCHEMA_CONTRACT,
                sync_url="postgresql+psycopg2://user:pass@localhost/db",
            )


def test_schema_contract_release_can_upgrade_to_head_when_allowed():
    current_revision_values = iter(["stock_classification_metadata", "m2_user_events"])

    with (
        patch("scripts.release_precheck.expected_head_revision", return_value="m2_user_events"),
        patch(
            "scripts.release_precheck.current_alembic_revision",
            side_effect=lambda *_args, **_kwargs: next(current_revision_values),
        ),
        patch("scripts.release_precheck._run_alembic") as run_alembic,
    ):
        result = run_release_precheck(
            release_class=RELEASE_CLASS_SCHEMA_CONTRACT,
            sync_url="postgresql+psycopg2://user:pass@localhost/db",
            apply_db_upgrade=True,
        )

    run_alembic.assert_called_once_with(
        "postgresql+psycopg2://user:pass@localhost/db",
        "upgrade",
        "m2_user_events",
    )
    assert result.expected_revision == "m2_user_events"
    assert result.current_revision == "m2_user_events"
    assert result.upgraded is True


def test_load_env_overrides_reads_simple_env_file(tmp_path):
    env_file = tmp_path / "prod.env"
    env_file.write_text(
        "POSTGRES_USER=instock\nPOSTGRES_PASSWORD=secret\nPOSTGRES_HOST=db\nPOSTGRES_DB=prod\n",
        encoding="utf-8",
    )

    overrides = load_env_overrides(str(env_file))

    assert overrides["POSTGRES_USER"] == "instock"
    assert overrides["POSTGRES_PASSWORD"] == "secret"
    assert overrides["POSTGRES_HOST"] == "db"
    assert overrides["POSTGRES_DB"] == "prod"


def test_resolve_sync_url_prefers_env_file_values_over_defaults(tmp_path):
    env_file = tmp_path / "prod.env"
    env_file.write_text(
        "POSTGRES_USER=instock\nPOSTGRES_PASSWORD=secret\nPOSTGRES_HOST=db\nPOSTGRES_PORT=6543\nPOSTGRES_DB=prod\n",
        encoding="utf-8",
    )

    sync_url = resolve_sync_url(env_file=str(env_file))

    assert sync_url == "postgresql+psycopg2://instock:secret@db:6543/prod"


def test_resolve_sync_url_prefers_env_file_over_conflicting_host_env(tmp_path, monkeypatch):
    env_file = tmp_path / "prod.env"
    env_file.write_text(
        "SYNC_DATABASE_URL=postgresql+psycopg2://file_user:file_pass@file-host:5432/file_db\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "SYNC_DATABASE_URL",
        "postgresql+psycopg2://host_user:host_pass@host-env:5432/host_db",
    )

    sync_url = resolve_sync_url(env_file=str(env_file))

    assert sync_url == "postgresql+psycopg2://file_user:file_pass@file-host:5432/file_db"
