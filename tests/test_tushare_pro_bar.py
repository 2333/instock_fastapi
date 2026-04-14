from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from core.crawling.base import AdjustType
from core.crawling.tushare_provider import TushareConfig, TushareProvider


@pytest.mark.asyncio
async def test_fetch_pro_bar_uses_sdk_for_asset_e(monkeypatch):
    captured: dict = {}

    def fake_pro_bar(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20260403",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "pre_close": 10,
                    "change": 0.5,
                    "pct_chg": 5,
                    "vol": 1000,
                    "amount": 2000,
                }
            ]
        )

    provider = TushareProvider(TushareConfig(token="token", min_delay=0.0))
    monkeypatch.setattr(provider, "_get_pro", lambda: object())
    monkeypatch.setitem(__import__("sys").modules, "tushare", SimpleNamespace(pro_bar=fake_pro_bar))

    rows = await provider.fetch_pro_bar(
        ts_code="000001.SZ",
        asset="E",
        freq="D",
        adj=AdjustType.NO_ADJUST,
        start_date="2026-04-01",
        end_date="2026-04-03",
    )

    assert captured == {
        "ts_code": "000001.SZ",
        "asset": "E",
        "freq": "D",
        "start_date": "20260401",
        "end_date": "20260403",
    }
    assert rows == [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260403",
            "trade_date_dt": date(2026, 4, 3),
            "date": "2026-04-03",
            "open": 10.0,
            "high": 11.0,
            "low": 9.0,
            "close": 10.5,
            "pre_close": 10.0,
            "change": 0.5,
            "change_pct": 5.0,
            "volume": 1000.0,
            "amount": 2000.0,
        }
    ]


@pytest.mark.asyncio
async def test_fetch_pro_bar_groups_trade_date_bulk_rows(monkeypatch):
    provider = TushareProvider(TushareConfig(token="token", min_delay=0.0))

    def fake_call_pro(func_name, **kwargs):
        assert func_name == "daily"
        assert kwargs == {"trade_date": "20260403"}
        return pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20260403",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "pre_close": 10,
                    "change": 0.5,
                    "pct_chg": 5,
                    "vol": 1000,
                    "amount": 2000,
                },
                {
                    "ts_code": "600000.SH",
                    "trade_date": "20260403",
                    "open": 8,
                    "high": 9,
                    "low": 7,
                    "close": 8.5,
                    "pre_close": 8,
                    "change": 0.5,
                    "pct_chg": 6.25,
                    "vol": 3000,
                    "amount": 4000,
                },
            ]
        )

    monkeypatch.setattr(provider, "_get_pro", lambda: object())
    monkeypatch.setattr(provider, "_call_pro", fake_call_pro)

    result = await provider.fetch_daily_by_date("2026-04-03")

    assert set(result) == {"000001.SZ", "600000.SH"}
    assert result["000001.SZ"][0]["trade_date_dt"] == date(2026, 4, 3)
    assert result["600000.SH"][0]["date"] == "2026-04-03"


@pytest.mark.asyncio
async def test_fetch_pro_bar_rejects_unsupported_asset(monkeypatch):
    provider = TushareProvider(TushareConfig(token="token", min_delay=0.0))
    monkeypatch.setattr(provider, "_get_pro", lambda: object())

    rows = await provider.fetch_pro_bar(ts_code="000001.SH", asset="I", freq="D")

    assert rows == []
