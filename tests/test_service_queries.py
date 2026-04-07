from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest

from app.services.attention_service import AttentionService
from app.services.fund_flow_service import FundFlowService
from app.services.indicator_service import IndicatorService
from app.services.strategy_service import STRATEGIES, STRATEGY_TEMPLATES, StrategyService


def make_result(*, rows=None, row=None):
    result = Mock()
    result.fetchall.return_value = rows or []
    result.fetchone.return_value = row
    return result


def make_mapping_row(**kwargs):
    return SimpleNamespace(_mapping=kwargs)


@pytest.mark.asyncio
async def test_strategy_service_returns_static_strategy_list():
    assert StrategyService.get_strategy_list() == STRATEGIES


@pytest.mark.asyncio
async def test_strategy_service_returns_strategy_templates():
    templates = StrategyService.get_strategy_templates()

    assert templates == STRATEGY_TEMPLATES
    assert templates[0]["default_params"]["fast_ma"] == 5
    assert templates[0]["parameters"][0]["name"] == "fast_ma"


@pytest.mark.asyncio
async def test_strategy_service_run_strategy_returns_success_payload():
    service = StrategyService(db=Mock())

    payload = await service.run_strategy("enter", "2024-01-02")

    assert payload == {"status": "success", "strategy": "enter", "count": 0}


@pytest.mark.asyncio
async def test_strategy_service_get_results_builds_filters_and_normalizes_rows():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                make_mapping_row(
                    id=1,
                    date="20240102",
                    score=92.5,
                    signal="buy",
                    details={"source": "test"},
                    name="平安银行",
                    code="000001",
                    ts_code="000001.SZ",
                    new_price=10.6,
                    change_rate=1.92,
                    strategy_name="enter",
                )
            ]
        )
    )
    service = StrategyService(db=db)

    rows = await service.get_results("enter", "20240102", 20)

    assert rows[0]["code"] == "000001"
    assert rows[0]["strategy_name"] == "enter"
    _, params = db.execute.await_args.args
    assert params == {"limit": 20, "strategy_name": "enter", "trade_date": "20240102"}


@pytest.mark.asyncio
async def test_fund_flow_service_returns_query_rows():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                make_mapping_row(ts_code="000001.SZ", trade_date="20240102", stock_name="平安银行")
            ]
        )
    )
    service = FundFlowService(db=db)

    rows = await service.get_fund_flow("000001", 5)

    assert rows[0]["stock_name"] == "平安银行"
    _, params = db.execute.await_args.args
    assert params == {"code": "000001", "days": 5}


@pytest.mark.asyncio
async def test_indicator_service_returns_rows_and_latest_item():
    first_result = make_result(
        rows=[make_mapping_row(ts_code="000001.SZ", trade_date="20240102", stock_name="平安银行")]
    )
    second_result = make_result(
        row=make_mapping_row(ts_code="000001.SZ", trade_date="20240103", stock_name="平安银行")
    )
    db = Mock()
    db.execute = AsyncMock(side_effect=[first_result, second_result])
    service = IndicatorService(db=db)

    rows = await service.get_indicators("000001", None, None, 10)
    latest = await service.get_latest_indicator("000001")

    assert rows[0]["trade_date"] == "20240102"
    assert latest["trade_date"] == "20240103"
    assert db.execute.await_args_list == [
        call(ANY_TEXT, {"code": "000001", "limit": 10}),
        call(ANY_TEXT, {"code": "000001"}),
    ]


@pytest.mark.asyncio
async def test_attention_service_get_list_supports_global_and_user_scoped_queries():
    first_result = make_result(rows=[make_mapping_row(code="000001", stock_name="平安银行")])
    second_result = make_result(rows=[make_mapping_row(code="600000", stock_name="浦发银行")])
    db = Mock()
    db.execute = AsyncMock(side_effect=[first_result, second_result])
    service = AttentionService(db=db)

    all_rows = await service.get_list()
    user_rows = await service.get_list(user_id=7)

    assert all_rows[0]["code"] == "000001"
    assert user_rows[0]["code"] == "600000"
    assert db.execute.await_args_list[1].args[1] == {"user_id": 7}


@pytest.mark.asyncio
async def test_attention_service_add_and_remove_handle_missing_stock():
    db = Mock()
    db.execute = AsyncMock(return_value=make_result(row=None))
    db.commit = AsyncMock()
    service = AttentionService(db=db)

    add_result = await service.add("000001", 7)
    remove_result = await service.remove("000001", 7)

    assert add_result == {"status": "error", "message": "Stock not found"}
    assert remove_result == {"status": "error", "message": "Stock not found"}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_attention_service_add_and_remove_commit_when_stock_exists():
    lookup_result = make_result(row=("000001.SZ",))
    delete_lookup_result = make_result(row=("000001.SZ",))
    db = Mock()
    # Service queries: add -> select ts_code, select id check, insert; remove -> select ts_code, delete
    db.execute = AsyncMock(
        side_effect=[
            lookup_result,  # add: SELECT ts_code
            make_result(),  # add: SELECT id (check) -> empty
            make_result(),  # add: INSERT result
            delete_lookup_result,  # remove: SELECT ts_code
            make_result(),  # remove: DELETE result
        ]
    )
    db.commit = AsyncMock()
    service = AttentionService(db=db)

    add_result = await service.add("000001", 7)
    remove_result = await service.remove("000001", 7)

    assert add_result == {"status": "success", "code": "000001"}
    assert remove_result == {"status": "success", "code": "000001"}
    assert db.commit.await_count == 2


class _AnyText:
    def __eq__(self, other):
        return hasattr(other, "text")


ANY_TEXT = _AnyText()
