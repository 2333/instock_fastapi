from unittest.mock import AsyncMock, Mock

import pytest

from app.services.selection_service import SelectionService


def make_result(*, rows=None):
    result = Mock()
    mappings = Mock()
    mappings.all.return_value = rows or []
    result.mappings.return_value = mappings
    return result


def test_selection_service_no_longer_accepts_provider_runtime():
    with pytest.raises(TypeError):
        SelectionService(db=Mock(), provider=Mock())  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_run_selection_uses_canonical_sql_adapter():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                {
                    "ts_code": "000001.SZ",
                    "code": "000001",
                    "stock_name": "平安银行",
                    "trade_date": "20240328",
                    "close": 10.6,
                    "pct_chg": 2.5,
                    "vol": 5000,
                    "amount": 300000000,
                }
            ]
        )
    )
    service = SelectionService(db=db)
    service._resolve_trade_date = AsyncMock(return_value="20240328")

    results = await service.run_selection({"priceMin": 5}, None)

    assert len(results) == 1
    assert results[0]["code"] == "000001"
    assert results[0]["signal"] == "buy"
    assert results[0]["reason_summary"].startswith("Close >= 5.00")
