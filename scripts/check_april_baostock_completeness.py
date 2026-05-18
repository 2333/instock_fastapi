#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.jobs.tasks.fetch_daily_task import build_baostock_code, save_daily_bars
from app.models.stock_model import DailyBar, Stock
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.base import AdjustType

logger = logging.getLogger(__name__)


def _normalize_ymd(value: str) -> str:
    normalized = value.strip().replace("-", "")
    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError(f"invalid date: {value!r}")
    return normalized


def _to_iso_ymd(value: str) -> str:
    normalized = _normalize_ymd(value)
    return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"


def _today_ymd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _report_default_path(start_date: str, end_date: str, execute: bool) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "execute" if execute else "dryrun"
    return REPO_ROOT / "logs" / f"baostock_completeness_{start_date}_{end_date}_{mode}_{stamp}.json"


@dataclass
class StockCandidate:
    ts_code: str
    symbol: str
    exchange: str
    is_etf: bool
    list_date: str | None
    delist_date: str | None


async def _load_candidates(
    session: AsyncSession,
    *,
    start_date: str,
    end_date: str,
    limit: int | None,
) -> list[StockCandidate]:
    stmt = (
        select(
            Stock.ts_code,
            Stock.symbol,
            Stock.exchange,
            Stock.is_etf,
            Stock.list_date,
            Stock.delist_date,
        )
        .where(
            Stock.list_status == "L",
            text("COALESCE(list_date, '19000101') <= :end_date"),
            text("(delist_date IS NULL OR delist_date = '' OR delist_date >= :start_date)"),
        )
        .params(start_date=start_date, end_date=end_date)
        .order_by(Stock.ts_code)
    )
    if limit:
        stmt = stmt.limit(limit)

    rows = (await session.execute(stmt)).all()
    return [
        StockCandidate(
            ts_code=row.ts_code,
            symbol=row.symbol,
            exchange=row.exchange,
            is_etf=bool(row.is_etf),
            list_date=row.list_date,
            delist_date=row.delist_date,
        )
        for row in rows
    ]


async def _load_existing_dates(
    session: AsyncSession,
    *,
    start_date: str,
    end_date: str,
    candidate_codes: list[str],
) -> dict[str, set[str]]:
    if not candidate_codes:
        return {}

    rows = (
        await session.execute(
            select(DailyBar.ts_code, DailyBar.trade_date).where(
                DailyBar.trade_date.between(start_date, end_date),
                DailyBar.ts_code.in_(candidate_codes),
            )
        )
    ).all()

    existing: dict[str, set[str]] = {}
    for ts_code, trade_date in rows:
        existing.setdefault(str(ts_code), set()).add(str(trade_date))
    return existing


