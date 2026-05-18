import os

import pytest

from app.models.stock_model import UserEvent
from scripts.migration_live_validation import (
    ACCEPTED_EXISTING_SCHEMA_START,
    EXPECTED_USER_EVENTS_COLUMNS,
    EXPECTED_USER_EVENTS_INDEXES,
    LIVE_VALIDATION_BASE_URL_ENV,
    M2_USER_EVENTS_REVISION,
    PREPARED_EXISTING_SCHEMA_BOUNDARY,
    validate_m2_user_events_migration,
)


def _index_names(model) -> set[str]:
    return {index.name for index in model.__table__.indexes}


def test_user_event_model_exposes_contract_columns_and_indexes():
    for column in EXPECTED_USER_EVENTS_COLUMNS[1:]:
        assert column in UserEvent.__table__.columns

    assert set(EXPECTED_USER_EVENTS_INDEXES) <= _index_names(UserEvent)


def test_user_event_migration_runs_live_against_postgres():
    base_url = os.getenv(LIVE_VALIDATION_BASE_URL_ENV)
    if not base_url:
        pytest.skip(
            f"Set {LIVE_VALIDATION_BASE_URL_ENV} to a disposable PostgreSQL URL "
            "to run live Alembic validation."
        )

    result = validate_m2_user_events_migration(base_url)

    assert result.prepared_schema_boundary == PREPARED_EXISTING_SCHEMA_BOUNDARY
    assert result.stamped_revision == ACCEPTED_EXISTING_SCHEMA_START
    assert result.upgraded_revision == M2_USER_EVENTS_REVISION
    assert result.downgraded_revision == ACCEPTED_EXISTING_SCHEMA_START
    assert result.user_events_columns == EXPECTED_USER_EVENTS_COLUMNS
    assert result.user_events_indexes == EXPECTED_USER_EVENTS_INDEXES
    assert result.user_events_foreign_keys == ("user_id->users.id",)
