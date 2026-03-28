from app.schemas.selection_schema import ScreeningRequest, ScreeningRunResponse


def test_screening_request_accepts_legacy_conditions_payload():
    request = ScreeningRequest.model_validate(
        {"conditions": {"priceMin": 5, "changeMin": 1.5}, "scope": {"market": "sz", "limit": 20}}
    )

    assert request.filters.price_min == 5
    assert request.filters.change_min == 1.5
    assert request.scope.market == "sz"
    assert request.scope.limit == 20


def test_screening_run_response_preserves_structured_reason_payload():
    response = ScreeningRunResponse.model_validate(
        {
            "data": {
                "query": {
                    "filters": {"changeMin": 1.5},
                    "scope": {"market": "sz", "limit": 50},
                    "trade_date": "20240102",
                },
                "items": [
                    {
                        "ts_code": "000001.SZ",
                        "code": "000001",
                        "stock_name": "平安银行",
                        "trade_date": "20240102",
                        "date": "20240102",
                        "close": 10.6,
                        "change_rate": 2.5,
                        "amount": 300000000,
                        "score": 15.5,
                        "signal": "buy",
                        "reason_summary": "Change >= 1.50%",
                        "reason": {
                            "summary": "Change >= 1.50%",
                            "matched": [
                                {
                                    "field": "change_rate",
                                    "operator": ">=",
                                    "value": 1.5,
                                    "summary": "Change >= 1.50%",
                                }
                            ],
                            "evidence": [
                                {
                                    "metric": "change_rate",
                                    "value": 2.5,
                                    "summary": "Daily change 2.50%",
                                }
                            ],
                        },
                    }
                ],
                "total": 1,
            }
        }
    )

    assert response.data.query.filters.change_min == 1.5
    assert response.data.items[0].reason.matched[0].field == "change_rate"
    assert response.data.items[0].reason.evidence[0].summary == "Daily change 2.50%"
