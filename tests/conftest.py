import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_async_session, async_engine
from app.models.stock_model import Base


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


@pytest.fixture(scope="function")
async def client():
    async with async_session_factory_test() as session:
        async with async_engine_test.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

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
