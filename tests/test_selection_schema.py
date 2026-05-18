import pytest
from pydantic import ValidationError

from app.schemas.selection_schema import (
    SavedScreenerDefinition,
    ScreeningRequest,
    ScreeningRunResponse,
    SelectionConditionCreate,
    SelectionConditionResponse,
)


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
                    "definition": {
                        "kind": "saved_screener",
                        "ast_version": 1,
                        "registry_version": 1,
                        "scope": {"market": "sz"},
                        "root": {
                            "type": "group",
                            "op": "all",
                            "children": [
                                {
                                    "type": "predicate",
                                    "rule_key": "changeMin",
                                    "params": {"value": 1.5},
                                }
                            ],
                        },
                    },
                    "definition_hash": "hash-1",
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
                        "evidence": [
                            {
                                "key": "change_rate",
                                "label": "Daily change",
                                "value": 2.5,
                                "operator": ">=",
                                "condition": 1.5,
                                "matched": True,
                            }
                        ],
                        "reason": {
                            "summary": "Change >= 1.50%",
                            "evidence": [
                                {
                                    "key": "change_rate",
                                    "label": "Daily change",
                                    "value": 2.5,
                                    "operator": ">=",
                                    "condition": 1.5,
                                    "matched": True,
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
    assert response.data.query.definition_hash == "hash-1"
    assert response.data.query.definition.root.children[0].rule_key == "changeMin"
    assert response.data.items[0].evidence[0].key == "change_rate"
    assert response.data.items[0].reason.evidence[0].condition == 1.5


def test_selection_condition_create_accepts_canonical_definition():
    payload = SelectionConditionCreate.model_validate(
        {
            "name": "MACD 金叉",
            "category": "technical",
            "definition": {
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {"market": "sz"},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "macdBullish",
                            "params": {"value": True},
                        }
                    ],
                },
            },
        }
    )

    assert payload.definition.scope.market == "sz"
    assert payload.definition.root.children[0].rule_key == "macdBullish"


def test_screening_request_accepts_definition_with_parameterized_boll_rule():
    request = ScreeningRequest.model_validate(
        {
            "definition": {
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {"market": "sz", "limit": 50},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "bollCloseAboveUpper",
                            "params": {"value": True, "period": 10, "stddev": 1.5},
                        }
                    ],
                },
            }
        }
    )

    assert request.definition is not None
    assert request.definition.root.children[0].rule_key == "bollCloseAboveUpper"
    assert request.definition.root.children[0].params["period"] == 10


def test_saved_screener_definition_rejects_nested_logic_beyond_current_scope():
    with pytest.raises(ValidationError, match="Input should be 'all'"):
        SavedScreenerDefinition.model_validate(
            {
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {},
                "root": {"type": "group", "op": "any", "children": []},
            }
        )


def test_selection_condition_response_exposes_versioned_saved_screener_fields():
    payload = SelectionConditionResponse.model_validate(
        {
            "id": 1,
            "user_id": 7,
            "name": "MACD 金叉",
            "category": "technical",
            "description": None,
            "params": {"macdBullish": True, "market": "sz"},
            "definition": {
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {"market": "sz"},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "macdBullish",
                            "params": {"value": True},
                        }
                    ],
                },
            },
            "schema_version": 1,
            "definition_version": 3,
            "definition_hash": "abc123",
            "is_active": True,
            "updated_at": "2026-04-23T10:00:00",
        }
    )

    assert payload.params == {"macdBullish": True, "market": "sz"}
    assert payload.schema_version == 1
    assert payload.definition_version == 3
    assert payload.definition_hash == "abc123"


def test_screening_request_accepts_definition_payload():
    request = ScreeningRequest.model_validate(
        {
            "scope": {"market": "sz", "limit": 20},
            "definition": {
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {"market": "sz"},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {
                            "type": "predicate",
                            "rule_key": "rsiMax",
                            "params": {"value": 30, "period": 6},
                        }
                    ],
                },
            },
        }
    )

    assert request.definition.root.children[0].params["period"] == 6
