from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.jobs.scheduler import FETCH_FUND_FLOW_TIME, should_recover_market_job
from tests.conftest import async_session_factory_test


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
        assert (
            data["validation_context"]["pattern_annotations"][0]["context"]["signal"] == "bullish"
        )


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

    async def test_get_stock_detail_reports_adjust_fallback_when_requested_data_missing(
        self, client
    ):
        with patch(
            "app.services.stock_service.StockService._fetch_adjusted_bars",
            new=AsyncMock(return_value=[]),
        ):
            response = await client.get(
                "/api/v1/stocks/000001.SZ",
                params={
                    "start_date": "20240101",
                    "end_date": "20240131",
                    "adjust": "qfq",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["adjust_requested"] == "qfq"
        assert data["adjust_applied"] == "bfq"
        assert data["adjust_note"] == "requested_adjust_data_unavailable_fallback_to_bfq"
        assert data["data_freshness"]["price_current"] is True
        assert data["data_freshness"]["indicator_current"] is True


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


class TestMarketTaskHealthAPI:
    async def test_get_task_health_exposes_stale_dataset_and_active_alerts(self, client):
        async with async_session_factory_test() as session:
            await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS data_fetch_audit (
                      task_name VARCHAR(64) NOT NULL,
                      entity_type VARCHAR(64) NOT NULL,
                      entity_key VARCHAR(128) NOT NULL,
                      trade_date VARCHAR(10) NOT NULL DEFAULT '',
                      status VARCHAR(32) NOT NULL,
                      source VARCHAR(32) NULL,
                      note TEXT NULL,
                      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (task_name, entity_type, entity_key, trade_date)
                    )
                """))
            await session.execute(text("DELETE FROM data_fetch_audit"))
            await session.execute(text("DELETE FROM fund_flows"))
            await session.execute(text("""
                    INSERT INTO data_fetch_audit (
                        task_name, entity_type, entity_key, trade_date, status, source, note, updated_at
                    ) VALUES
                        ('fetch_fund_flow', 'stock_fund_flow', 'ALL', '20240101', 'needs_fallback', 'tushare', 'primary source returned empty', '2024-01-02 10:00:00'),
                        ('fetch_market_reference', 'stock_top', 'ALL', '20240102', 'done', 'tushare', 'rows=12', '2024-01-02 11:00:00')
                """))
            await session.execute(text("""
                    INSERT INTO fund_flows (ts_code, trade_date, created_at)
                    VALUES ('000001.SZ', '20240101', '2024-01-02 10:00:00')
                """))
            await session.commit()

        response = await client.get("/api/v1/market/task-health")

        assert response.status_code == 200
        data = response.json()
        assert data["baseline_trade_date"] == "20240102"
        assert data["alert_count"] == 1
        assert data["alerts"][0]["task_name"] == "fetch_fund_flow"
        assert data["alerts"][0]["status"] == "needs_fallback"
        assert next(item for item in data["datasets"] if item["dataset"] == "fund_flows") == {
            "dataset": "fund_flows",
            "latest_trade_date": "20240101",
            "baseline_trade_date": "20240102",
            "current": False,
        }

    async def test_task_health_staleness_matches_scheduler_recovery_decision(self, client):
        async with async_session_factory_test() as session:
            await session.execute(text("""
                    CREATE TABLE IF NOT EXISTS data_fetch_audit (
                      task_name VARCHAR(64) NOT NULL,
                      entity_type VARCHAR(64) NOT NULL,
                      entity_key VARCHAR(128) NOT NULL,
                      trade_date VARCHAR(10) NOT NULL DEFAULT '',
                      status VARCHAR(32) NOT NULL,
                      source VARCHAR(32) NULL,
                      note TEXT NULL,
                      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (task_name, entity_type, entity_key, trade_date)
                    )
                """))
            await session.execute(text("DELETE FROM data_fetch_audit"))
            await session.execute(text("DELETE FROM fund_flows"))
            await session.execute(text("""
                    INSERT INTO data_fetch_audit (
                        task_name, entity_type, entity_key, trade_date, status, source, note, updated_at
                    ) VALUES (
                        'fetch_fund_flow', 'stock_fund_flow', 'ALL', '20240101',
                        'needs_fallback', 'tushare', 'primary source returned empty', '2024-01-02 16:05:00'
                    )
                """))
            await session.execute(text("""
                    INSERT INTO fund_flows (ts_code, trade_date, created_at)
                    VALUES ('000001.SZ', '20240101', '2024-01-02 16:05:00')
                """))
            await session.commit()

        response = await client.get("/api/v1/market/task-health")

        assert response.status_code == 200
        data = response.json()
        fund_flow_dataset = next(
            item for item in data["datasets"] if item["dataset"] == "fund_flows"
        )

        latest_trade_dates = [
            item["latest_trade_date"]
            for item in data["datasets"]
            if item["dataset"] == "fund_flows"
        ]
        should_recover = should_recover_market_job(
            now=datetime(2024, 1, 2, 16, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
            scheduled_time=FETCH_FUND_FLOW_TIME,
            today_trade_date=data["baseline_trade_date"],
            latest_trade_dates=latest_trade_dates,
            today_is_trading_day=True,
        )

        assert data["baseline_trade_date"] == "20240102"
        assert fund_flow_dataset["latest_trade_date"] == "20240101"
        assert fund_flow_dataset["current"] is False
        assert data["alerts"][0]["task_name"] == "fetch_fund_flow"
        assert should_recover is True
