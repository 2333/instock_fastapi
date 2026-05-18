"""m3 saved screener condition versioning

Revision ID: m3_saved_screener_condition_versioning
Revises: m3_alert_engine_baseline
Create Date: 2026-04-23 10:30:00
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "m3_saved_screener_condition_versioning"
down_revision: Union[str, None] = "m3_alert_engine_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SAVED_SCREENER_SCHEMA_VERSION = 1
_SUPPORTED_FILTER_KEYS = (
    "priceMin",
    "priceMax",
    "changeMin",
    "changeMax",
    "rsiMin",
    "rsiMax",
    "macdBullish",
    "macdBearish",
    "bollCloseAboveUpper",
    "bollCloseBelowLower",
    "pattern",
)
_RULE_DEFAULT_PARAMS = {
    "rsiMin": {"period": 14},
    "rsiMax": {"period": 14},
    "macdBullish": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    "macdBearish": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
    "bollCloseAboveUpper": {"period": 20, "stddev": 2.0},
    "bollCloseBelowLower": {"period": 20, "stddev": 2.0},
}


def _table_exists(bind: sa.Connection, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _column_names(bind: sa.Connection, table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _strip_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strip_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_strip_none(item) for item in value]
    return value


def _normalize_legacy_filter_payload(params: Any) -> dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    payload = dict(params)
    nested_filters = payload.get("filters")
    if isinstance(nested_filters, dict):
        payload = nested_filters
    return {key: value for key, value in payload.items() if value is not None}


def _canonicalize_definition_for_hash(params: Any) -> dict[str, Any]:
    if isinstance(params, dict) and params.get("kind") == "saved_screener":
        return _strip_none(params)

    filters = _normalize_legacy_filter_payload(params)
    scope: dict[str, Any] = {"limit": 300}
    if filters.get("market") is not None:
        scope["market"] = filters["market"]

    children = []
    for filter_key in _SUPPORTED_FILTER_KEYS:
        value = filters.get(filter_key)
        if value is None:
            continue
        if isinstance(value, bool) and value is False:
            continue
        children.append(
            {
                "type": "predicate",
                "rule_key": filter_key,
                "params": {
                    **_RULE_DEFAULT_PARAMS.get(filter_key, {}),
                    "value": value,
                },
            }
        )

    return {
        "kind": "saved_screener",
        "ast_version": 1,
        "registry_version": 1,
        "scope": scope,
        "root": {
            "type": "group",
            "op": "all",
            "children": children,
        },
    }


def _build_definition_hash(params: Any) -> str:
    canonical_definition = _canonicalize_definition_for_hash(params)
    canonical_json = json.dumps(
        canonical_definition,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    table_name = "selection_conditions"

    if not _table_exists(bind, table_name):
        return

    existing_columns = _column_names(bind, table_name)

    if "schema_version" not in existing_columns:
        op.add_column(
            table_name,
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )
    if "definition_version" not in existing_columns:
        op.add_column(
            table_name,
            sa.Column(
                "definition_version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )
    if "definition_hash" not in existing_columns:
        op.add_column(
            table_name,
            sa.Column("definition_hash", sa.String(length=64), nullable=True),
        )
    if "updated_at" not in existing_columns:
        op.add_column(
            table_name,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    rows = bind.execute(
        sa.text(
            """
            SELECT id, params, created_at, definition_hash, definition_version, schema_version, updated_at
            FROM selection_conditions
            """
        )
    ).mappings()

    for row in rows:
        bind.execute(
            sa.text(
                """
                UPDATE selection_conditions
                SET schema_version = :schema_version,
                    definition_version = :definition_version,
                    definition_hash = :definition_hash,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "schema_version": int(row.get("schema_version") or _SAVED_SCREENER_SCHEMA_VERSION),
                "definition_version": int(row.get("definition_version") or 1),
                "definition_hash": row.get("definition_hash")
                or _build_definition_hash(row.get("params")),
                "updated_at": row.get("updated_at") or row.get("created_at"),
            },
        )

    op.execute(
        sa.text(
            """
            UPDATE selection_conditions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE updated_at IS NULL
            """
        )
    )
    op.alter_column(table_name, "updated_at", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    table_name = "selection_conditions"

    if not _table_exists(bind, table_name):
        return

    existing_columns = _column_names(bind, table_name)
    for column_name in ("updated_at", "definition_hash", "definition_version", "schema_version"):
        if column_name in existing_columns:
            op.drop_column(table_name, column_name)
