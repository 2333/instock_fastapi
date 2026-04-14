from types import SimpleNamespace

import pytest

from app.jobs.m1_quality_runner import has_quality_failures, run_m1_quality_checks, summarize_quality_results


class _FakeRow(dict):
    def __init__(self, mapping):
        super().__init__(mapping)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self):
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
        self.executed_sql: list[str] = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.executed_sql.append(sql)

        if "SELECT COUNT(*) AS row_count FROM" in sql:
            table = sql.rsplit(" ", 1)[-1]
            return _FakeResult([_FakeRow({"row_count": 3 if table == "daily_bars" else 1})])
        if "COUNT(*) AS row_count" in sql and "GROUP BY trade_date" in sql:
            return _FakeResult(
                [
                    _FakeRow({"trade_date": "20240102", "row_count": 2}),
                    _FakeRow({"trade_date": "20240101", "row_count": 1}),
                ]
            )
        if "MIN(trade_date_dt)" in sql:
            return _FakeResult(
                [
                    _FakeRow(
                        {
                            "min_trade_date_dt": "2024-01-01",
                            "max_trade_date_dt": "2024-01-02",
                            "min_trade_date": "20240101",
                            "max_trade_date": "20240102",
                            "row_count": 3,
                        }
                    )
                ]
            )
        if "null_trade_date_dt_count" in sql:
            value = 1 if "FROM daily_bars" in sql else 0
            return _FakeResult([_FakeRow({"null_trade_date_dt_count": value})])
        if "duplicate_groups" in sql:
            return _FakeResult([_FakeRow({"duplicate_groups": 0})])
        if "duplicate_count" in sql:
            return _FakeResult([])
        if "shared_rows" in sql and "daily_basic" in sql:
            return _FakeResult(
                [
                    _FakeRow(
                        {
                            "shared_rows": 1,
                            "shared_dates": 1,
                            "latest_shared_trade_date": "20240102",
                            "daily_bars_dates": 1,
                            "daily_basic_dates": 1,
                        }
                    )
                ]
            )

        raise AssertionError(f"Unexpected SQL: {sql}")


@pytest.mark.asyncio
async def test_quality_runner_builds_summary_with_failures():
    session = _FakeSession()

    results = await run_m1_quality_checks(session, sample_limit=3)
    summary = summarize_quality_results(results)

    assert len(results) == 29
    assert any(item["check"] == "null_trade_date_dt" and item["status"] == "fail" for item in results)
    assert summary["total_checks"] == 29
    assert summary["status_counts"]["fail"] == 1
    assert has_quality_failures(results) is True


@pytest.mark.asyncio
async def test_quality_runner_executes_expected_sql_shapes():
    session = _FakeSession()

    await run_m1_quality_checks(session, sample_limit=2)

    assert any("FROM daily_bars" in sql for sql in session.executed_sql)
    assert any("FROM daily_basic" in sql for sql in session.executed_sql)
    assert any("daily_bars b" in sql and "daily_basic d" in sql for sql in session.executed_sql)
