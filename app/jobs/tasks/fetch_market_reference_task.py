import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.jobs.market_calendar import is_trading_day, should_skip_market_task
from app.jobs.tasks.fetch_audit import upsert_fetch_audit
from app.models.stock_model import DailyBar, StockBlockTrade, StockTop
from core.crawling.tushare_provider import TushareProvider

logger = logging.getLogger(__name__)


async def _resolve_trade_date(session: AsyncSession) -> str | None:
    result = await session.execute(text("SELECT MAX(trade_date) FROM daily_bars"))
    row = result.fetchone()
    return row[0] if row and row[0] else None


def summarize_top_list(rows: Iterable[dict], inst_rows: Iterable[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        ts_code = row.get("ts_code")
        if not ts_code:
            continue
        current = grouped.setdefault(
            ts_code,
            {
                "ts_code": ts_code,
                "trade_date": row.get("trade_date", ""),
                "name": row.get("name"),
                "sum_buy": 0.0,
                "sum_sell": 0.0,
                "net_amount": 0.0,
                "ranking_times": 0,
                "buy_seat": 0,
                "sell_seat": 0,
            },
        )
        current["name"] = current["name"] or row.get("name")
        current["trade_date"] = current["trade_date"] or row.get("trade_date", "")
        current["sum_buy"] += float(row.get("buy_amount") or 0.0)
        current["sum_sell"] += float(row.get("sell_amount") or 0.0)
        current["net_amount"] += float(row.get("net_amount") or 0.0)
        current["ranking_times"] += 1

    for row in inst_rows:
        ts_code = row.get("ts_code")
        if not ts_code or ts_code not in grouped:
            continue
        side = str(row.get("side") or "").lower()
        if side in {"buy", "b", "0"}:
            grouped[ts_code]["buy_seat"] += 1
        elif side in {"sell", "s", "1"}:
            grouped[ts_code]["sell_seat"] += 1

    return list(grouped.values())


async def _load_closes(session: AsyncSession, trade_date: str) -> dict[str, float]:
    result = await session.execute(
        text("SELECT ts_code, close FROM daily_bars WHERE trade_date = :trade_date"),
        {"trade_date": trade_date},
    )
    closes: dict[str, float] = {}
    for ts_code, close in result.fetchall():
        if ts_code and close is not None:
            closes[ts_code] = float(close)
    return closes


def summarize_block_trades(rows: Iterable[dict], closes: dict[str, float]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        ts_code = row.get("ts_code")
        if not ts_code:
            continue

        price = float(row.get("price") or 0.0)
        volume = float(row.get("vol") or 0.0)
        amount = float(row.get("amount") or 0.0)

        current = grouped.setdefault(
            ts_code,
            {
                "ts_code": ts_code,
                "trade_date": row.get("trade_date", ""),
                "amount_sum": 0.0,
                "volume_sum": 0.0,
                "weighted_price": 0.0,
                "trade_count": 0,
            },
        )
        current["trade_date"] = current["trade_date"] or row.get("trade_date", "")
        current["amount_sum"] += amount
        current["volume_sum"] += volume
        current["weighted_price"] += price * volume
        current["trade_count"] += 1

    summarized: list[dict] = []
    for ts_code, item in grouped.items():
        volume_sum = item["volume_sum"]
        avg_price = item["weighted_price"] / volume_sum if volume_sum else 0.0
        close_price = closes.get(ts_code)
        premium_rate = ((avg_price - close_price) / close_price * 100.0) if close_price else None
        summarized.append(
            {
                "ts_code": ts_code,
                "trade_date": item["trade_date"],
                "close_price": close_price,
                "pct_chg": None,
                "avg_price": avg_price or None,
                "premium_rate": premium_rate,
                "trade_count": item["trade_count"],
                "total_volume": volume_sum or None,
                "total_amount": item["amount_sum"] or None,
            }
        )
    return summarized


async def save_stock_tops(session: AsyncSession, rows: list[dict], trade_date: str) -> int:
    await session.execute(text("DELETE FROM stock_tops WHERE trade_date = :trade_date"), {"trade_date": trade_date})
    for row in rows:
        await session.execute(insert(StockTop).values(**row))
    await session.commit()
    return len(rows)


async def save_block_trades(session: AsyncSession, rows: list[dict], trade_date: str) -> int:
    await session.execute(
        text("DELETE FROM stock_block_trades WHERE trade_date = :trade_date"),
        {"trade_date": trade_date},
    )
    for row in rows:
        await session.execute(insert(StockBlockTrade).values(**row))
    await session.commit()
    return len(rows)


async def run():
    logger.info("执行龙虎榜/大宗交易参考数据任务: %s", datetime.now())

    provider = TushareProvider()
    if should_skip_market_task("龙虎榜/大宗交易参考数据任务", today_is_trading_day=await is_trading_day()):
        return

    async with async_session_factory() as session:
        trade_date = await _resolve_trade_date(session)
        if not trade_date:
            logger.warning("龙虎榜/大宗交易参考数据任务跳过: daily_bars 尚无交易日")
            return

        top_rows = await provider.fetch_top_list(trade_date)
        inst_rows = await provider.fetch_top_inst(trade_date)
        summarized_tops = summarize_top_list(top_rows, inst_rows)
        if summarized_tops:
            count = await save_stock_tops(session, summarized_tops, trade_date)
            await upsert_fetch_audit(
                session,
                task_name="fetch_market_reference",
                entity_type="stock_top",
                entity_key="ALL",
                trade_date=trade_date,
                status="done",
                source="tushare",
                note=f"rows={count}",
            )
            await session.commit()
            logger.info("龙虎榜写入完成: %s rows, trade_date=%s", count, trade_date)
        else:
            await upsert_fetch_audit(
                session,
                task_name="fetch_market_reference",
                entity_type="stock_top",
                entity_key="ALL",
                trade_date=trade_date,
                status="nodata",
                source="tushare",
                note="empty result",
            )
            await session.commit()
            logger.warning("龙虎榜未产出数据: trade_date=%s", trade_date)

        block_rows = await provider.fetch_block_trade(trade_date)
        closes = await _load_closes(session, trade_date)
        summarized_blocks = summarize_block_trades(block_rows, closes)
        if summarized_blocks:
            count = await save_block_trades(session, summarized_blocks, trade_date)
            await upsert_fetch_audit(
                session,
                task_name="fetch_market_reference",
                entity_type="block_trade",
                entity_key="ALL",
                trade_date=trade_date,
                status="done",
                source="tushare",
                note=f"rows={count}",
            )
            await session.commit()
            logger.info("大宗交易写入完成: %s rows, trade_date=%s", count, trade_date)
        else:
            await upsert_fetch_audit(
                session,
                task_name="fetch_market_reference",
                entity_type="block_trade",
                entity_key="ALL",
                trade_date=trade_date,
                status="nodata",
                source="tushare",
                note="empty result",
            )
            await session.commit()
            logger.warning("大宗交易未产出数据: trade_date=%s", trade_date)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
