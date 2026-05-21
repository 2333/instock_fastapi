from types import SimpleNamespace

import pytest

from app.core.dependencies import get_current_user
from app.main import app
from app.services.optimization_service import OptimizationService
from tests.conftest import async_session_factory_test


@pytest.fixture
def current_user_override():
    current_user = SimpleNamespace(
        id=7,
        username="alice",
        email="alice@example.com",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: current_user
    yield current_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_optimization_api_smoke_create_run_best_and_backtest_replay(
    client,
    current_user_override,
):
    payload = {
        "name": "m5 smoke",
        "base_params": {
            "stock_code": "000001",
            "start_date": "20240101",
            "end_date": "20240131",
            "strategy": "ma_crossover",
            "strategy_params": {"fast_ma": 5, "slow_ma": 20},
            "initial_capital": 100000,
        },
        "parameter_space": {
            "fast_ma": {"type": "int", "min": 3, "max": 4},
            "slow_ma": {"type": "int", "min": 10, "max": 11},
        },
        "objective_metric": "sharpe_ratio",
        "trial_count": 2,
        "random_seed": 9,
    }

    create_response = await client.post(
        "/api/v1/optimization/jobs",
        params={"auto_start": "false"},
        json=payload,
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["data"]["id"]

    async with async_session_factory_test() as session:
        await OptimizationService(session).run_job(job_id=job_id)

    detail_response = await client.get(f"/api/v1/optimization/jobs/{job_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["status"] == "completed"

    trials_response = await client.get(f"/api/v1/optimization/jobs/{job_id}/trials")
    assert trials_response.status_code == 200
    assert len(trials_response.json()["data"]) == 2

    best_response = await client.get(f"/api/v1/optimization/jobs/{job_id}/best")
    assert best_response.status_code == 200
    backtest_params = best_response.json()["data"]["backtest_params"]
    assert backtest_params["strategy"] == "ma_crossover"
    assert "fast_ma" in backtest_params["strategy_params"]

    replay_response = await client.post("/api/v1/backtest", json=backtest_params)
    assert replay_response.status_code == 200
    assert replay_response.json()["status"] == "completed"
