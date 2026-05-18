#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import MetaData, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.pool import NullPool

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.stock_model import Base
from scripts.migration_live_validation import _run_alembic
from scripts.release_precheck import expected_head_revision, resolve_sync_url

ALEMBIC_VERSION_TABLE = "alembic_version"
POSTGRES_DIALECT = postgresql.dialect()


@dataclass(frozen=True)
class AuditFinding:
    level: str
    kind: str
    table: str | None
    name: str
    expected: str | None
    actual: str | None


@dataclass(frozen=True)
class SchemaOnboardingResult:
    database_identity: str
    expected_revision: str
    current_revision: str | None
    audit_passed: bool
    can_stamp_head: bool
    stamp_applied: bool
    blocking_findings: tuple[AuditFinding, ...]
    warning_findings: tuple[AuditFinding, ...]
    message: str
    evidence_file: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "database_identity": self.database_identity,
            "expected_revision": self.expected_revision,
            "current_revision": self.current_revision,
            "audit_passed": self.audit_passed,
            "can_stamp_head": self.can_stamp_head,
            "stamp_applied": self.stamp_applied,
            "message": self.message,
            "blocking_findings": [asdict(finding) for finding in self.blocking_findings],
            "warning_findings": [asdict(finding) for finding in self.warning_findings],
            "evidence_file": self.evidence_file,
        }


def run_schema_onboarding(
    *,
    sync_url: str | None = None,
    env_file: str | None = None,
    apply_stamp: bool = False,
    evidence_file: str | None = None,
) -> SchemaOnboardingResult:
    resolved_sync_url = resolve_sync_url(sync_url, env_file=env_file)
    current_revision = read_alembic_revision(resolved_sync_url)
    target_revision = expected_head_revision()
    blocking_findings, warning_findings = audit_database_boundary(
        resolved_sync_url,
        Base.metadata,
    )
    audit_passed = not blocking_findings
    can_stamp_head = audit_passed and current_revision is None
    stamp_applied = False

    if current_revision is None:
        if apply_stamp and audit_passed:
            _run_alembic(resolved_sync_url, "stamp", target_revision)
            current_revision = read_alembic_revision(resolved_sync_url)
            if current_revision != target_revision:
                raise RuntimeError(
                    "Schema onboarding stamp did not reach the expected Alembic head "
                    f"{target_revision!r}."
                )
            stamp_applied = True
            can_stamp_head = False
            message = (
                "Schema onboarding audit passed and Alembic was stamped to head "
                f"{target_revision!r}."
            )
        elif audit_passed:
            message = (
                "Schema onboarding audit passed. The target database can now be "
                f"truthfully stamped to head {target_revision!r}."
            )
        else:
            message = (
                "Schema onboarding audit failed. Align the live schema boundary "
                "before stamping Alembic head."
            )
    elif current_revision == target_revision:
        message = (
            "Target database is already under Alembic control at the expected head "
            f"{target_revision!r}."
        )
    else:
        message = (
            "Target database already has alembic_version="
            f"{current_revision!r}. This one-time onboarding path only applies to "
            "unstamped databases; use the normal release precheck/upgrade flow instead."
        )

    result = SchemaOnboardingResult(
        database_identity=_redacted_database_identity(resolved_sync_url),
        expected_revision=target_revision,
        current_revision=current_revision,
        audit_passed=audit_passed,
        can_stamp_head=can_stamp_head,
        stamp_applied=stamp_applied,
        blocking_findings=tuple(blocking_findings),
        warning_findings=tuple(warning_findings),
        message=message,
    )
    return write_evidence(result, evidence_file)


