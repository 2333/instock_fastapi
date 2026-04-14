from types import SimpleNamespace

import pytest

from scripts.timescale_health_check import CORE_TABLES, run_timescale_health_checks


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value

    def scalar(self):
        return self._value

    def fetchall(self):
        return self._value

    def all(self):
        return self._value


class _FakeSession:
    def __init__(self, dialect_name: str, mapping: dict[str, object]):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self._mapping = mapping
        self.executed_sql: list[str] = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.executed_sql.append(sql)
        for needle, value in self._mapping.items():
            if needle in sql:
                return _FakeResult(value)
        raise AssertionError(f"Unexpected SQL: {sql}")


@pytest.mark.asyncio
async def test_timescale_health_checks_skip_non_postgres():
    session = _FakeSession("sqlite", {})

    results = await run_timescale_health_checks(session)

    assert all(item["status"] == "skipped" for item in results)
    assert session.executed_sql == []
    assert len(results) == 1 + len(CORE_TABLES) * 4 + 2


@pytest.mark.asyncio
async def test_timescale_health_checks_collect_postgres_signals():
    mapping = {
        "FROM pg_extension": True,
        "FROM timescaledb_information.hypertables": True,
        "FROM timescaledb_information.chunks": 3,
        "FROM timescaledb_information.jobs": True,
        "EXPLAIN": [("ChunkAppend on daily_bars",), ("Index Scan using ix_daily_bars_trade_date_dt",)],
    }
    session = _FakeSession("postgresql", mapping)

    results = await run_timescale_health_checks(session)

    assert results[0]["check"] == "extension.timescaledb"
    assert results[0]["status"] == "ok"
    assert any(item["check"] == "hypertable.registered" for item in results)
    assert any(item["check"] == "hypertable.chunk_count" and item["value"] == 3 for item in results)
    assert any(item["check"] == "hypertable.compression_policy" and item["status"] == "ok" for item in results)
    assert any(item["check"] == "plan.daily_bars_window" for item in results)
    assert any(
        item["check"] == "plan.daily_bars_window" and "ChunkAppend on daily_bars" in item["value"]
        for item in results
    )
