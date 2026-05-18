from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.core.dependencies import get_current_user
from app.jobs import scheduler as scheduler_module
from app.jobs.tasks import alert_subscription_task, pattern_task
from app.jobs.tasks.fetch_audit import upsert_fetch_audit
from app.main import app
from app.models.stock_model import DailyBar, Pattern, Stock
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


async def _seed_pattern_task_bars(*, trade_date: date = date(2024, 1, 2)) -> None:
    start_date = trade_date - timedelta(days=29)
    async with async_session_factory_test() as session:
        await session.execute(text("DELETE FROM daily_bars WHERE ts_code = '000001.SZ'"))
        await session.execute(text("DELETE FROM patterns WHERE ts_code = '000001.SZ'"))
        for index in range(30):
            current_date = start_date + timedelta(days=index)
            close = Decimal("10.00") + Decimal(index) / Decimal("10")
            session.add(
                DailyBar(
                    ts_code="000001.SZ",
                    trade_date=current_date.strftime("%Y%m%d"),
                    trade_date_dt=current_date,
                    open=close,
                    high=close + Decimal("0.20"),
                    low=close - Decimal("0.20"),
                    close=close,
                    pre_close=close - Decimal("0.05"),
                    change=Decimal("0.05"),
                    pct_chg=Decimal("0.50"),
                    vol=Decimal("1000000"),
                    amount=Decimal("10000000"),
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_alert_subscription_create_run_and_dedupe_notifications(
    client, current_user_override
):
    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "RSI baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    assert create_condition.status_code == 200
    condition_id = create_condition.json()["id"]
    definition_version = create_condition.json()["definition_version"]
    definition_hash = create_condition.json()["definition_hash"]

    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={
            "selection_condition_id": condition_id,
            "name": "收盘后观察",
            "cooldown_trade_days": 1,
        },
    )
    assert create_subscription.status_code == 200
    assert create_subscription.json()["data"]["definition_version"] == definition_version
    assert create_subscription.json()["data"]["definition_hash"] == definition_hash
    subscription_id = create_subscription.json()["data"]["id"]

    first_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert first_run.status_code == 200
    assert first_run.json()["data"]["run"]["match_count"] == 1
    assert first_run.json()["data"]["run"]["new_match_count"] == 1
    assert len(first_run.json()["data"]["hits"]) == 1
    assert first_run.json()["data"]["notification"]["payload"]["new_match_count"] == 1
    assert first_run.json()["data"]["notification"]["notification_type"] == "alert_summary"
    assert first_run.json()["data"]["notification"]["dedupe_key"]
    first_run_id = first_run.json()["data"]["run"]["id"]

    second_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert second_run.status_code == 200
    assert second_run.json()["data"]["run"]["id"] == first_run_id

    notifications = await client.get("/api/v1/notifications")
    assert notifications.status_code == 200
    assert len(notifications.json()["data"]) == 1
    assert notifications.json()["data"][0]["subscription_id"] == subscription_id


@pytest.mark.asyncio
async def test_alert_subscription_becomes_stale_after_saved_screener_changes(
    client, current_user_override
):
    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "BOLL baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]

    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )
    subscription_id = create_subscription.json()["data"]["id"]

    update_condition = await client.put(
        f"/api/v1/selection/my-conditions/{condition_id}",
        json={
            "name": "BOLL baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "rsiMin",
                            "params": {"value": 40, "period": 14},
                        }
                    ],
                },
            },
        },
    )
    assert update_condition.status_code == 200
    assert update_condition.json()["definition_version"] == 2

    subscriptions = await client.get("/api/v1/alerts/subscriptions")
    assert subscriptions.status_code == 200
    assert subscriptions.json()["data"][0]["status"] == "stale"

    stale_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert stale_run.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_subscription_returns_business_error(client, current_user_override):
    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Duplicate guard",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]

    first = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )
    second = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )

    assert first.status_code == 200
    assert second.status_code == 400
    assert "已存在订阅" in second.json()["detail"]