def audit_database_boundary(
    sync_url: str,
    metadata: MetaData,
) -> tuple[list[AuditFinding], list[AuditFinding]]:
    expected_tables = _expected_boundary(metadata)
    actual_tables = _observed_boundary(sync_url)
    blocking_findings: list[AuditFinding] = []
    warning_findings: list[AuditFinding] = []

    for table_name, expected in expected_tables.items():
        actual = actual_tables.get(table_name)
        if actual is None:
            blocking_findings.append(
                AuditFinding(
                    level="block",
                    kind="missing_table",
                    table=table_name,
                    name=table_name,
                    expected="present",
                    actual="missing",
                )
            )
            continue

        _compare_primary_key(blocking_findings, table_name, expected, actual)
        _compare_columns(blocking_findings, warning_findings, table_name, expected, actual)
        _compare_named_members(
            blocking_findings,
            warning_findings,
            table_name,
            "index",
            expected["indexes"],
            actual["indexes"],
        )
        _compare_named_members(
            blocking_findings,
            warning_findings,
            table_name,
            "unique_constraint",
            expected["unique_constraints"],
            actual["unique_constraints"],
        )
        _compare_signatures(
            blocking_findings,
            warning_findings,
            table_name,
            "foreign_key",
            expected["foreign_keys"],
            actual["foreign_keys"],
        )

    extra_tables = sorted(set(actual_tables) - set(expected_tables))
    for table_name in extra_tables:
        warning_findings.append(
            AuditFinding(
                level="warn",
                kind="extra_table",
                table=table_name,
                name=table_name,
                expected=None,
                actual="present",
            )
        )

    return blocking_findings, warning_findings


