from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.jobs.tasks.fetch_audit import upsert_fetch_audit
from app.models.stock_model import DailyBasic
from core.crawling.tushare_provider import TushareProvider

logger = logging.getLogger(__name__)

DAILY_BASIC_NUMERIC_FIELDS = (
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
)


def _normalize_ymd(value: str) -> str:
    normalized = value.strip().replace("-", "")
    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError(f"invalid trade date: {value!r}")
    return normalized


def _iter_weekdays(start_date: str, end_date: str) -> list[str]:
    start = datetime.strptime(_normalize_ymd(start_date), "%Y%m%d").date()
    end = datetime.strptime(_normalize_ymd(end_date), "%Y%m%d").date()
    if start > end:
        raise ValueError("start_date must be <= end_date")

    dates: list[str] = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


async def save_daily_basic(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        ts_code = row.get("ts_code")
        trade_date = row.get("trade_date")
        trade_date_dt = row.get("trade_date_dt")
        if not ts_code or not trade_date or trade_date_dt is None:
            continue

        values = {
            "ts_code": ts_code,
            "trade_date": trade_date,
            "trade_date_dt": trade_date_dt,
            **{field: row.get(field) for field in DAILY_BASIC_NUMERIC_FIELDS},
        }

        existing = await session.scalar(
            select(DailyBasic).where(
                DailyBasic.ts_code == ts_code,
                DailyBasic.trade_date_dt == trade_date_dt,
            )
        )
        if existing:
            for key, value in values.items():
                if key != "ts_code":
                    setattr(existing, key, value)
        else:
            session.add(DailyBasic(**values))
        count += 1
    return count


async def run_daily_basic_for_date(
    trade_date: str,
    *,
    execute: bool = True,
    provider: TushareProvider | None = None,
    session_factory: Callable[[], Any] = async_session_factory,
) -> dict[str, Any]:
    date_value = _normalize_ymd(trade_date)
    provider = provider or TushareProvider()
    rows = await provider.fetch_daily_basic(date_value)
    result: dict[str, Any] = {
        "dry_run": not execute,
        "trade_date": date_value,
        "fetched_rows": len(rows),
        "saved_rows": 0,
    }
    if not execute:
        return result

    async with session_factory() as session:
        saved = await save_daily_basic(session, rows)
        status = "done" if saved else "nodata"
        await upsert_fetch_audit(
            session,
            task_name="fetch_daily_basic",
            entity_type="daily_basic",
            entity_key="ALL",
            trade_date=date_value,
            status=status,
            source="tushare",
            note=f"rows={saved}",
        )
        await session.commit()
        result["saved_rows"] = saved
    return result


async def run_daily_basic_backfill_window(
    *,
    start_date: str,
    end_date: str,
    day_limit: int | None = None,
    execute: bool = False,
    sleep_seconds: float = 0.0,
    provider: TushareProvider | None = None,
    session_factory: Callable[[], Any] = async_session_factory,
) -> dict[str, Any]:
    if day_limit is not None and day_limit < 1:
        raise ValueError("day_limit must be >= 1")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be >= 0")

    trade_dates = _iter_weekdays(start_date, end_date)
    if day_limit is not None:
        trade_dates = trade_dates[:day_limit]

    provider = provider or TushareProvider()
    result: dict[str, Any] = {
        "dry_run": not execute,
        "start_date": _normalize_ymd(start_date),
        "end_date": _normalize_ymd(end_date),
        "day_limit": day_limit,
        "target_dates": trade_dates,
        "fetched_rows": 0,
        "saved_rows": 0,
        "items": [],
    }
    if not execute:
        return result

    for trade_date in trade_dates:
        item = await run_daily_basic_for_date(
            trade_date,
            execute=True,
            provider=provider,
            session_factory=session_factory,
        )
        result["fetched_rows"] += item["fetched_rows"]
        result["saved_rows"] += item["saved_rows"]
        result["items"].append(item)
        if sleep_seconds:
            await asyncio.sleep(sleep_seconds)

    logger.info(
        "daily_basic backfill window complete: dates=%s fetched=%s saved=%s",
        len(trade_dates),
        result["fetched_rows"],
        result["saved_rows"],
    )
    return result
