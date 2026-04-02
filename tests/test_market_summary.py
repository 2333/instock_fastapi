from unittest.mock import AsyncMock, Mock

import pytest

from app.services.market_data_service import MarketDataService


def make_result(*, row=None, rows=None):
    result = Mock()
    result.fetchone.return_value = row
    result.fetchall.return_value = [Mock(_mapping=item) for item in (rows or [])]
    return result


@pytest.mark.asyncio
async def test_market_data_service_get_summary_builds_breadth_and_proxy_indices():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(row=("20240102",)),
            make_result(
                rows=[
                    {
                        "symbol": "600000",
                        "name": "浦发银行",
                        "market": "主板",
                        "exchange": "SSE",
                        "is_etf": False,
                        "close": 10.0,
                        "pct_chg": 10.0,
                        "trade_date": "20240102",
                    },
                    {
                        "symbol": "000001",
                        "name": "平安银行",
                        "market": "主板",
                        "exchange": "SZSE",
                        "is_etf": False,
                        "close": 12.0,
                        "pct_chg": -10.0,
                        "trade_date": "20240102",
                    },
                    {
                        "symbol": "300001",
                        "name": "特锐德",
                        "market": "创业板",
                        "exchange": "SZSE",
                        "is_etf": False,
                        "close": 20.0,
                        "pct_chg": 19.9,
                        "trade_date": "20240102",
                    },
                    {
                        "symbol": "688001",
                        "name": "华兴源创",
                        "market": "科创板",
                        "exchange": "SSE",
                        "is_etf": False,
                        "close": 30.0,
                        "pct_chg": 0.0,
                        "trade_date": "20240102",
                    },
                ]
            ),
        ]
    )

    service = MarketDataService(db)
    summary = await service.get_summary()

    assert summary["trade_date"] == "20240102"
    assert summary["total_count"] == 4
    assert summary["up_count"] == 2
    assert summary["down_count"] == 1
    assert summary["flat_count"] == 1
    assert summary["limit_up_count"] == 2
    assert summary["limit_down_count"] == 1
    assert "上涨 2 只" in summary["sentiment_summary"]
    assert len(summary["indices"]) == 3
    assert summary["indices"][0]["code"] == "sh_index"
    assert summary["indices"][0]["source"] == "proxy"
    assert summary["indices"][0]["constituent_count"] == 2
    assert summary["indices"][1]["code"] == "sz_index"
    assert summary["indices"][1]["constituent_count"] == 1
    assert summary["indices"][2]["code"] == "chinext_index"
    assert summary["indices"][2]["constituent_count"] == 1


@pytest.mark.asyncio
async def test_market_summary_endpoint_returns_schema(client):
    response = await client.get("/api/v1/market/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trade_date"] == "20240102"
    assert payload["total_count"] == 1
    assert payload["indices"][0]["code"] in {"sh_index", "sz_index"}
    assert len(payload["indices"]) == 3
    assert "sentiment_summary" in payload