def read_alembic_revision(sync_url: str) -> str | None:
    engine = create_engine(sync_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            if ALEMBIC_VERSION_TABLE not in inspector.get_table_names():
                return None
            return connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()


def write_evidence(
    result: SchemaOnboardingResult,
    evidence_file: str | None,
) -> SchemaOnboardingResult:
    if not evidence_file:
        return result

    path = Path(evidence_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    result_with_path = SchemaOnboardingResult(
        database_identity=result.database_identity,
        expected_revision=result.expected_revision,
        current_revision=result.current_revision,
        audit_passed=result.audit_passed,
        can_stamp_head=result.can_stamp_head,
        stamp_applied=result.stamp_applied,
        blocking_findings=result.blocking_findings,
        warning_findings=result.warning_findings,
        message=result.message,
        evidence_file=str(path),
    )
    path.write_text(
        json.dumps(result_with_path.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result_with_path


def _expected_boundary(metadata: MetaData) -> dict[str, dict[str, object]]:
    return {
        table.name: {
            "primary_key": tuple(column.name for column in table.primary_key.columns),
            "columns": {
                column.name: {
                    "type": _canonical_type(column.type, POSTGRES_DIALECT),
                    "nullable": bool(column.nullable),
                }
                for column in table.columns
            },
            "indexes": {
                index.name: tuple(column.name for column in index.columns)
                for index in table.indexes
                if index.name
            },
            "unique_constraints": {
                _constraint_key(constraint.name, tuple(column.name for column in constraint.columns)): tuple(
                    column.name for column in constraint.columns
                )
                for constraint in table.constraints
                if isinstance(constraint, UniqueConstraint)
            },
            "foreign_keys": sorted(
                _foreign_key_signature(
                    tuple(element.parent.name for element in constraint.elements),
                    constraint.elements[0].column.table.name,
                    tuple(element.column.name for element in constraint.elements),
                )
                for constraint in table.foreign_key_constraints
            ),
        }
        for table in metadata.sorted_tables
    }


def _observed_boundary(sync_url: str) -> dict[str, dict[str, object]]:
    engine = create_engine(sync_url, poolclass=NullPool)
    try:
        inspector = inspect(engine)
        boundary: dict[str, dict[str, object]] = {}
        for table_name in inspector.get_table_names():
            if table_name == ALEMBIC_VERSION_TABLE:
                continue
            boundary[table_name] = {
                "primary_key": tuple(
                    inspector.get_pk_constraint(table_name).get("constrained_columns") or []
                ),
                "columns": {
                    column["name"]: {
                        "type": _canonical_type(column["type"], engine.dialect),
                        "nullable": bool(column["nullable"]),
                    }
                    for column in inspector.get_columns(table_name)
                },
                "indexes": {
                    index["name"]: tuple(index.get("column_names") or [])
                    for index in inspector.get_indexes(table_name)
                    if index.get("name")
                },
                "unique_constraints": {
                    _constraint_key(
                        constraint.get("name"),
                        tuple(constraint.get("column_names") or []),
                    ): tuple(constraint.get("column_names") or [])
                    for constraint in inspector.get_unique_constraints(table_name)
                },
                "foreign_keys": sorted(
                    _foreign_key_signature(
                        tuple(foreign_key.get("constrained_columns") or []),
                        str(foreign_key.get("referred_table")),
                        tuple(foreign_key.get("referred_columns") or []),
                    )
                    for foreign_key in inspector.get_foreign_keys(table_name)
                ),
            }
        return boundary
    finally:
        engine.dispose()


def _compare_primary_key(
    blocking_findings: list[AuditFinding],
    table_name: str,
    expected: dict[str, object],
    actual: dict[str, object],
) -> None:
    expected_pk = tuple(expected["primary_key"])
    actual_pk = tuple(actual["primary_key"])
    if expected_pk != actual_pk:
        blocking_findings.append(
            AuditFinding(
                level="block",
                kind="primary_key_mismatch",
                table=table_name,
                name=table_name,
                expected=",".join(expected_pk),
                actual=",".join(actual_pk),
            )
        )


def _compare_columns(
    blocking_findings: list[AuditFinding],
    warning_findings: list[AuditFinding],
    table_name: str,
    expected: dict[str, object],
    actual: dict[str, object],
) -> None:
    expected_columns = dict(expected["columns"])
    actual_columns = dict(actual["columns"])

    for column_name, expected_column in expected_columns.items():
        actual_column = actual_columns.get(column_name)
        if actual_column is None:
            blocking_findings.append(
                AuditFinding(
                    level="block",
                    kind="missing_column",
                    table=table_name,
                    name=column_name,
                    expected="present",
                    actual="missing",
                )
            )
            continue

        if expected_column["type"] != actual_column["type"]:
            blocking_findings.append(
                AuditFinding(
                    level="block",
                    kind="column_type_mismatch",
                    table=table_name,
                    name=column_name,
                    expected=str(expected_column["type"]),
                    actual=str(actual_column["type"]),
                )
            )
        if expected_column["nullable"] != actual_column["nullable"]:
            blocking_findings.append(
                AuditFinding(
                    level="block",
                    kind="column_nullability_mismatch",
                    table=table_name,
                    name=column_name,
                    expected=str(expected_column["nullable"]).lower(),
                    actual=str(actual_column["nullable"]).lower(),
                )
            )

    for column_name in sorted(set(actual_columns) - set(expected_columns)):
        warning_findings.append(
            AuditFinding(
                level="warn",
                kind="extra_column",
                table=table_name,
                name=column_name,
                expected=None,
                actual="present",
            )
        )


def _compare_named_members(
    blocking_findings: list[AuditFinding],
    warning_findings: list[AuditFinding],
    table_name: str,
    member_kind: str,
    expected_members: dict[str, tuple[str, ...]],
    actual_members: dict[str, tuple[str, ...]],
) -> None:
    unmatched_actual_members = dict(actual_members)
    for name, expected_columns in expected_members.items():
        actual_columns = unmatched_actual_members.get(name)
        if (
            actual_columns is None
            and member_kind == "unique_constraint"
            and name.startswith("__columns__:")
        ):
            for actual_name, actual_candidate_columns in unmatched_actual_members.items():
                if tuple(expected_columns) == tuple(actual_candidate_columns):
                    actual_columns = actual_candidate_columns
                    del unmatched_actual_members[actual_name]
                    break
        elif actual_columns is not None:
            del unmatched_actual_members[name]

        if actual_columns is None:
            blocking_findings.append(
                AuditFinding(
                    level="block",
                    kind=f"missing_{member_kind}",
                    table=table_name,
                    name=name,
                    expected=",".join(expected_columns),
                    actual="missing",
                )
            )
            continue
        if tuple(expected_columns) != tuple(actual_columns):
            blocking_findings.append(
                AuditFinding(
                    level="block",
                    kind=f"{member_kind}_mismatch",
                    table=table_name,
                    name=name,
                    expected=",".join(expected_columns),
                    actual=",".join(actual_columns),
                )
            )

    for name in sorted(unmatched_actual_members):
        warning_findings.append(
            AuditFinding(
                level="warn",
                kind=f"extra_{member_kind}",
                table=table_name,
                name=name,
                expected=None,
                actual="present",
            )
        )


def _compare_signatures(
    blocking_findings: list[AuditFinding],
    warning_findings: list[AuditFinding],
    table_name: str,
    member_kind: str,
    expected_members: list[str],
    actual_members: list[str],
) -> None:
    expected_set = set(expected_members)
    actual_set = set(actual_members)

    for signature in sorted(expected_set - actual_set):
        blocking_findings.append(
            AuditFinding(
                level="block",
                kind=f"missing_{member_kind}",
                table=table_name,
                name=signature,
                expected=signature,
                actual="missing",
            )
        )

    for signature in sorted(actual_set - expected_set):
        warning_findings.append(
            AuditFinding(
                level="warn",
                kind=f"extra_{member_kind}",
                table=table_name,
                name=signature,
                expected=None,
                actual=signature,
            )
        )


def _constraint_key(name: str | None, columns: tuple[str, ...]) -> str:
    if name:
        return name
    return "__columns__:" + ",".join(columns)


def _foreign_key_signature(
    constrained_columns: tuple[str, ...],
    referred_table: str,
    referred_columns: tuple[str, ...],
) -> str:
    return (
        ",".join(constrained_columns)
        + "->"
        + referred_table
        + "."
        + ",".join(referred_columns)
    )


def _canonical_type(column_type, dialect: Dialect) -> str:
    compiled = column_type.compile(dialect=dialect)
    normalized = re.sub(r"\s+", " ", compiled).strip().lower()
    return normalized


def _redacted_database_identity(sync_url: str) -> str:
    url = make_url(sync_url)
    return url.render_as_string(hide_password=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a real target database against the current SQLAlchemy/Alembic "
            "head boundary, and optionally stamp Alembic head only after the audit passes."
        )
    )
    parser.add_argument(
        "--sync-url",
        default=None,
        help="Override SYNC_DATABASE_URL for the onboarding audit.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Load DB settings from this env file before resolving the sync URL.",
    )
    parser.add_argument(
        "--apply-stamp",
        action="store_true",
        help="Stamp Alembic head after the audit passes on an unstamped database.",
    )
    parser.add_argument(
        "--evidence-file",
        default=None,
        help="Write the onboarding audit/stamp evidence as JSON to this path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_schema_onboarding(
        sync_url=args.sync_url,
        env_file=args.env_file,
        apply_stamp=args.apply_stamp,
        evidence_file=args.evidence_file,
    )
    print(result.message)
    print(f"database={result.database_identity}")
    print(f"expected_revision={result.expected_revision}")
    print(f"current_revision={result.current_revision or 'unstamped'}")
    print(f"audit_passed={'yes' if result.audit_passed else 'no'}")
    print(f"can_stamp_head={'yes' if result.can_stamp_head else 'no'}")
    print(f"stamp_applied={'yes' if result.stamp_applied else 'no'}")
    print(f"blocking_findings={len(result.blocking_findings)}")
    print(f"warning_findings={len(result.warning_findings)}")
    if result.evidence_file:
        print(f"evidence_file={result.evidence_file}")

    return 0 if _result_is_successful(result, apply_stamp=args.apply_stamp) else 1


def _result_is_successful(
    result: SchemaOnboardingResult,
    *,
    apply_stamp: bool,
) -> bool:
    if not result.audit_passed:
        return False
    if result.current_revision not in {None, result.expected_revision} and not result.stamp_applied:
        return False
    if apply_stamp and not (result.stamp_applied or result.current_revision == result.expected_revision):
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
