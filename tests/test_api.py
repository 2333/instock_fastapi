import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import client, sample_stock, sample_daily_bar


class TestStocksAPI:
    async def test_get_stocks(self, client):
        response = await client.get("/api/v1/stocks")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    async def test_get_stock_by_ts_code(self, client):
        response = await client.get("/api/v1/stocks/000001.SZ")
        assert response.status_code == 200
        data = response.json()
        assert data["ts_code"] == "000001.SZ"


class TestDailyBarsAPI:
    async def test_get_daily_bars(self, client):
        response = await client.get(
            "/api/v1/stocks/daily",
            params={
                "ts_code": "000001.SZ",
                "start_date": "20240101",
                "end_date": "20240131",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data


class TestIndicatorsAPI:
    async def test_get_indicators(self, client):
        response = await client.get(
            "/api/v1/indicators",
            params={"ts_code": "000001.SZ", "trade_date": "20240102"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestHealthCheck:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