@pytest.mark.asyncio
async def test_notifications_can_be_marked_read(client, current_user_override):
    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Digest baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]
    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )
    subscription_id = create_subscription.json()["data"]["id"]
    await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )

    notifications = await client.get("/api/v1/notifications")
    notification_id = notifications.json()["data"][0]["id"]
    mark_read = await client.patch(
        f"/api/v1/notifications/{notification_id}",
        json={"is_read": True},
    )
    assert mark_read.status_code == 200
    assert mark_read.json()["data"][0]["is_read"] is True


@pytest.mark.asyncio
async def test_historical_manual_trigger_compares_against_previous_trade_date_only(
    client, current_user_override
):
    async with async_session_factory_test() as session:
        session.add(
            DailyBar(
                ts_code="000001.SZ",
                trade_date="20240103",
                trade_date_dt=None,
                open=Decimal("10.60"),
                high=Decimal("10.90"),
                low=Decimal("10.50"),
                close=Decimal("10.80"),
                pre_close=Decimal("10.60"),
                change=Decimal("0.20"),
                pct_chg=Decimal("1.89"),
                vol=Decimal("40000000"),
                amount=Decimal("420000000"),
            )
        )
        await session.commit()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "History baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]
    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )
    subscription_id = create_subscription.json()["data"]["id"]

    latest_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240103"},
    )
    assert latest_run.status_code == 200
    assert latest_run.json()["data"]["run"]["new_match_count"] == 1

    historical_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert historical_run.status_code == 200
    assert historical_run.json()["data"]["run"]["trade_date"] == "20240102"
    assert historical_run.json()["data"]["run"]["new_match_count"] == 1


@pytest.mark.asyncio
async def test_alert_subscription_cooldown_suppresses_new_digest_notification(
    client, current_user_override
):
    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000002.SZ",
                symbol="000002",
                name="万科A",
                area="深圳",
                industry="地产",
                market="主板",
                exchange="SZSE",
                list_status="L",
                is_etf=False,
            )
        )
        for ts_code, trade_date, close in (
            ("000001.SZ", "20240103", "10.80"),
            ("000002.SZ", "20240103", "20.80"),
        ):
            session.add(
                DailyBar(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    trade_date_dt=None,
                    open=Decimal(close),
                    high=Decimal(close),
                    low=Decimal(close),
                    close=Decimal(close),
                    pre_close=Decimal("10.60"),
                    change=Decimal("0.20"),
                    pct_chg=Decimal("1.89"),
                    vol=Decimal("40000000"),
                    amount=Decimal("420000000"),
                )
            )
        await session.commit()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Cooldown baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]
    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id, "cooldown_trade_days": 2},
    )
    subscription_id = create_subscription.json()["data"]["id"]

    first_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert first_run.status_code == 200
    assert first_run.json()["data"]["notification"] is not None

    cooldown_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240103"},
    )
    assert cooldown_run.status_code == 200
    assert cooldown_run.json()["data"]["run"]["new_match_count"] == 1
    assert cooldown_run.json()["data"]["run"]["summary"]["notification_suppressed"] is True
    assert cooldown_run.json()["data"]["notification"] is None

    notifications = await client.get("/api/v1/notifications")
    assert len(notifications.json()["data"]) == 1


@pytest.mark.asyncio
async def test_post_close_task_runs_active_subscriptions(
    client, current_user_override, monkeypatch
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Post close baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "completed"
    assert summary["trade_date"] == "20240102"
    assert summary["attempted"] == 1
    assert summary["completed"] == 1
    assert summary["failed"] == 0

    notifications = await client.get("/api/v1/notifications")
    assert len(notifications.json()["data"]) == 1


@pytest.mark.asyncio
async def test_post_close_task_skips_subscription_already_run_for_trade_date(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "No duplicate batch run",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]
    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )
    subscription_id = create_subscription.json()["data"]["id"]

    manual_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert manual_run.status_code == 200

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "completed"
    assert summary["attempted"] == 0
    assert summary["completed"] == 0

    notifications = await client.get("/api/v1/notifications")
    assert len(notifications.json()["data"]) == 1