async def run_monthly_completeness_check(
    *,
    start_date: str,
    end_date: str,
    execute: bool,
    report_path: Path,
    limit: int | None = None,
    progress_every: int = 200,
) -> dict[str, Any]:
    normalized_start = _normalize_ymd(start_date)
    normalized_end = _normalize_ymd(end_date)
    if normalized_start > normalized_end:
        raise ValueError("start_date must be <= end_date")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    provider = BaoStockProvider()
    started_at = datetime.now()
    source_latest_trade_date: str | None = None

    async with async_session_factory() as session:
        candidates = await _load_candidates(
            session,
            start_date=normalized_start,
            end_date=normalized_end,
            limit=limit,
        )
        existing_dates = await _load_existing_dates(
            session,
            start_date=normalized_start,
            end_date=normalized_end,
            candidate_codes=[item.ts_code for item in candidates],
        )

        supported_candidates = [
            item
            for item in candidates
            if build_baostock_code(
                ts_code=item.ts_code,
                symbol=item.symbol,
                exchange=item.exchange,
                is_etf=item.is_etf,
            )
            is not None
        ]
        unsupported_candidates = [
            {
                "ts_code": item.ts_code,
                "exchange": item.exchange,
                "reason": "unsupported_bj_exchange"
                if str(item.exchange or "").strip().upper() == "BJ"
                else "unsupported_security_type",
            }
            for item in candidates
            if build_baostock_code(
                ts_code=item.ts_code,
                symbol=item.symbol,
                exchange=item.exchange,
                is_etf=item.is_etf,
            )
            is None
        ]
        contract_anomalies: list[dict[str, Any]] = []

        budget = max(1, int(os.getenv("BAOSTOCK_DAILY_REQUEST_BUDGET", "90000")))
        if len(supported_candidates) > budget:
            raise RuntimeError(
                "BaoStock daily request budget would be exceeded: "
                f"supported_candidates={len(supported_candidates)}, budget={budget}"
            )

        stats = Counter()
        details: list[dict[str, Any]] = []

        logger.info(
            "Starting BaoStock completeness check: start=%s end=%s candidates=%s supported=%s execute=%s",
            normalized_start,
            normalized_end,
            len(candidates),
            len(supported_candidates),
            execute,
        )

        for index, candidate in enumerate(supported_candidates, start=1):
            baostock_code = build_baostock_code(
                ts_code=candidate.ts_code,
                symbol=candidate.symbol,
                exchange=candidate.exchange,
                is_etf=candidate.is_etf,
            )
            if baostock_code is None:
                continue

            db_dates = existing_dates.get(candidate.ts_code, set())
            try:
                bars = await provider.fetch_kline(
                    code=baostock_code,
                    start_date=_to_iso_ymd(normalized_start),
                    end_date=_to_iso_ymd(normalized_end),
                    adjust=AdjustType.NO_ADJUST,
                    period="daily",
                )
            except Exception as exc:
                stats["error_stock_count"] += 1
                details.append(
                    {
                        "ts_code": candidate.ts_code,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue

            source_dates = {
                str(item["date"]).replace("-", "")
                for item in bars
                if item.get("date")
            }
            if source_dates:
                latest_for_stock = max(source_dates)
                if source_latest_trade_date is None or latest_for_stock > source_latest_trade_date:
                    source_latest_trade_date = latest_for_stock

            missing_dates = sorted(source_dates - db_dates)
            extra_dates = sorted(db_dates - source_dates)

            stats["processed_stock_count"] += 1
            stats["baseline_row_count"] += len(source_dates)
            stats["db_row_count"] += len(db_dates)
            stats["missing_row_count"] += len(missing_dates)
            stats["extra_db_row_count"] += len(extra_dates)

            if source_dates:
                stats["stocks_with_source_rows"] += 1
            else:
                stats["stocks_with_no_source_rows"] += 1

            if missing_dates:
                stats["stocks_with_missing_rows"] += 1
            elif source_dates and not extra_dates:
                stats["complete_stock_count"] += 1

            if extra_dates:
                stats["stocks_with_extra_db_rows"] += 1
            if not source_dates and not db_dates:
                stats["no_source_no_db_stock_count"] += 1
            if not source_dates and db_dates:
                stats["no_source_but_db_present_stock_count"] += 1

            written_rows = 0
            if execute and missing_dates:
                missing_bars = [
                    item
                    for item in bars
                    if str(item.get("date", "")).replace("-", "") in set(missing_dates)
                ]
                written_rows = await save_daily_bars(
                    session,
                    candidate.ts_code,
                    missing_bars,
                    source="baostock",
                )
                stats["written_row_count"] += written_rows
                existing_dates.setdefault(candidate.ts_code, set()).update(missing_dates)

            if missing_dates or extra_dates or not source_dates:
                if not source_dates and not db_dates:
                    status = "no_source_no_db"
                elif not source_dates and db_dates:
                    status = "no_source_but_db_present"
                    contract_anomalies.append(
                        {
                            "ts_code": candidate.ts_code,
                            "exchange": candidate.exchange,
                            "status": status,
                            "baseline_rows": len(source_dates),
                            "db_rows": len(db_dates),
                            "extra_db_dates": extra_dates,
                        }
                    )
                elif execute and missing_dates:
                    status = "written"
                else:
                    status = "incomplete"
                if status != "no_source_but_db_present":
                    details.append(
                        {
                            "ts_code": candidate.ts_code,
                            "exchange": candidate.exchange,
                            "status": status,
                            "baseline_rows": len(source_dates),
                            "db_rows": len(db_dates),
                            "missing_dates": missing_dates,
                            "extra_db_dates": extra_dates,
                            "written_rows": written_rows,
                        }
                    )

            if index % progress_every == 0:
                logger.info(
                    "Progress %s/%s, missing_stocks=%s, missing_rows=%s, written_rows=%s",
                    index,
                    len(supported_candidates),
                    stats["stocks_with_missing_rows"],
                    stats["missing_row_count"],
                    stats["written_row_count"],
                )

    finished_at = datetime.now()
    report = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "start_date": normalized_start,
        "end_date": normalized_end,
        "execute": execute,
        "report_path": str(report_path),
        "eligible_stock_count": len(candidates),
        "baostock_supported_stock_count": len(supported_candidates),
        "baostock_unsupported_stock_count": len(unsupported_candidates),
        "unsupported_universe_count": len(unsupported_candidates),
        "unsupported_universe_examples": unsupported_candidates[:20],
        "contract_anomaly_count": len(contract_anomalies),
        "contract_anomalies": contract_anomalies,
        "source_latest_trade_date": source_latest_trade_date,
        "stats": dict(stats),
        "details": details,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit April completeness in daily_bars against BaoStock and optionally backfill missing rows."
    )
    parser.add_argument("--start-date", default="20260401")
    parser.add_argument("--end-date", default=_today_ymd())
    parser.add_argument("--execute", action="store_true", help="write missing rows into daily_bars")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N stocks")
    parser.add_argument("--progress-every", type=int, default=200)
    parser.add_argument("--report-path", type=Path, default=None)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    report_path = args.report_path or _report_default_path(
        _normalize_ymd(args.start_date),
        _normalize_ymd(args.end_date),
        args.execute,
    )
    report = asyncio.run(
        run_monthly_completeness_check(
            start_date=args.start_date,
            end_date=args.end_date,
            execute=args.execute,
            report_path=report_path,
            limit=args.limit,
            progress_every=args.progress_every,
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
