class TestStocksAPI:
    async def test_get_stocks(self, client):
        response = await client.get("/api/v1/stocks")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_stock_by_ts_code(self, client):
        response = await client.get(
            "/api/v1/stocks/000001.SZ",
            params={"start_date": "20240102", "end_date": "20240131"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ts_code"] == "000001.SZ"
        assert len(data["bars"]) == 1
        assert data["latest_trade_date"] == "20240102"
        assert data["latest_bar"]["close"] == 10.6
        assert data["data_freshness"]["indicator_current"] is True
        assert data["latest_indicator_snapshot"]["values"]["rsi"] == 56.78
        assert data["recent_patterns"]["latest_hits"][0]["pattern_name"] == "HAMMER"
        assert data["validation_context"]["pattern_annotations"][0]["context"]["signal"] == "bullish"


class TestDailyBarsAPI:
    async def test_get_daily_bars(self, client):
        response = await client.get(
            "/api/v1/stocks/000001.SZ",
            params={
                "start_date": "20240101",
                "end_date": "20240131",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "bars" in data
        assert len(data["bars"]) == 1


class TestInfoAPI:
    async def test_api_info(self, client):
        response = await client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "InStock API"


class TestHealthCheck:
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