@pytest.mark.asyncio
async def test_post_close_task_skips_non_trading_day(client, monkeypatch):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)
    monkeypatch.setattr(alert_subscription_task, "current_market_date", lambda: date(2024, 1, 6))

    async def fake_is_trading_day(*, target_date):
        return False

    monkeypatch.setattr(alert_subscription_task, "is_trading_day", fake_is_trading_day)

    summary = await alert_subscription_task.run()

    assert summary["status"] == "skipped"
    assert summary["reason"] == "non_trading_day"
    assert summary["attempted"] == 0


@pytest.mark.asyncio
async def test_post_close_task_skips_when_target_trade_date_has_no_daily_data(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "No stale date fallback",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240103")

    assert summary["status"] == "skipped"
    assert summary["reason"] == "trade_date_not_ready"
    assert summary["attempted"] == 0

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_post_close_task_skips_when_target_trade_date_has_partial_gap(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000002.SZ",
                symbol="000002",
                name="万科A",
                area="深圳",
                industry="地产",
                market="主板",
                exchange="SZSE",
                list_status="L",
                is_etf=False,
            )
        )
        await session.commit()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Partial gap guard",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "skipped"
    assert summary["reason"] == "trade_date_partial_gap"
    assert summary["coverage"]["expected_count"] == 2
    assert summary["coverage"]["covered_count"] == 1

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_post_close_task_skips_pattern_subscription_when_pattern_audit_missing(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    async with async_session_factory_test() as session:
        session.add(
            DailyBar(
                ts_code="000001.SZ",
                trade_date="20240103",
                trade_date_dt=None,
                open=Decimal("10.60"),
                high=Decimal("10.90"),
                low=Decimal("10.50"),
                close=Decimal("10.80"),
                pre_close=Decimal("10.60"),
                change=Decimal("0.20"),
                pct_chg=Decimal("1.89"),
                vol=Decimal("40000000"),
                amount=Decimal("420000000"),
            )
        )
        await session.commit()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Pattern readiness missing",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "pattern",
                            "params": {"value": "HAMMER"},
                        }
                    ],
                },
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240103")

    assert summary["status"] == "skipped"
    assert summary["reason"] == "patterns_audit_missing"
    assert summary["patterns_status"]["reason"] == "patterns_audit_missing"
    assert summary["attempted"] == 0

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_post_close_task_runs_pattern_subscription_after_zero_hit_evaluation(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    async with async_session_factory_test() as session:
        await upsert_fetch_audit(
            session,
            task_name="pattern_recognition",
            entity_type="trade_date",
            entity_key="ALL",
            trade_date="20240102",
            status="done",
            source="local",
            note=(
                "expected=1; evaluated=1; skipped_insufficient_history=0; "
                "failed=0; matched_stocks=0; patterns=0"
            ),
        )
        await session.commit()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Pattern readiness zero-hit",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "pattern",
                            "params": {"value": "DOJI"},
                        }
                    ],
                },
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "completed"
    assert summary["attempted"] == 1
    assert summary["completed"] == 1

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_post_close_task_rejects_incomplete_pattern_audit_metrics(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)

    async with async_session_factory_test() as session:
        await upsert_fetch_audit(
            session,
            task_name="pattern_recognition",
            entity_type="trade_date",
            entity_key="ALL",
            trade_date="20240102",
            status="done",
            source="local",
            note="expected=1; evaluated=1; skipped_insufficient_history=0; failed=0",
        )
        await session.commit()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Pattern incomplete audit",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "pattern",
                            "params": {"value": "DOJI"},
                        }
                    ],
                },
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "skipped"
    assert summary["reason"] == "patterns_audit_incomplete"
    assert summary["patterns_status"]["reason"] == "patterns_audit_incomplete"
    assert summary["attempted"] == 0

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_pattern_task_rerun_clears_stale_hits_before_post_close_run(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)
    monkeypatch.setattr(pattern_task, "async_session_factory", async_session_factory_test)
    monkeypatch.setattr(pattern_task, "should_skip_market_task", lambda *args, **kwargs: False)
    monkeypatch.setattr(pattern_task, "_pattern_engine_available", lambda: True)

    async def fake_is_trading_day():
        return True

    monkeypatch.setattr(pattern_task, "is_trading_day", fake_is_trading_day)
    monkeypatch.setattr(pattern_task, "detect_patterns", lambda bars: [])

    await _seed_pattern_task_bars()
    async with async_session_factory_test() as session:
        session.add(
            Pattern(
                ts_code="000001.SZ",
                trade_date="20240102",
                trade_date_dt=date(2024, 1, 2),
                pattern_name="HAMMER",
                pattern_type="candlestick",
                confidence=Decimal("90.00"),
            )
        )
        await session.commit()

    await pattern_task.run()

    async with async_session_factory_test() as session:
        pattern_count = (await session.execute(text("""
                    SELECT COUNT(*)
                    FROM patterns
                    WHERE ts_code = '000001.SZ' AND trade_date = '20240102'
                    """))).scalar_one()
        audit_row = (await session.execute(text("""
                    SELECT status, note
                    FROM data_fetch_audit
                    WHERE task_name = 'pattern_recognition'
                      AND entity_type = 'trade_date'
                      AND entity_key = 'ALL'
                      AND trade_date = '20240102'
                    """))).mappings().one()
    assert pattern_count == 0
    assert audit_row["status"] == "done"
    assert "expected=1" in audit_row["note"]
    assert "evaluated=1" in audit_row["note"]
    assert "failed=0" in audit_row["note"]

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Pattern rerun zero-hit",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "pattern",
                            "params": {"value": "HAMMER"},
                        }
                    ],
                },
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "completed"
    assert summary["attempted"] == 1
    assert summary["completed"] == 1

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_pattern_task_engine_unavailable_blocks_pattern_readiness(
    client,
    current_user_override,
    monkeypatch,
):
    monkeypatch.setattr(
        alert_subscription_task, "async_session_factory", async_session_factory_test
    )
    monkeypatch.setattr(scheduler_module, "async_session_factory", async_session_factory_test)
    monkeypatch.setattr(pattern_task, "async_session_factory", async_session_factory_test)
    monkeypatch.setattr(pattern_task, "should_skip_market_task", lambda *args, **kwargs: False)
    monkeypatch.setattr(pattern_task, "_pattern_engine_available", lambda: False)

    async def fake_is_trading_day():
        return True

    monkeypatch.setattr(pattern_task, "is_trading_day", fake_is_trading_day)

    await _seed_pattern_task_bars()

    await pattern_task.run()

    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Pattern engine unavailable",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "pattern",
                            "params": {"value": "HAMMER"},
                        }
                    ],
                },
            },
        },
    )
    await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": create_condition.json()["id"]},
    )

    summary = await alert_subscription_task.run(date="20240102")

    assert summary["status"] == "skipped"
    assert summary["reason"] == "patterns_not_ready"
    assert summary["patterns_status"]["status"] == "failed"
    assert summary["attempted"] == 0

    notifications = await client.get("/api/v1/notifications")
    assert notifications.json()["data"] == []


@pytest.mark.asyncio
async def test_subscription_run_marks_inactive_condition_stale(client, current_user_override):
    create_condition = await client.post(
        "/api/v1/selection/my-conditions",
        json={
            "name": "Inactive baseline",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "scope": {"limit": 50},
                "root": {"type": "group", "op": "all", "children": []},
            },
        },
    )
    condition_id = create_condition.json()["id"]
    create_subscription = await client.post(
        "/api/v1/alerts/subscriptions",
        json={"selection_condition_id": condition_id},
    )
    subscription_id = create_subscription.json()["data"]["id"]

    async with async_session_factory_test() as session:
        await session.execute(
            text("UPDATE selection_conditions SET is_active = 0 WHERE id = :condition_id"),
            {"condition_id": condition_id},
        )
        await session.commit()

    stale_run = await client.post(
        f"/api/v1/alerts/subscriptions/{subscription_id}/run",
        params={"date": "20240102"},
    )
    assert stale_run.status_code == 409

    subscriptions = await client.get("/api/v1/alerts/subscriptions")
    assert subscriptions.json()["data"][0]["status"] == "stale"
