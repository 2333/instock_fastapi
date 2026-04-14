from datetime import date
from decimal import Decimal

import pytest

from app.models.stock_model import Base, DailyBasic, StockST, TechnicalFactor
from app.repositories.fact_repository import FactRepository
from app.services.fact_service import FactService
from tests.conftest import async_engine_test, async_session_factory_test


async def _seed_fact_rows(session):
    session.add_all(
        [
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
            ),
            StockST(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                name="平安银行",
                st_type="ST",
                reason="示例原因",
                begin_date="20240101",
                end_date=None,
            ),
            TechnicalFactor(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                factors={"rsi_14": 56.78, "macd": 0.12},
            ),
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_fact_repository_normalizes_code_and_date_filters():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        await _seed_fact_rows(session)
        repo = FactRepository(session)

        daily_basic = await repo.get_daily_basic(code="000001", date="2024-01-02", limit=10)
        stock_st = await repo.get_stock_st(code="000001.SZ", date="20240102", limit=10)
        technical_factors = await repo.get_technical_factors(
            code="000001", date="2024-01-02", limit=10
        )

    assert daily_basic[0]["ts_code"] == "000001.SZ"
    assert daily_basic[0]["trade_date"] == "20240102"
    assert daily_basic[0]["trade_date_dt"] == date(2024, 1, 2)
    assert stock_st[0]["reason"] == "示例原因"
    assert technical_factors[0]["factors"]["rsi_14"] == 56.78

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_fact_service_returns_required_fact_rows():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        await _seed_fact_rows(session)
        service = FactService(session)

        daily_basic = await service.get_daily_basic(code="000001", date="2024-01-02", limit=10)
        stock_st = await service.get_stock_st(code="000001", date="2024-01-02", limit=10)
        technical_factors = await service.get_technical_factors(
            code="000001", date="2024-01-02", limit=10
        )

    assert daily_basic[0]["pe"] == Decimal("12.34")
    assert stock_st[0]["st_type"] == "ST"
    assert technical_factors[0]["factors"]["macd"] == 0.12

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_fact_api_exposes_required_fact_endpoints(client):
    daily_basic = await client.get(
        "/api/v1/facts/daily-basic",
        params={"code": "000001", "date": "2024-01-02"},
    )
    stock_st = await client.get(
        "/api/v1/facts/stock-st",
        params={"code": "000001", "date": "2024-01-02"},
    )
    technical_factors = await client.get(
        "/api/v1/facts/technical-factors",
        params={"code": "000001", "date": "2024-01-02"},
    )

    assert daily_basic.status_code == 200
    assert daily_basic.json()[0]["turnover_rate"] == 1.23
    assert stock_st.status_code == 200
    assert stock_st.json()[0]["reason"] == "示例原因"
    assert technical_factors.status_code == 200
    assert technical_factors.json()[0]["factors"]["rsi_14"] == 56.78
