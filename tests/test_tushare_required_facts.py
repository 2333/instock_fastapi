from datetime import date

import pandas as pd
import pytest

from core.crawling.tushare_provider import TushareConfig, TushareProvider


def _provider(monkeypatch, frame_by_endpoint: dict[str, pd.DataFrame | Exception]) -> TushareProvider:
    provider = TushareProvider(TushareConfig(token="token", min_delay=0.0))
    monkeypatch.setattr(provider, "_get_pro", lambda: object())

    def fake_call_pro(func_name, **kwargs):
        response = frame_by_endpoint[func_name]
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(provider, "_call_pro", fake_call_pro)
    return provider


@pytest.mark.asyncio
async def test_fetch_daily_basic_maps_required_fields(monkeypatch):
    provider = _provider(
        monkeypatch,
        {
            "daily_basic": pd.DataFrame(
                [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260403",
                        "turnover_rate": 1.2,
                        "turnover_rate_f": 2.3,
                        "volume_ratio": 1.1,
                        "pe": 8.5,
                        "pe_ttm": 8.6,
                        "pb": 0.9,
                        "ps": 1.7,
                        "ps_ttm": 1.8,
                        "dv_ratio": 3.1,
                        "dv_ttm": 3.2,
                        "total_share": 100,
                        "float_share": 80,
                        "free_share": 60,
                        "total_mv": 1000,
                        "circ_mv": 800,
                    },
                    {
                        "ts_code": "",
                        "trade_date": "20260403",
                        "turnover_rate": 9.9,
                    },
                ]
            )
        },
    )

    rows = await provider.fetch_daily_basic("2026-04-03")

    assert rows == [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260403",
            "trade_date_dt": date(2026, 4, 3),
            "turnover_rate": 1.2,
            "turnover_rate_f": 2.3,
            "volume_ratio": 1.1,
            "pe": 8.5,
            "pe_ttm": 8.6,
            "pb": 0.9,
            "ps": 1.7,
            "ps_ttm": 1.8,
            "dv_ratio": 3.1,
            "dv_ttm": 3.2,
            "total_share": 100.0,
            "float_share": 80.0,
            "free_share": 60.0,
            "total_mv": 1000.0,
            "circ_mv": 800.0,
        }
    ]


@pytest.mark.asyncio
async def test_fetch_stock_st_maps_flexible_text_fields(monkeypatch):
    provider = _provider(
        monkeypatch,
        {
            "stock_st": pd.DataFrame(
                [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260403",
                        "stock_name": "平安银行",
                        "type": "ST",
                        "change_reason": "risk warning",
                        "entry_date": "20260401",
                        "remove_date": "20260501",
                    }
                ]
            )
        },
    )

    rows = await provider.fetch_stock_st("20260403")

    assert rows == [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260403",
            "trade_date_dt": date(2026, 4, 3),
            "name": "平安银行",
            "st_type": "ST",
            "reason": "risk warning",
            "begin_date": "20260401",
            "end_date": "20260501",
        }
    ]


@pytest.mark.asyncio
async def test_fetch_technical_factors_packs_non_identity_columns(monkeypatch):
    provider = _provider(
        monkeypatch,
        {
            "stk_factor_pro": pd.DataFrame(
                [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260403",
                        "macd": 0.12,
                        "rsi_6": 55.5,
                        "empty": None,
                    }
                ]
            )
        },
    )

    rows = await provider.fetch_technical_factors("20260403")

    assert rows == [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260403",
            "trade_date_dt": date(2026, 4, 3),
            "factors": {
                "macd": 0.12,
                "rsi_6": 55.5,
            },
        }
    ]


@pytest.mark.asyncio
async def test_required_fact_fetchers_return_empty_for_empty_or_exception(monkeypatch):
    provider = _provider(
        monkeypatch,
        {
            "daily_basic": pd.DataFrame(),
            "stock_st": RuntimeError("permission denied"),
            "stk_factor_pro": pd.DataFrame([{"ts_code": "000001.SZ", "trade_date": ""}]),
        },
    )

    assert await provider.fetch_daily_basic("20260403") == []
    assert await provider.fetch_stock_st("20260403") == []
    assert await provider.fetch_technical_factors("20260403") == []

