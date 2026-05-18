import pytest

from app.schemas.selection_schema import SavedScreenerDefinition
from app.services.screener_adapter import (
    build_saved_screener_persistence,
    canonicalize_legacy_params,
    definition_to_filters,
    get_saved_screener_schema_version,
    normalize_saved_screener_payload,
)


def test_legacy_params_round_trip_into_canonical_definition():
    definition = canonicalize_legacy_params({"priceMin": 10, "macdBullish": True, "market": "sz"})

    assert definition["kind"] == "saved_screener"
    assert definition["scope"]["market"] == "sz"
    assert definition_to_filters(definition) == {
        "market": "sz",
        "priceMin": 10,
        "macdBullish": True,
    }


def test_normalize_saved_screener_payload_rejects_unknown_rule():
    with pytest.raises(ValueError, match="unsupported rule_key"):
        normalize_saved_screener_payload(
            definition={
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {"type": "predicate", "rule_key": "unknown", "params": {"value": 1}}
                    ],
                },
            }
        )


def test_normalize_saved_screener_payload_accepts_pre_canonicalized_params():
    definition, filters, _ = normalize_saved_screener_payload(
        params={
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
                        "params": {"value": 30},
                    }
                ],
            },
        }
    )

    assert definition["scope"]["market"] == "sz"
    assert filters == {"market": "sz", "rsiMax": 30}


def test_normalize_saved_screener_payload_rejects_duplicate_effective_filters():
    with pytest.raises(ValueError, match="duplicate predicate"):
        normalize_saved_screener_payload(
            definition={
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 1,
                "scope": {},
                "root": {
                    "type": "group",
                    "op": "all",
                    "children": [
                        {"type": "predicate", "rule_key": "rsiMax", "params": {"value": 30}},
                        {"type": "predicate", "rule_key": "rsiMax", "params": {"value": 40}},
                    ],
                },
            }
        )


def test_normalize_saved_screener_payload_rejects_unknown_registry_version():
    with pytest.raises(ValueError, match="unsupported registry_version"):
        normalize_saved_screener_payload(
            definition={
                "kind": "saved_screener",
                "ast_version": 1,
                "registry_version": 2,
                "scope": {},
                "root": {"type": "group", "op": "all", "children": []},
            }
        )


def test_saved_screener_schema_version_is_stable():
    assert get_saved_screener_schema_version() == 1


def test_normalize_saved_screener_payload_applies_indicator_defaults():
    definition, _, _ = normalize_saved_screener_payload(
        definition={
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
                        "params": {"value": 30},
                    }
                ],
            },
        }
    )

    assert definition["root"]["children"][0]["params"]["period"] == 14


def test_normalize_saved_screener_payload_rejects_invalid_macd_periods():
    with pytest.raises(ValueError, match="fast_period < slow_period"):
        normalize_saved_screener_payload(
            definition={
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
                            "params": {
                                "value": True,
                                "fast_period": 20,
                                "slow_period": 10,
                                "signal_period": 5,
                            },
                        }
                    ],
                },
            }
        )


def test_normalize_saved_screener_payload_merges_scope_market_when_definition_omits_it():
    definition, filters, _ = normalize_saved_screener_payload(
        definition={
            "kind": "saved_screener",
            "ast_version": 1,
            "registry_version": 1,
            "scope": {},
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
        scope={"market": "sz", "limit": 20},
    )

    assert definition["scope"]["market"] == "sz"
    assert filters["market"] == "sz"


def test_normalize_saved_screener_payload_merges_scope_limit_when_definition_omits_it():
    definition, _, definition_hash = normalize_saved_screener_payload(
        definition={
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
                        "params": {"value": 30, "period": 10},
                    }
                ],
            },
        },
        scope={"market": "sz", "limit": 50},
    )

    assert definition["scope"]["limit"] == 50
    assert len(definition_hash) == 64


def test_normalize_saved_screener_payload_overrides_pydantic_scope_defaults_with_top_level_scope():
    definition, _, _ = normalize_saved_screener_payload(
        definition=SavedScreenerDefinition.model_validate(
            {
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
                            "params": {"value": 30, "period": 10},
                        }
                    ],
                },
            }
        ),
        scope={"market": "sz", "limit": 50},
    )

    assert definition["scope"]["limit"] == 50


def test_build_saved_screener_persistence_keeps_definition_version_when_definition_is_unchanged():
    existing_params = canonicalize_legacy_params({"rsiMax": 30, "market": "sz"})

    persistence = build_saved_screener_persistence(
        params={"rsiMax": 30, "market": "sz"},
        existing_params=existing_params,
        existing_definition_version=4,
    )

    assert persistence["definition_changed"] is False
    assert persistence["definition_version"] == 4
    assert persistence["schema_version"] == 1
    assert persistence["params"] == {"market": "sz", "rsiMax": 30}


def test_build_saved_screener_persistence_increments_definition_version_when_definition_changes():
    existing_params = canonicalize_legacy_params({"rsiMax": 30, "market": "sz"})

    persistence = build_saved_screener_persistence(
        definition={
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
        existing_params=existing_params,
        existing_definition_version=1,
    )

    assert persistence["definition_changed"] is True
    assert persistence["definition_version"] == 2
    assert persistence["params"] == {"market": "sz", "macdBullish": True}


def test_parameterized_indicator_definition_preserves_non_default_runtime_params():
    definition, filters, _ = normalize_saved_screener_payload(
        definition={
            "kind": "saved_screener",
            "ast_version": 1,
            "registry_version": 1,
            "scope": {},
            "root": {
                "type": "group",
                "op": "all",
                "children": [
                    {
                        "type": "predicate",
                        "rule_key": "rsiMax",
                        "params": {"value": 40, "period": 5},
                    },
                    {
                        "type": "predicate",
                        "rule_key": "bollCloseAboveUpper",
                        "params": {"value": True, "period": 10, "stddev": 1.5},
                    },
                ],
            },
        }
    )

    children = {item["rule_key"]: item["params"] for item in definition["root"]["children"]}
    assert children["rsiMax"] == {"value": 40, "period": 5}
    assert children["bollCloseAboveUpper"] == {"value": True, "period": 10, "stddev": 1.5}
    assert filters == {"rsiMax": 40, "bollCloseAboveUpper": True}
