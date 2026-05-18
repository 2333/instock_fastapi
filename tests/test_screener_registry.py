from app.services.screener_registry import (
    BASELINE_SQL_ADAPTER,
    get_filter_fields,
    get_rule_registry,
)


def test_registry_filter_fields_are_backed_by_rule_registry():
    rule_registry = get_rule_registry()
    filter_fields = get_filter_fields()

    assert [field["key"] for field in filter_fields] == [rule["rule_key"] for rule in rule_registry]
    assert all(BASELINE_SQL_ADAPTER in rule["supported_adapters"] for rule in rule_registry)


def test_parameterized_technical_rules_expose_default_params_and_param_schema():
    rules = {rule["rule_key"]: rule for rule in get_rule_registry()}
    filter_fields = get_filter_fields()

    assert rules["rsiMax"]["default_params"] == {"period": 14}
    assert rules["macdBullish"]["default_params"] == {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
    }
    assert rules["bollCloseAboveUpper"]["default_params"] == {"period": 20, "stddev": 2.0}
    assert "period" in rules["rsiMin"]["param_schema"]
    assert "fast_period" in rules["macdBearish"]["param_schema"]
    assert "stddev" in rules["bollCloseBelowLower"]["param_schema"]
    assert any(field["key"] == "bollCloseAboveUpper" for field in filter_fields)
    rsi_max = next(field for field in filter_fields if field["key"] == "rsiMax")
    assert rsi_max["param_schema"]["period"]["default"] == 14
