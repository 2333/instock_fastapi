import importlib.util
from pathlib import Path

import pytest

from app.models.stock_model import (
    AlertCondition,
    AlertRun,
    AlertRunHit,
    AlertSubscription,
    Notification,
)
from app.schemas.alert_schema import (
    AlertRule,
    AlertRuleCreate,
    AlertRuleUpdate,
    MarkNotificationReadRequest,
    NotificationItem,
    NotificationListResponse,
)
from app.services.screener_adapter import build_definition_hash, canonicalize_legacy_params

MIGRATION_PATH = Path("alembic/versions/2026_04_22_0005_m3_alert_engine_baseline.py")
SCREENER_CONDITION_VERSIONING_MIGRATION_PATH = Path(
    "alembic/versions/2026_04_23_0006_m3_saved_screener_condition_versioning.py"
)
ALERT_SUBSCRIPTION_MIGRATION_PATH = Path(
    "alembic/versions/2026_04_24_0007_m3_alert_subscription_baseline.py"
)
ALERT_RUN_DEFINITION_SNAPSHOT_MIGRATION_PATH = Path(
    "alembic/versions/2026_05_20_0008_m3_alert_run_definition_snapshot.py"
)
NOTIFICATION_SCHEMA_RECONCILE_MIGRATION_PATH = Path(
    "alembic/versions/2026_05_20_0009_m3_notification_schema_reconcile.py"
)
NOTIFICATION_LEGACY_TYPE_MIGRATION_PATH = Path(
    "alembic/versions/2026_05_20_0010_m3_notification_legacy_type_nullable.py"
)


def _constraint_names(model) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints}


def _index_names(model) -> set[str]:
    return {index.name for index in model.__table__.indexes}


def _find_check_constraint(model, name: str) -> str | None:
    for constraint in model.__table__.constraints:
        if constraint.name == name:
            return str(constraint.sqltext)
    return None


def test_alert_condition_model_fields_and_indexes():
    assert AlertCondition.__table__.name == "alert_conditions"

    for column in (
        "id",
        "user_id",
        "ts_code",
        "rule_type",
        "threshold",
        "cooldown_minutes",
        "is_active",
        "created_at",
        "updated_at",
    ):
        assert column in AlertCondition.__table__.columns

    assert {"ix_alert_conditions_user_id", "ix_alert_conditions_ts_code"} <= _index_names(
        AlertCondition
    )
    assert "uq_alert_conditions_user_ts_code_rule_type_threshold" in _constraint_names(
        AlertCondition
    )


def test_alert_condition_model_restricts_supported_rule_types():
    constraint_sql = _find_check_constraint(AlertCondition, "ck_alert_conditions_rule_type")
    assert constraint_sql is not None
    for rule_type in ("price_above", "price_below", "change_above", "change_below"):
        assert rule_type in constraint_sql


def test_notification_model_fields_and_indexes():
    assert Notification.__table__.name == "notifications"
    for column in (
        "id",
        "user_id",
        "alert_condition_id",
        "subscription_id",
        "alert_run_id",
        "notification_type",
        "dedupe_key",
        "ts_code",
        "title",
        "message",
        "payload",
        "is_read",
        "read_at",
        "created_at",
    ):
        assert column in Notification.__table__.columns

    assert {
        "ix_notifications_user_id",
        "ix_notifications_user_unread",
        "ix_notifications_alert_condition_id",
        "ix_notifications_subscription_id",
        "ix_notifications_alert_run_id",
        "uq_notifications_dedupe_key",
    } <= _index_names(Notification)


def test_alert_subscription_models_pin_saved_screener_identity():
    assert AlertSubscription.__table__.name == "alert_subscriptions"
    for column in (
        "selection_condition_id",
        "definition_version",
        "definition_hash",
        "status",
        "cooldown_trade_days",
    ):
        assert column in AlertSubscription.__table__.columns
    assert "definition_snapshot" not in AlertSubscription.__table__.columns
    assert {
        "ix_alert_subscriptions_user_id",
        "ix_alert_subscriptions_selection_condition_id",
        "ix_alert_subscriptions_status",
    } <= _index_names(AlertSubscription)

    assert AlertRun.__table__.name == "alert_runs"
    assert {"subscription_id", "trade_date", "definition_hash", "notification_id"} <= set(
        AlertRun.__table__.columns.keys()
    )
    assert "uq_alert_runs_subscription_trade_date_definition_hash" in _constraint_names(AlertRun)

    assert AlertRunHit.__table__.name == "alert_run_hits"
    assert {"run_id", "ts_code", "snapshot", "evidence"} <= set(
        AlertRunHit.__table__.columns.keys()
    )
    assert "uq_alert_run_hits_run_ts_code" in _constraint_names(AlertRunHit)


