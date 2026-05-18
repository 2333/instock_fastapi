#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from scripts.migration_live_validation import (
        LIVE_VALIDATION_BASE_URL_ENV,
        validate_m2_user_events_migration,
    )

    parser = argparse.ArgumentParser(
        description="Run live Alembic validation for stock_classification_metadata -> m2_user_events"
    )
    parser.add_argument(
        "--base-url",
        help=(
            "Disposable PostgreSQL URL with CREATE DATABASE privilege. "
            f"Defaults to ${LIVE_VALIDATION_BASE_URL_ENV}."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the structured validation result as JSON",
    )
    args = parser.parse_args()

    result = validate_m2_user_events_migration(args.base_url)

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        print(
            "validated "
            f"{result.stamped_revision} -> {result.upgraded_revision} -> "
            f"{result.downgraded_revision}"
        )
        print(f"temporary_database={result.database_name}")
        print(f"prepared_table_count={result.prepared_table_count}")
        print(f"boundary={result.prepared_schema_boundary}")
        print(f"user_events_columns={','.join(result.user_events_columns)}")
        print(f"user_events_indexes={','.join(result.user_events_indexes)}")
        print(f"user_events_foreign_keys={','.join(result.user_events_foreign_keys)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
