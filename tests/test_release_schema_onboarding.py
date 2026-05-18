import json
from unittest.mock import patch

from sqlalchemy import Column, Integer, MetaData, String, Table, UniqueConstraint

from scripts.release_schema_onboarding import (
    _result_is_successful,
    audit_database_boundary,
    run_schema_onboarding,
)


def _minimal_metadata() -> MetaData:
    metadata = MetaData()
    Table(
        "daily_bars",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("ts_code", String(20), nullable=False),
        Column("trade_date_dt", String(10), nullable=False),
        UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            name="uq_daily_bars_ts_code_trade_date_dt",
        ),
    )
    return metadata


def test_audit_database_boundary_blocks_when_required_unique_constraint_is_missing():
    metadata = _minimal_metadata()

    observed_boundary = {
        "daily_bars": {
            "primary_key": ("id",),
            "columns": {
                "id": {"type": "integer", "nullable": False},
                "ts_code": {"type": "varchar(20)", "nullable": False},
                "trade_date_dt": {"type": "varchar(10)", "nullable": False},
            },
            "indexes": {},
            "unique_constraints": {},
            "foreign_keys": [],
        }
    }

    with patch(
        "scripts.release_schema_onboarding._observed_boundary",
        return_value=observed_boundary,
    ):
        blocking_findings, warning_findings = audit_database_boundary(
            "postgresql+psycopg2://user:pass@localhost/db",
            metadata,
        )

    assert any(
        finding.kind == "missing_unique_constraint"
        and finding.name == "uq_daily_bars_ts_code_trade_date_dt"
        for finding in blocking_findings
    )
    assert warning_findings == []


def test_audit_database_boundary_records_extra_legacy_shape_as_warnings_only():
    metadata = _minimal_metadata()

    observed_boundary = {
        "daily_bars": {
            "primary_key": ("id",),
            "columns": {
                "id": {"type": "integer", "nullable": False},
                "ts_code": {"type": "varchar(20)", "nullable": False},
                "trade_date_dt": {"type": "varchar(10)", "nullable": False},
                "legacy_source": {"type": "varchar(20)", "nullable": True},
            },
            "indexes": {},
            "unique_constraints": {
                "uq_daily_bars_ts_code_trade_date_dt": ("ts_code", "trade_date_dt")
            },
            "foreign_keys": [],
        },
        "legacy_shadow_table": {
            "primary_key": ("id",),
            "columns": {"id": {"type": "integer", "nullable": False}},
            "indexes": {},
            "unique_constraints": {},
            "foreign_keys": [],
        },
    }

    with patch(
        "scripts.release_schema_onboarding._observed_boundary",
        return_value=observed_boundary,
    ):
        blocking_findings, warning_findings = audit_database_boundary(
            "postgresql+psycopg2://user:pass@localhost/db",
            metadata,
        )

    assert blocking_findings == []
    assert any(finding.kind == "extra_column" for finding in warning_findings)
    assert any(finding.kind == "extra_table" for finding in warning_findings)


def test_audit_database_boundary_accepts_named_db_unique_for_unnamed_model_unique():
    metadata = MetaData()
    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("email", String(100), unique=True, nullable=False),
    )

    observed_boundary = {
        "users": {
            "primary_key": ("id",),
            "columns": {
                "id": {"type": "integer", "nullable": False},
                "email": {"type": "varchar(100)", "nullable": False},
            },
            "indexes": {},
            "unique_constraints": {"users_email_key": ("email",)},
            "foreign_keys": [],
        }
    }

    with patch(
        "scripts.release_schema_onboarding._observed_boundary",
        return_value=observed_boundary,
    ):
        blocking_findings, warning_findings = audit_database_boundary(
            "postgresql+psycopg2://user:pass@localhost/db",
            metadata,
        )

    assert blocking_findings == []
    assert warning_findings == []


def test_run_schema_onboarding_can_stamp_head_and_write_evidence(tmp_path):
    evidence_file = tmp_path / "schema-onboarding.json"
    revision_values = iter([None, "m2_user_events"])

    with (
        patch(
            "scripts.release_schema_onboarding.expected_head_revision",
            return_value="m2_user_events",
        ),
        patch(
            "scripts.release_schema_onboarding.read_alembic_revision",
            side_effect=lambda *_args, **_kwargs: next(revision_values),
        ),
        patch(
            "scripts.release_schema_onboarding.audit_database_boundary",
            return_value=([], []),
        ),
        patch("scripts.release_schema_onboarding._run_alembic") as run_alembic,
    ):
        result = run_schema_onboarding(
            sync_url="postgresql+psycopg2://user:pass@localhost/db",
            apply_stamp=True,
            evidence_file=str(evidence_file),
        )

    run_alembic.assert_called_once_with(
        "postgresql+psycopg2://user:pass@localhost/db",
        "stamp",
        "m2_user_events",
    )
    assert result.audit_passed is True
    assert result.stamp_applied is True
    assert result.current_revision == "m2_user_events"
    assert result.evidence_file == str(evidence_file)
    assert _result_is_successful(result, apply_stamp=True) is True

    payload = json.loads(evidence_file.read_text(encoding="utf-8"))
    assert payload["expected_revision"] == "m2_user_events"
    assert payload["stamp_applied"] is True
    assert payload["evidence_file"] == str(evidence_file)


def test_run_schema_onboarding_blocks_restamp_when_database_is_already_managed():
    with (
        patch(
            "scripts.release_schema_onboarding.expected_head_revision",
            return_value="m2_user_events",
        ),
        patch(
            "scripts.release_schema_onboarding.read_alembic_revision",
            return_value="stock_classification_metadata",
        ),
        patch(
            "scripts.release_schema_onboarding.audit_database_boundary",
            return_value=([], []),
        ),
    ):
        result = run_schema_onboarding(
            sync_url="postgresql+psycopg2://user:pass@localhost/db",
        )

    assert result.audit_passed is True
    assert result.stamp_applied is False
    assert "one-time onboarding path only applies to unstamped databases" in result.message
    assert _result_is_successful(result, apply_stamp=False) is False
