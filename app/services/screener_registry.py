from __future__ import annotations

from typing import Any


REGISTRY_VERSION = 1
BASELINE_SQL_ADAPTER = "baseline_sql"


_RULES: list[dict[str, Any]] = [
    {
        "rule_key": "priceMin",
        "label": "最低价格",
        "value_type": "number",
        "operators": [">="],
        "param_schema": {
            "value": {"type": "number", "required": True},
        },
        "maps_to_filter_key": "priceMin",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "basic_filter",
        "status": "active",
    },
    {
        "rule_key": "priceMax",
        "label": "最高价格",
        "value_type": "number",
        "operators": ["<="],
        "param_schema": {
            "value": {"type": "number", "required": True},
        },
        "maps_to_filter_key": "priceMax",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "basic_filter",
        "status": "active",
    },
    {
        "rule_key": "changeMin",
        "label": "最小涨跌幅",
        "value_type": "number",
        "operators": [">="],
        "param_schema": {
            "value": {"type": "number", "required": True},
        },
        "maps_to_filter_key": "changeMin",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "basic_filter",
        "status": "active",
    },
    {
        "rule_key": "changeMax",
        "label": "最大涨跌幅",
        "value_type": "number",
        "operators": ["<="],
        "param_schema": {
            "value": {"type": "number", "required": True},
        },
        "maps_to_filter_key": "changeMax",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "basic_filter",
        "status": "active",
    },
    {
        "rule_key": "market",
        "label": "市场范围",
        "value_type": "enum",
        "operators": ["="],
        "param_schema": {
            "value": {"type": "string", "required": True, "enum": ["sh", "sz"]},
        },
        "maps_to_filter_key": "market",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "scope",
        "status": "active",
    },
    {
        "rule_key": "rsiMin",
        "label": "RSI 下限",
        "value_type": "number",
        "operators": [">="],
        "param_schema": {
            "value": {"type": "number", "required": True, "min": 0, "max": 100},
            "period": {"type": "integer", "default": 14, "min": 2, "max": 60},
        },
        "default_params": {"period": 14},
        "maps_to_filter_key": "rsiMin",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "rsi_threshold",
        "status": "active",
        "description": "RSI 指标最小值 (0-100)",
    },
    {
        "rule_key": "rsiMax",
        "label": "RSI 上限",
        "value_type": "number",
        "operators": ["<="],
        "param_schema": {
            "value": {"type": "number", "required": True, "min": 0, "max": 100},
            "period": {"type": "integer", "default": 14, "min": 2, "max": 60},
        },
        "default_params": {"period": 14},
        "maps_to_filter_key": "rsiMax",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "rsi_threshold",
        "status": "active",
        "description": "RSI 指标最大值 (0-100)",
    },
    {
        "rule_key": "macdBullish",
        "label": "MACD 看涨",
        "value_type": "boolean",
        "operators": ["="],
        "param_schema": {
            "value": {"type": "boolean", "required": True},
            "fast_period": {"type": "integer", "default": 12, "min": 2, "max": 30},
            "slow_period": {"type": "integer", "default": 26, "min": 5, "max": 60},
            "signal_period": {"type": "integer", "default": 9, "min": 2, "max": 20},
        },
        "default_params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "maps_to_filter_key": "macdBullish",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "macd_signal",
        "status": "active",
        "description": "是否要求 MACD 金叉/柱状图为正",
    },
    {
        "rule_key": "macdBearish",
        "label": "MACD 看跌",
        "value_type": "boolean",
        "operators": ["="],
        "param_schema": {
            "value": {"type": "boolean", "required": True},
            "fast_period": {"type": "integer", "default": 12, "min": 2, "max": 30},
            "slow_period": {"type": "integer", "default": 26, "min": 5, "max": 60},
            "signal_period": {"type": "integer", "default": 9, "min": 2, "max": 20},
        },
        "default_params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "maps_to_filter_key": "macdBearish",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "macd_signal",
        "status": "active",
        "description": "是否要求 MACD 死叉/柱状图为负",
    },
    {
        "rule_key": "bollCloseAboveUpper",
        "label": "BOLL 突破上轨",
        "value_type": "boolean",
        "operators": ["="],
        "param_schema": {
            "value": {"type": "boolean", "required": True},
            "period": {"type": "integer", "default": 20, "min": 5, "max": 60},
            "stddev": {"type": "number", "default": 2.0, "min": 1.0, "max": 4.0},
        },
        "default_params": {"period": 20, "stddev": 2.0},
        "maps_to_filter_key": "bollCloseAboveUpper",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "boll_band",
        "status": "active",
        "description": "收盘价高于布林带上轨",
    },
    {
        "rule_key": "bollCloseBelowLower",
        "label": "BOLL 跌破下轨",
        "value_type": "boolean",
        "operators": ["="],
        "param_schema": {
            "value": {"type": "boolean", "required": True},
            "period": {"type": "integer", "default": 20, "min": 5, "max": 60},
            "stddev": {"type": "number", "default": 2.0, "min": 1.0, "max": 4.0},
        },
        "default_params": {"period": 20, "stddev": 2.0},
        "maps_to_filter_key": "bollCloseBelowLower",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "boll_band",
        "status": "active",
        "description": "收盘价低于布林带下轨",
    },
    {
        "rule_key": "pattern",
        "label": "形态筛选",
        "value_type": "enum",
        "operators": ["="],
        "param_schema": {
            "value": {"type": "string", "required": True},
        },
        "maps_to_filter_key": "pattern",
        "supported_adapters": [BASELINE_SQL_ADAPTER],
        "runtime_kind": "basic_filter",
        "status": "active",
        "description": "形态类型（如 HAMMER、HEAD_SHOULDERS、INVERSE_HEAD_SHOULDERS）",
    },
]


_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "macd-golden-cross",
        "name": "MACD 金叉池",
        "description": "筛选 MACD 看涨信号，可作为趋势延续模板。",
        "icon": "✨",
        "filters": {"macdBullish": True},
    },
    {
        "id": "rsi-oversold",
        "name": "RSI 超卖反弹",
        "description": "关注 RSI 低位区间的潜在反弹标的。",
        "icon": "📈",
        "filters": {"rsiMin": 0, "rsiMax": 30},
    },
    {
        "id": "boll-breakout-watch",
        "name": "布林突破观察",
        "description": "以价格与涨跌幅作为布林突破前的观察模板。",
        "icon": "🚀",
        "filters": {"priceMin": 5.0, "changeMin": 3.0},
    },
]


def get_registry_version() -> int:
    return REGISTRY_VERSION


def get_rule_registry() -> list[dict[str, Any]]:
    return [dict(rule) for rule in _RULES]


def get_rule_registry_map() -> dict[str, dict[str, Any]]:
    return {rule["rule_key"]: dict(rule) for rule in _RULES}


def get_filter_fields() -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for rule in _RULES:
        field = {
            "key": rule["rule_key"],
            "label": rule["label"],
            "value_type": rule["value_type"],
            "operators": list(rule["operators"]),
            "param_schema": dict(rule.get("param_schema") or {}),
            "default_params": dict(rule.get("default_params") or {}),
            "supported_adapters": list(rule.get("supported_adapters") or []),
        }
        if rule.get("description"):
            field["description"] = rule["description"]
        fields.append(field)
    return fields


def get_templates() -> list[dict[str, Any]]:
    return [dict(template) for template in _TEMPLATES]
