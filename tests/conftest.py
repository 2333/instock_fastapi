import os
import sys
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
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
from app.models.stock_model import Base, DailyBar, Indicator, Stock


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
