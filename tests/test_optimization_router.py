from types import SimpleNamespace

import pytest

from app.core.dependencies import get_current_user
from app.main import app


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


def optimization_payload():
    return {
        "name": "router smoke",
        "base_params": {
            "stock_code": "000001",
            "start_date": "20240101",
            "end_date": "20240131",
            "strategy": "ma_crossover",
            "strategy_params": {"fast_ma": 5, "slow_ma": 20},
        },
        "parameter_space": {
            "fast_ma": {"type": "int", "min": 3, "max": 5},
            "slow_ma": {"type": "int", "min": 10, "max": 12},
        },
        "objective_metric": "sharpe_ratio",
        "trial_count": 2,
        "random_seed": 7,
    }


@pytest.mark.asyncio
async def test_optimization_job_auto_start_schedules_task_by_default(
    client,
    current_user_override,
    monkeypatch,
):
    scheduled_job_ids = []

    def fake_schedule_optimization_job(job_id):
        scheduled_job_ids.append(job_id)
        return SimpleNamespace(done=lambda: False)

    monkeypatch.setattr(
        "app.api.routers.optimization_router.schedule_optimization_job",
        fake_schedule_optimization_job,
    )

    response = await client.post("/api/v1/optimization/jobs", json=optimization_payload())

    assert response.status_code == 201
    created = response.json()["data"]
    assert created["status"] == "pending"
    assert scheduled_job_ids == [created["id"]]


@pytest.mark.asyncio
async def test_optimization_job_crud_endpoints(client, current_user_override):
    create_response = await client.post(
        "/api/v1/optimization/jobs",
        params={"auto_start": "false"},
        json=optimization_payload(),
    )
    assert create_response.status_code == 201
    created = create_response.json()["data"]
    job_id = created["id"]
    assert created["status"] == "pending"
    assert created["objective_direction"] == "maximize"

    list_response = await client.get("/api/v1/optimization/jobs")
    assert list_response.status_code == 200
    assert list_response.json()["data"][0]["id"] == job_id

    detail_response = await client.get(f"/api/v1/optimization/jobs/{job_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["base_params"]["stock_code"] == "000001"

    trials_response = await client.get(f"/api/v1/optimization/jobs/{job_id}/trials")
    assert trials_response.status_code == 200
    assert trials_response.json()["data"] == []

    best_response = await client.get(f"/api/v1/optimization/jobs/{job_id}/best")
    assert best_response.status_code == 200
    assert best_response.json()["data"]["best_parameters"] is None

    cancel_response = await client.delete(f"/api/v1/optimization/jobs/{job_id}")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_optimization_job_rejects_invalid_space(client, current_user_override):
    payload = optimization_payload()
    payload["parameter_space"] = {"fast_ma": []}

    response = await client.post(
        "/api/v1/optimization/jobs",
        params={"auto_start": "false"},
        json=payload,
    )

    assert response.status_code == 422
    assert "choices cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_optimization_job_owner_isolation_returns_404(client, current_user_override):
    create_response = await client.post(
        "/api/v1/optimization/jobs",
        params={"auto_start": "false"},
        json=optimization_payload(),
    )
    job_id = create_response.json()["data"]["id"]

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=8,
        username="bob",
        email="bob@example.com",
        is_active=True,
        is_superuser=False,
    )

    response = await client.get(f"/api/v1/optimization/jobs/{job_id}")

    assert response.status_code == 404