def test_alert_engine_migration_chain_and_contract():
    migration = MIGRATION_PATH.read_text()

    assert 'down_revision: Union[str, None] = "m2_user_events"' in migration
    assert 'if not _table_exists(bind, "alert_conditions")' in migration
    assert 'op.create_table(\n            "alert_conditions"' in migration
    assert 'if not _table_exists(bind, "notifications")' in migration
    assert 'op.create_table(\n            "notifications"' in migration
    assert 'alert_columns = _column_names(bind, "alert_conditions")' in migration
    assert 'notification_columns = _column_names(bind, "notifications")' in migration
    assert (
        'if "ts_code" in alert_columns and "ix_alert_conditions_ts_code" not in alert_indexes'
        in migration
    )
    assert (
        'if (\n        "alert_condition_id" in notification_columns\n        and "ix_notifications_alert_condition_id" not in notification_indexes\n    )'
        in migration
    )
    assert "if _NOTIFICATION_BASELINE_COLUMNS <= notification_columns:" in migration
    assert "if _ALERT_BASELINE_COLUMNS <= alert_columns:" in migration


def test_alert_subscription_migration_extends_notifications_without_alert_conditions():
    migration = ALERT_SUBSCRIPTION_MIGRATION_PATH.read_text()

    assert 'down_revision = "m3_saved_screener_condition_versioning"' in migration
    assert 'op.create_table(\n            "alert_subscriptions"' in migration
    assert 'op.create_table(\n            "alert_runs"' in migration
    assert 'op.create_table(\n            "alert_run_hits"' in migration
    assert 'op.add_column("notifications", sa.Column("subscription_id"' in migration
    assert 'op.add_column("notifications", sa.Column("alert_run_id"' in migration
    assert 'op.add_column("notifications", sa.Column("dedupe_key"' in migration
    assert '"alert_conditions"' not in migration
    subscription_block = migration.split('op.create_table(\n            "alert_runs"')[0]
    assert '"definition_snapshot", postgresql.JSONB' not in subscription_block


def test_alert_run_definition_snapshot_reconcile_migration_is_idempotent():
    migration = ALERT_RUN_DEFINITION_SNAPSHOT_MIGRATION_PATH.read_text()

    assert 'down_revision = "m3_alert_subscription_baseline"' in migration
    assert (
        'if _table_exists(bind, "alert_runs") and "definition_snapshot" not in _column_names'
        in migration
    )
    assert 'op.add_column(\n            "alert_runs"' in migration
    assert '"definition_snapshot", postgresql.JSONB' in migration
    assert 'op.drop_column("alert_runs", "definition_snapshot")' in migration


def test_notification_schema_reconcile_migration_is_idempotent():
    migration = NOTIFICATION_SCHEMA_RECONCILE_MIGRATION_PATH.read_text()

    assert 'down_revision = "m3_alert_run_definition_snapshot"' in migration
    assert 'if "alert_condition_id" not in columns:' in migration
    assert 'if "notification_type" not in columns:' in migration
    assert 'if "dedupe_key" not in columns:' in migration
    assert 'if "ts_code" not in columns:' in migration
    assert 'server_default=""' in migration
    assert '"uq_notifications_dedupe_key"' in migration


def test_notification_legacy_type_nullable_migration_is_idempotent():
    migration = NOTIFICATION_LEGACY_TYPE_MIGRATION_PATH.read_text()

    assert 'down_revision = "m3_notification_schema_reconcile"' in migration
    assert 'if "type" in columns and not columns["type"].get("nullable", True):' in migration
    assert 'op.alter_column(\n            "notifications",' in migration
    assert '"type",' in migration
    assert "nullable=True" in migration


def test_saved_screener_condition_versioning_migration_hash_matches_runtime_for_boll():
    spec = importlib.util.spec_from_file_location(
        "m3_saved_screener_condition_versioning",
        SCREENER_CONDITION_VERSIONING_MIGRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    legacy_params = {"market": "sz", "bollCloseAboveUpper": True}

    assert module._build_definition_hash(legacy_params) == build_definition_hash(  # type: ignore[attr-defined]
        canonicalize_legacy_params(legacy_params)
    )


def test_alert_rule_payload_validates_allowed_rule_types():
    payload = AlertRuleCreate(
        ts_code="000001.SZ",
        rule_type="price_above",
        threshold=10.5,
        cooldown_minutes=30,
    )
    assert payload.rule_type == "price_above"
    assert payload.ts_code == "000001.SZ"
    assert payload.cooldown_minutes == 30


def test_alert_rule_payload_rejects_invalid_rule_type():
    with pytest.raises(Exception):
        AlertRuleCreate.model_validate(
            {"ts_code": "000001.SZ", "rule_type": "invalid_type", "threshold": 10.5}
        )


def test_alert_rule_update_allows_partial_fields():
    payload = AlertRuleUpdate.model_validate({"is_active": False, "threshold": 12.34})
    assert payload.is_active is False
    assert payload.threshold == 12.34
    assert payload.ts_code is None


def test_notification_models_contract():
    notification = NotificationItem(
        id=1,
        user_id=9,
        alert_condition_id=3,
        ts_code="000001.SZ",
        message="test",
    )
    assert notification.message == "test"
    assert notification.title is None

    response = AlertRule(
        id=1,
        user_id=9,
        ts_code="000001.SZ",
        rule_type="change_below",
        threshold=3.0,
        cooldown_minutes=60,
    )
    assert response.rule_type == "change_below"

    wrapped = NotificationListResponse(data=[notification])
    assert len(wrapped.data) == 1
    assert wrapped.data[0].ts_code == "000001.SZ"

    mark_request = MarkNotificationReadRequest()
    assert mark_request.is_read is True
