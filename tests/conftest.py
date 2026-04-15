import os
import sys
from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-characters"
os.environ["DEBUG"] = "false"
os.environ.setdefault("CRAWLER_PROXY_ENABLED", "false")

from app.database import get_db
from app.main import app
from app.models.stock_model import (
    Base,
    DailyBar,
    DailyBasic,
    Indicator,
    Pattern,
    Stock,
    StockST,
    TechnicalFactor,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_element, _compiler, **_kwargs):
    return "JSON"


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async_engine_test = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


async_session_factory_test = async_sessionmaker(
    bind=async_engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with async_session_factory_test() as session:
        yield session


@pytest.fixture(scope="function")
async def client():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        for table in (
            "technical_factors",
            "stock_st",
            "daily_basic",
            "patterns",
            "indicators",
            "daily_bars",
            "stocks",
        ):
            await session.execute(text(f"DELETE FROM {table}"))

        session.add(
            Stock(
                ts_code="000001.SZ",
                symbol="000001",
                name="平安银行",
                area="深圳",
                industry="银行",
                market="主板",
                exchange="SZSE",
                list_status="L",
                is_etf=False,
            )
        )
        session.add(
            DailyBar(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=None,
                open=Decimal("10.50"),
                high=Decimal("10.80"),
                low=Decimal("10.30"),
                close=Decimal("10.60"),
                pre_close=Decimal("10.40"),
                change=Decimal("0.20"),
                pct_chg=Decimal("1.92"),
                vol=Decimal("50000000"),
                amount=Decimal("525000000"),
            )
        )
        session.add(
            Indicator(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=None,
                indicator_name="RSI",
                indicator_value=Decimal("56.78"),
            )
        )
        session.add(
            Indicator(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=None,
                indicator_name="MACD",
                indicator_value=Decimal("0.12"),
            )
        )
        session.add(
            Pattern(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                pattern_name="HAMMER",
                pattern_type="reversal",
                confidence=Decimal("0.91"),
            )
        )
        session.add(
            DailyBasic(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                turnover_rate=Decimal("1.23"),
                turnover_rate_f=Decimal("0.98"),
                volume_ratio=Decimal("1.11"),
                pe=Decimal("12.34"),
                pe_ttm=Decimal("11.22"),
                pb=Decimal("1.56"),
                ps=Decimal("2.34"),
                ps_ttm=Decimal("2.20"),
                dv_ratio=Decimal("0.85"),
                dv_ttm=Decimal("0.72"),
                total_share=Decimal("1000000"),
                float_share=Decimal("800000"),
                free_share=Decimal("600000"),
                total_mv=Decimal("123456789"),
                circ_mv=Decimal("98765432"),
            )
        )
        session.add(
            StockST(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                name="平安银行",
                st_type="ST",
                reason="示例原因",
                begin_date="20240101",
                end_date=None,
            )
        )
        session.add(
            TechnicalFactor(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                factors={"rsi_14": 56.78, "macd": 0.12},
            )
        )
        await session.commit()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def sample_stock():
    return {
        "ts_code": "000001.SZ",
        "symbol": "000001",
        "name": "平安银行",
        "area": "深圳",
        "industry": "银行",
        "market": "主板",
        "exchange": "SZSE",
        "list_status": "L",
    }


@pytest.fixture
def sample_daily_bar():
    return {
        "ts_code": "000001.SZ",
        "trade_date": "20240102",
        "open": Decimal("10.50"),
        "high": Decimal("10.80"),
        "low": Decimal("10.30"),
        "close": Decimal("10.60"),
        "pre_close": Decimal("10.40"),
        "change": Decimal("0.20"),
        "pct_chg": Decimal("1.92"),
        "vol": Decimal("50000000"),
        "amount": Decimal("525000000"),
    }
