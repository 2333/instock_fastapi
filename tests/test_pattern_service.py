from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.pattern_service import PatternService


def make_result(*, rows=None, row=None):
    result = Mock()
    result.fetchall.return_value = rows or []
    result.fetchone.return_value = row
    return result


def make_mapping_row(**kwargs):
    return SimpleNamespace(_mapping=kwargs)


@pytest.mark.asyncio
async def test_build_indicator_snapshot_marks_bullish_and_inside_when_prices_trend_up():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                make_mapping_row(trade_date="20240106", close=15),
                make_mapping_row(trade_date="20240105", close=14),
                make_mapping_row(trade_date="20240104", close=13),
                make_mapping_row(trade_date="20240103", close=12),
                make_mapping_row(trade_date="20240102", close=11),
                make_mapping_row(trade_date="20240101", close=10),
            ]
        )
    )
    service = PatternService(db)

    snapshot = await service._build_indicator_snapshot(
        ts_code="000001.SZ",
        trade_date="20240106",
        ema_fast=2,
        ema_slow=3,
        boll_period=3,
        boll_std=2,
    )

    assert snapshot["ema_signal"] == "bullish"
    assert snapshot["boll_signal"] == "inside"
    assert snapshot["ema_fast_value"] is not None
    assert snapshot["ema_slow_value"] is not None
    assert snapshot["boll_upper"] is not None
    assert snapshot["boll_lower"] is not None


@pytest.mark.asyncio
async def test_build_indicator_snapshot_marks_bearish_and_breakdown_when_prices_drop_sharply():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                make_mapping_row(trade_date="20240106", close=1),
                make_mapping_row(trade_date="20240105", close=10),
                make_mapping_row(trade_date="20240104", close=10),
                make_mapping_row(trade_date="20240103", close=10),
                make_mapping_row(trade_date="20240102", close=10),
                make_mapping_row(trade_date="20240101", close=10),
            ]
        )
    )
    service = PatternService(db)

    snapshot = await service._build_indicator_snapshot(
        ts_code="000001.SZ",
        trade_date="20240106",
        ema_fast=2,
        ema_slow=3,
        boll_period=5,
        boll_std=1,
    )

    assert snapshot["ema_signal"] == "bearish"
    assert snapshot["boll_signal"] == "breakdown"


@pytest.mark.asyncio
async def test_get_composite_patterns_respects_indicator_mode_any():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(
                rows=[
                    make_mapping_row(
                        ts_code="000001.SZ",
                        trade_date="20240106",
                        pattern_name="HAMMER",
                        pattern_type="reversal",
                        confidence=0.91,
                        stock_name="平安银行",
                        code="000001",
                    )
                ]
            ),
            make_result(
                rows=[
                    make_mapping_row(trade_date="20240106", close=1),
                    make_mapping_row(trade_date="20240105", close=10),
                    make_mapping_row(trade_date="20240104", close=10),
                    make_mapping_row(trade_date="20240103", close=10),
                    make_mapping_row(trade_date="20240102", close=10),
                    make_mapping_row(trade_date="20240101", close=10),
                ]
            ),
        ]
    )
    service = PatternService(db)

    rows = await service.get_composite_patterns(
        signal="BULLISH",
        limit=10,
        start_date=None,
        end_date=None,
        min_confidence=0,
        pattern_names=["HAMMER"],
        ema_fast=2,
        ema_slow=3,
        boll_period=5,
        boll_std=1,
        ema_signal="bullish",
        boll_signal="breakdown",
        indicator_mode="any",
    )

    assert len(rows) == 1
    assert rows[0]["pattern_name"] == "HAMMER"
    assert rows[0]["boll_signal"] == "breakdown"


@pytest.mark.asyncio
async def test_get_composite_patterns_filters_out_rows_when_indicator_mode_all_fails():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(
                rows=[
                    make_mapping_row(
                        ts_code="000001.SZ",
                        trade_date="20240106",
                        pattern_name="HAMMER",
                        pattern_type="reversal",
                        confidence=0.91,
                        stock_name="平安银行",
                        code="000001",
                    )
                ]
            ),
            make_result(
                rows=[
                    make_mapping_row(trade_date="20240106", close=1),
                    make_mapping_row(trade_date="20240105", close=10),
                    make_mapping_row(trade_date="20240104", close=10),
                    make_mapping_row(trade_date="20240103", close=10),
                    make_mapping_row(trade_date="20240102", close=10),
                    make_mapping_row(trade_date="20240101", close=10),
                ]
            ),
        ]
    )
    service = PatternService(db)

    rows = await service.get_composite_patterns(
        signal="BULLISH",
        limit=10,
        start_date=None,
        end_date=None,
        min_confidence=0,
        pattern_names=["HAMMER"],
        ema_fast=2,
        ema_slow=3,
        boll_period=5,
        boll_std=1,
        ema_signal="bullish",
        boll_signal="breakdown",
        indicator_mode="all",
    )

    assert rows == []
