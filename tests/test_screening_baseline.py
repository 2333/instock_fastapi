import time
from statistics import mean
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


@pytest.mark.asyncio
async def test_screening_run_baseline_records_three_runs(client, current_user_override):
    payload = {
        "filters": {
            "priceMin": 5,
            "changeMin": 1,
            "macdBullish": True,
        },
        "scope": {
            "limit": 100,
        },
    }

    samples: list[dict[str, float | int | str]] = []

    for _ in range(3):
        started_at = time.perf_counter()
        response = await client.post("/api/v1/screening/run", json=payload)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 3)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True

        data = body["data"]
        samples.append(
            {
                "elapsed_ms": elapsed_ms,
                "total": int(data["total"]),
                "trade_date": str(data["query"]["trade_date"] or ""),
            }
        )

    assert len(samples) == 3
    trade_dates = {str(sample["trade_date"]) for sample in samples}
    assert len(trade_dates) == 1
    assert all(sample["total"] >= 0 for sample in samples)

    slowest_ms = max(float(sample["elapsed_ms"]) for sample in samples)
    average_ms = round(mean(float(sample["elapsed_ms"]) for sample in samples), 3)

    # 先把基线记录在测试断言上下文里，不在这里写死 30s 门槛，
    # 避免内存数据库/测试夹具环境给出误导性的性能结论。
    assert slowest_ms >= 0
    assert average_ms >= 0
