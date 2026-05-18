import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_current_user
from app.database import get_db
from app.jobs.tasks import strategy_task
from app.main import app
from app.models.stock_model import Strategy
from app.schemas.strategy_schema import StrategyResponse

RESIDUE_MODEL_FIELDS = {
    "is_public",
    "is_official",
    "rating",
    "rating_count",
    "favorite_count",
    "comment_count",
    "backtest_count",
    "view_count",
    "tags",
    "risk_level",
    "suitable_market",
}

RESIDUE_RESPONSE_FIELDS = RESIDUE_MODEL_FIELDS | {
    "user_rating",
    "user_favorited",
}


@pytest.fixture
async def minimal_strategy_runtime():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.execute(text("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    params JSON,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME,
                    UNIQUE (user_id, name)
                )
                """))
        await conn.execute(text("""
                CREATE TABLE strategy_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    ts_code VARCHAR(20) NOT NULL,
                    trade_date VARCHAR(10) NOT NULL,
                    score NUMERIC(10, 4),
                    signal VARCHAR(20),
                    details JSON,
                    created_at DATETIME,
                    FOREIGN KEY(strategy_id) REFERENCES strategies(id) ON DELETE RESTRICT
                )
                """))
        await conn.execute(text("""
                CREATE TABLE backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    strategy_id INTEGER,
                    start_date VARCHAR(10) NOT NULL,
                    end_date VARCHAR(10) NOT NULL,
                    initial_capital NUMERIC(20, 2) NOT NULL,
                    created_at DATETIME,
                    FOREIGN KEY(strategy_id) REFERENCES strategies(id) ON DELETE RESTRICT
                )
                """))

    current_user = SimpleNamespace(
        id=7,
        username="alice",
        email="alice@example.com",
        is_active=True,
        is_superuser=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {
            "client": client,
            "session_factory": session_factory,
            "current_user": current_user,
        }

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    await engine.dispose()


def test_strategy_model_removes_social_and_library_residue_columns():
    assert RESIDUE_MODEL_FIELDS.isdisjoint(Strategy.__table__.columns.keys())


def test_strategy_response_schema_removes_social_and_library_residue_fields():
    assert RESIDUE_RESPONSE_FIELDS.isdisjoint(StrategyResponse.model_fields)


@pytest.mark.asyncio
async def test_strategy_router_crud_uses_runtime_safe_strategy_columns(minimal_strategy_runtime):
    client = minimal_strategy_runtime["client"]
    session_factory = minimal_strategy_runtime["session_factory"]

    create_response = await client.post(
        "/api/v1/strategies/my",
        json={
            "name": "ma_crossover-600519",
            "description": "saved from backtest",
            "params": {
                "strategy_type": "ma_crossover",
                "stock_code": "600519",
                "strategy_params": {"fast_ma": 5, "slow_ma": 20},
            },
            "is_active": True,
        },
    )
    selection_response = await client.post(
        "/api/v1/strategies/my/from-selection",
        json={
            "name": "筛选策略-002",
            "description": "通过筛选条件保存",
            "params": {
                "selection_filters": {"changeMin": 1, "macdBullish": True},
                "selection_scope": {"market": "sh", "limit": 120},
                "entry_rules": {"mode": "screening_match"},
                "exit_rules": {"mode": "configurable", "rules": []},
            },
            "is_active": True,
        },
    )
    list_response = await client.get("/api/v1/strategies/my")
    created_id = create_response.json()["id"]
    update_response = await client.put(
        f"/api/v1/strategies/my/{created_id}",
        json={
            "params": {
                "strategy_type": "rsi_oversold",
                "stock_code": "000001",
                "period": "1y",
                "initial_capital": 200000,
                "strategy_params": {"rsi_period": 14, "oversold_level": 30},
            }
        },
    )
    selection_id = selection_response.json()["id"]
    delete_response = await client.delete(f"/api/v1/strategies/my/{selection_id}")

    assert create_response.status_code == 200
    assert selection_response.status_code == 200
    assert list_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert sorted(item["name"] for item in list_response.json()) == [
        "ma_crossover-600519",
        "筛选策略-002",
    ]
    assert create_response.json()["params"]["template_name"] == "ma_crossover"
    assert selection_response.json()["params"]["source"] == "selection"
    assert update_response.json()["params"]["template_name"] == "rsi_oversold"

    async with session_factory() as session:
        remaining_count = (
            await session.execute(text("SELECT COUNT(*) FROM strategies"))
        ).scalar_one()
        updated_row = (
            (
                await session.execute(
                    text("SELECT name, params, is_active FROM strategies WHERE id = :strategy_id"),
                    {"strategy_id": created_id},
                )
            )
            .mappings()
            .one()
        )

    updated_params = updated_row["params"]
    if isinstance(updated_params, str):
        updated_params = json.loads(updated_params)

    assert remaining_count == 1
    assert updated_row["name"] == "ma_crossover-600519"
    assert updated_params["template_name"] == "rsi_oversold"
    assert updated_row["is_active"] == 1


@pytest.mark.asyncio
async def test_strategy_delete_removes_child_results_and_detaches_backtests(
    minimal_strategy_runtime,
):
    client = minimal_strategy_runtime["client"]
    session_factory = minimal_strategy_runtime["session_factory"]

    create_response = await client.post(
        "/api/v1/strategies/my",
        json={"name": "delete-me", "description": "with children"},
    )
    strategy_id = create_response.json()["id"]

    async with session_factory() as session:
        await session.execute(
            text("""
                INSERT INTO strategy_results (
                    strategy_id, ts_code, trade_date, score, signal, details
                ) VALUES (
                    :strategy_id, :ts_code, :trade_date, :score, :signal, :details
                )
                """),
            {
                "strategy_id": strategy_id,
                "ts_code": "000001.SZ",
                "trade_date": "20240102",
                "score": 12.5,
                "signal": "buy",
                "details": json.dumps({"source": "test"}),
            },
        )
        await session.execute(
            text("""
                INSERT INTO backtest_results (
                    user_id, name, strategy_id, start_date, end_date, initial_capital
                ) VALUES (
                    :user_id, :name, :strategy_id, :start_date, :end_date, :initial_capital
                )
                """),
            {
                "user_id": 7,
                "name": "historical backtest",
                "strategy_id": strategy_id,
                "start_date": "20240101",
                "end_date": "20240131",
                "initial_capital": 100000,
            },
        )
        await session.commit()

    delete_response = await client.delete(f"/api/v1/strategies/my/{strategy_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"

    async with session_factory() as session:
        strategy_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM strategies WHERE id = :strategy_id"),
                {"strategy_id": strategy_id},
            )
        ).scalar_one()
        child_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM strategy_results WHERE strategy_id = :strategy_id"),
                {"strategy_id": strategy_id},
            )
        ).scalar_one()
        detached_backtest_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM backtest_results WHERE strategy_id IS NULL")
            )
        ).scalar_one()
        remaining_backtest_fk_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM backtest_results WHERE strategy_id = :strategy_id"),
                {"strategy_id": strategy_id},
            )
        ).scalar_one()

    assert strategy_count == 0
    assert child_count == 0
    assert detached_backtest_count == 1
    assert remaining_backtest_fk_count == 0


@pytest.mark.asyncio
async def test_strategy_update_rename_duplicate_returns_controlled_400(minimal_strategy_runtime):
    client = minimal_strategy_runtime["client"]

    first_response = await client.post(
        "/api/v1/strategies/my",
        json={"name": "alpha", "description": "first"},
    )
    second_response = await client.post(
        "/api/v1/strategies/my",
        json={"name": "beta", "description": "second"},
    )

    update_response = await client.put(
        f"/api/v1/strategies/my/{first_response.json()['id']}",
        json={"name": second_response.json()["name"]},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert update_response.status_code == 400
    assert update_response.json()["detail"] == "策略名称已存在"


@pytest.mark.asyncio
async def test_strategy_task_does_not_bootstrap_default_strategy_rows(minimal_strategy_runtime):
    session_factory = minimal_strategy_runtime["session_factory"]

    with (
        patch("app.jobs.tasks.strategy_task.async_session_factory", session_factory),
        patch(
            "app.jobs.tasks.strategy_task.is_trading_day",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.jobs.tasks.strategy_task.should_skip_market_task",
            return_value=False,
        ),
        patch(
            "app.jobs.tasks.strategy_task.run_strategy",
            new=AsyncMock(return_value=[]),
        ) as run_strategy_mock,
    ):
        await strategy_task.run()

    async with session_factory() as session:
        strategy_count = (
            await session.execute(text("SELECT COUNT(*) FROM strategies"))
        ).scalar_one()

    assert strategy_count == 0
    run_strategy_mock.assert_not_awaited()
