from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.jobs.tasks.fetch_audit import upsert_fetch_audit
from app.models.stock_model import DailyBar, TechnicalFactor

logger = logging.getLogger(__name__)

TECHNICAL_FACTOR_SOURCE = "daily_bars_local"


def _normalize_ymd(value: str) -> str:
    normalized = value.strip().replace("-", "")
    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError(f"invalid trade date: {value!r}")
    return normalized


def _parse_ymd(value: str) -> date:
    return datetime.strptime(_normalize_ymd(value), "%Y%m%d").date()


def _ymd(value: date) -> str:
    return value.strftime("%Y%m%d")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _average(values: Sequence[float | None]) -> float | None:
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return None
    return sum(clean_values) / len(clean_values)


def build_technical_factor_rows(
    bars: Sequence[DailyBar],
    *,
    start_date: str,
) -> list[dict[str, Any]]:
    start_dt = _parse_ymd(start_date)
    rows: list[dict[str, Any]] = []
    ordered_bars = sorted(
        (bar for bar in bars if bar.trade_date_dt is not None),
        key=lambda bar: bar.trade_date_dt,
    )

    for index, bar in enumerate(ordered_bars):
        if bar.trade_date_dt < start_dt:
            continue

        close_values = [_to_float(item.close) for item in ordered_bars[: index + 1]]
        volume_values = [_to_float(item.vol) for item in ordered_bars[: index + 1]]
        amount_values = [_to_float(item.amount) for item in ordered_bars[: index + 1]]

        close = _to_float(bar.close)
        high = _to_float(bar.high)
        low = _to_float(bar.low)
        pre_close = _to_float(bar.pre_close)
        ma5 = _average(close_values[-5:])
        ma10 = _average(close_values[-10:])
        ma20 = _average(close_values[-20:])

        factors: dict[str, Any] = {
            "source": TECHNICAL_FACTOR_SOURCE,
            "close": close,
            "pct_chg": _to_float(bar.pct_chg),
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "vol_ma5": _average(volume_values[-5:]),
            "vol_ma10": _average(volume_values[-10:]),
            "amount_ma5": _average(amount_values[-5:]),
            "window_count": index + 1,
        }
        if high is not None and low is not None and pre_close not in (None, 0):
            factors["amplitude_pct"] = (high - low) / pre_close * 100
        if close is not None and ma5 not in (None, 0):
            factors["close_to_ma5_pct"] = (close - ma5) / ma5 * 100

        rows.append(
            {
                "ts_code": bar.ts_code,
                "trade_date": bar.trade_date,
                "trade_date_dt": bar.trade_date_dt,
                "factors": factors,
            }
        )
    return rows


async def save_technical_factors(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        ts_code = row.get("ts_code")
        trade_date = row.get("trade_date")
        trade_date_dt = row.get("trade_date_dt")
        factors = row.get("factors")
        if not ts_code or not trade_date or trade_date_dt is None or factors is None:
            continue

        existing = await session.scalar(
            select(TechnicalFactor).where(
                TechnicalFactor.ts_code == ts_code,
                TechnicalFactor.trade_date_dt == trade_date_dt,
            )
        )
        if existing:
            existing.trade_date = trade_date
            existing.factors = factors
        else:
            session.add(
                TechnicalFactor(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    trade_date_dt=trade_date_dt,
                    factors=factors,
                )
            )
        count += 1
    return count


async def run_technical_factors_for_code(
    ts_code: str,
    *,
    start_date: str,
    end_date: str,
    lookback_days: int = 40,
    execute: bool = True,
    session_factory: Callable[[], Any] = async_session_factory,
) -> dict[str, Any]:
    start_dt = _parse_ymd(start_date)
    end_dt = _parse_ymd(end_date)
    if start_dt > end_dt:
        raise ValueError("start_date must be <= end_date")
    if lookback_days < 0:
        raise ValueError("lookback_days must be >= 0")

    query_start_dt = start_dt - timedelta(days=lookback_days)
    async with session_factory() as session:
        result = await session.execute(
            select(DailyBar)
            .where(
                DailyBar.ts_code == ts_code,
                DailyBar.trade_date_dt >= query_start_dt,
                DailyBar.trade_date_dt <= end_dt,
            )
            .order_by(DailyBar.trade_date_dt)
        )
        bars = list(result.scalars().all())
        rows = build_technical_factor_rows(bars, start_date=start_date)
        output: dict[str, Any] = {
            "dry_run": not execute,
            "source": TECHNICAL_FACTOR_SOURCE,
            "ts_code": ts_code,
            "start_date": _ymd(start_dt),
            "end_date": _ymd(end_dt),
            "input_rows": len(bars),
            "factor_rows": len(rows),
            "saved_rows": 0,
        }
        if not execute:
            return output

        saved = await save_technical_factors(session, rows)
        await upsert_fetch_audit(
            session,
            task_name="calculate_technical_factors",
            entity_type="technical_factor",
            entity_key=ts_code,
            trade_date=_ymd(end_dt),
            status="done" if saved else "nodata",
            source=TECHNICAL_FACTOR_SOURCE,
            note=json.dumps({"rows": saved}, ensure_ascii=False),
        )
        await session.commit()
        output["saved_rows"] = saved
        return output


async def run_technical_factors_backfill_window(
    *,
    start_date: str,
    end_date: str,
    code_limit: int = 20,
    lookback_days: int = 40,
    execute: bool = False,
    sleep_seconds: float = 0.0,
    session_factory: Callable[[], Any] = async_session_factory,
) -> dict[str, Any]:
    start_dt = _parse_ymd(start_date)
    end_dt = _parse_ymd(end_date)
    if start_dt > end_dt:
        raise ValueError("start_date must be <= end_date")
    if code_limit < 1:
        raise ValueError("code_limit must be >= 1")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be >= 0")

    async with session_factory() as session:
        result = await session.execute(
            select(DailyBar.ts_code)
            .where(DailyBar.trade_date_dt >= start_dt, DailyBar.trade_date_dt <= end_dt)
            .distinct()
            .order_by(DailyBar.ts_code)
            .limit(code_limit)
        )
        target_codes = list(result.scalars().all())

    output: dict[str, Any] = {
        "dry_run": not execute,
        "source": TECHNICAL_FACTOR_SOURCE,
        "start_date": _ymd(start_dt),
        "end_date": _ymd(end_dt),
        "code_limit": code_limit,
        "target_count": len(target_codes),
        "targets": target_codes,
        "input_rows": 0,
        "factor_rows": 0,
        "saved_rows": 0,
        "items": [],
    }
    if not execute:
        return output

    for ts_code in target_codes:
        item = await run_technical_factors_for_code(
            ts_code,
            start_date=_ymd(start_dt),
            end_date=_ymd(end_dt),
            lookback_days=lookback_days,
            execute=True,
            session_factory=session_factory,
        )
        output["input_rows"] += item["input_rows"]
        output["factor_rows"] += item["factor_rows"]
        output["saved_rows"] += item["saved_rows"]
        output["items"].append(item)
        if sleep_seconds:
            await asyncio.sleep(sleep_seconds)

    logger.info(
        "technical_factors local backfill complete: targets=%s factors=%s saved=%s",
        len(target_codes),
        output["factor_rows"],
        output["saved_rows"],
    )
    return output
