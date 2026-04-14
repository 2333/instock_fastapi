from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class TableSpec:
    table: str
    natural_key: tuple[str, ...]


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec("daily_bars", ("ts_code", "trade_date_dt")),
    TableSpec("fund_flows", ("ts_code", "trade_date_dt")),
    TableSpec("indicators", ("ts_code", "trade_date_dt", "indicator_name")),
    TableSpec("patterns", ("ts_code", "trade_date_dt", "pattern_name")),
    TableSpec("daily_basic", ("ts_code", "trade_date_dt")),
    TableSpec("stock_st", ("ts_code", "trade_date_dt")),
    TableSpec("technical_factors", ("ts_code", "trade_date_dt")),
)


def _table_label(table: str) -> str:
    return table


async def _fetch_all(session: AsyncSession, sql: str, params: dict[str, Any] | None = None) -> list[dict]:
    result = await session.execute(text(sql), params or {})
    rows: list[dict] = []
    for row in result.mappings().all():
        mapping = getattr(row, "_mapping", row)
        rows.append(dict(mapping))
    return rows


async def _fetch_one(session: AsyncSession, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = await _fetch_all(session, sql, params)
    return rows[0] if rows else {}


async def _table_row_counts_by_date(
    session: AsyncSession,
    table: str,
    sample_limit: int,
) -> list[dict[str, Any]]:
    return await _fetch_all(
        session,
        f"""
        SELECT trade_date, COUNT(*) AS row_count
        FROM {table}
        GROUP BY trade_date
        ORDER BY trade_date DESC
        LIMIT :sample_limit
        """,
        {"sample_limit": sample_limit},
    )


async def _table_total_row_count(session: AsyncSession, table: str) -> int:
    row = await _fetch_one(session, f"SELECT COUNT(*) AS row_count FROM {table}")
    return int(row.get("row_count") or 0)


async def _table_date_range(session: AsyncSession, table: str) -> dict[str, Any]:
    return await _fetch_one(
        session,
        f"""
        SELECT
            MIN(trade_date_dt) AS min_trade_date_dt,
            MAX(trade_date_dt) AS max_trade_date_dt,
            MIN(trade_date) AS min_trade_date,
            MAX(trade_date) AS max_trade_date,
            COUNT(*) AS row_count
        FROM {table}
        """,
    )


async def _table_null_trade_date_dt_count(session: AsyncSession, table: str) -> int:
    row = await _fetch_one(
        session,
        f"SELECT COUNT(*) AS null_trade_date_dt_count FROM {table} WHERE trade_date_dt IS NULL"
    )
    return int(row.get("null_trade_date_dt_count") or 0)


async def _table_duplicate_key_details(
    session: AsyncSession,
    table: str,
    natural_key: Sequence[str],
    sample_limit: int,
) -> tuple[int, list[dict[str, Any]]]:
    key_expr = ", ".join(natural_key)
    duplicate_count_row = await _fetch_one(
        session,
        f"""
        SELECT COUNT(*) AS duplicate_groups
        FROM (
            SELECT 1
            FROM {table}
            GROUP BY {key_expr}
            HAVING COUNT(*) > 1
        ) dup
        """,
    )
    duplicate_groups = int(duplicate_count_row.get("duplicate_groups") or 0)

    sample_rows = await _fetch_all(
        session,
        f"""
        SELECT {key_expr}, COUNT(*) AS duplicate_count
        FROM {table}
        GROUP BY {key_expr}
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, {key_expr}
        LIMIT :sample_limit
        """,
        {"sample_limit": sample_limit},
    )
    return duplicate_groups, sample_rows


def _make_result(
    *,
    check: str,
    table: str,
    status: str,
    value: Any,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": check,
        "table": table,
        "status": status,
        "value": value,
        "details": details or {},
    }


async def _run_table_checks(
    session: AsyncSession,
    spec: TableSpec,
    *,
    sample_limit: int,
) -> list[dict[str, Any]]:
    table = spec.table
    results: list[dict[str, Any]] = []

    total_rows = await _table_total_row_count(session, table)
    row_counts = await _table_row_counts_by_date(session, table, sample_limit)
    status = "ok" if total_rows > 0 else "warn"
    results.append(
        _make_result(
            check="row_counts_by_date",
            table=_table_label(table),
            status=status,
            value=row_counts,
            details={
                "total_rows": total_rows,
                "sample_limit": sample_limit,
                "sampled_dates": len(row_counts),
            },
        )
    )

    date_range = await _table_date_range(session, table)
    range_status = "ok" if date_range.get("row_count") else "warn"
    results.append(
        _make_result(
            check="date_range",
            table=_table_label(table),
            status=range_status,
            value={
                "min_trade_date_dt": date_range.get("min_trade_date_dt"),
                "max_trade_date_dt": date_range.get("max_trade_date_dt"),
                "min_trade_date": date_range.get("min_trade_date"),
                "max_trade_date": date_range.get("max_trade_date"),
            },
            details={"row_count": int(date_range.get("row_count") or 0)},
        )
    )

    null_trade_date_dt_count = await _table_null_trade_date_dt_count(session, table)
    results.append(
        _make_result(
            check="null_trade_date_dt",
            table=_table_label(table),
            status="fail" if null_trade_date_dt_count else "ok",
            value=null_trade_date_dt_count,
            details={"column": "trade_date_dt"},
        )
    )

    duplicate_groups, sample_rows = await _table_duplicate_key_details(
        session, table, spec.natural_key, sample_limit
    )
    results.append(
        _make_result(
            check="duplicate_keys",
            table=_table_label(table),
            status="fail" if duplicate_groups else "ok",
            value=duplicate_groups,
            details={
                "natural_key": list(spec.natural_key),
                "sample": sample_rows,
            },
        )
    )

    return results


async def _run_cross_source_checks(session: AsyncSession) -> list[dict[str, Any]]:
    rows = await _fetch_all(
        session,
        """
        SELECT
            COUNT(*) AS shared_rows,
            COUNT(DISTINCT COALESCE(b.trade_date, d.trade_date)) AS shared_dates,
            MAX(COALESCE(b.trade_date, d.trade_date)) AS latest_shared_trade_date,
            COUNT(DISTINCT b.trade_date) AS daily_bars_dates,
            COUNT(DISTINCT d.trade_date) AS daily_basic_dates
        FROM daily_bars b
        INNER JOIN daily_basic d
            ON b.ts_code = d.ts_code
           AND (
                b.trade_date_dt = d.trade_date_dt
                OR (
                    b.trade_date_dt IS NULL
                    AND d.trade_date_dt IS NULL
                    AND b.trade_date = d.trade_date
                )
           )
        """,
    )
    row = rows[0] if rows else {}
    shared_rows = int(row.get("shared_rows") or 0)
    shared_dates = int(row.get("shared_dates") or 0)
    daily_bars_dates = int(row.get("daily_bars_dates") or 0)
    daily_basic_dates = int(row.get("daily_basic_dates") or 0)
    status = "ok" if shared_rows and shared_dates else "warn"
    return [
        _make_result(
            check="daily_bars_vs_daily_basic_overlap",
            table="daily_bars/daily_basic",
            status=status,
            value={
                "shared_rows": shared_rows,
                "shared_dates": shared_dates,
                "latest_shared_trade_date": row.get("latest_shared_trade_date"),
            },
            details={
                "daily_bars_dates": daily_bars_dates,
                "daily_basic_dates": daily_basic_dates,
            },
        )
    ]


async def run_m1_quality_checks(
    session: AsyncSession,
    *,
    sample_limit: int = 5,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for spec in TABLE_SPECS:
        results.extend(await _run_table_checks(session, spec, sample_limit=sample_limit))
    results.extend(await _run_cross_source_checks(session))
    return results


def summarize_quality_results(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {"ok": 0, "warn": 0, "fail": 0}
    for result in results:
        status = str(result.get("status") or "warn")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_checks": len(results),
        "status_counts": status_counts,
        "failed_checks": [
            {
                "check": item.get("check"),
                "table": item.get("table"),
                "value": item.get("value"),
            }
            for item in results
            if item.get("status") == "fail"
        ],
        "results": list(results),
    }


def has_quality_failures(results: Sequence[dict[str, Any]]) -> bool:
    return any(result.get("status") == "fail" for result in results)
