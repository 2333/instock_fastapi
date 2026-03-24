from __future__ import annotations

from app.selection.catalog.base import SelectionCatalogRegistry
from app.selection.catalog.fundamental import METRICS as FUNDAMENTAL_METRICS
from app.selection.catalog.pattern import build_pattern_metrics
from app.selection.catalog.price import METRICS as PRICE_METRICS
from app.selection.catalog.technical import METRICS as TECHNICAL_METRICS
from app.selection.catalog.volume import METRICS as VOLUME_METRICS

CATEGORY_LABELS = {
    "price": "行情价格",
    "volume": "成交量与换手",
    "technical": "技术指标",
    "fundamental": "基本面",
    "pattern": "形态信号",
}

OPERATOR_DEFINITIONS = [
    {"key": "gt", "label": ">"},
    {"key": "gte", "label": ">="},
    {"key": "lt", "label": "<"},
    {"key": "lte", "label": "<="},
    {"key": "eq", "label": "="},
    {"key": "ne", "label": "!="},
    {"key": "crosses_above", "label": "上穿"},
    {"key": "crosses_below", "label": "下穿"},
]

TIME_RULE_DEFINITIONS = [
    {"key": "current", "label": "当前周期"},
    {"key": "any", "label": "最近 N 个周期任意满足"},
    {"key": "all", "label": "最近 N 个周期连续满足"},
]

PERIOD_DEFINITIONS = [
    {"key": "daily", "label": "日线"},
    {"key": "weekly", "label": "周线"},
    {"key": "monthly", "label": "月线"},
]


def build_selection_registry(pattern_names: list[str] | None = None) -> SelectionCatalogRegistry:
    registry = SelectionCatalogRegistry()
    registry.register(*PRICE_METRICS)
    registry.register(*VOLUME_METRICS)
    registry.register(*TECHNICAL_METRICS)
    registry.register(*FUNDAMENTAL_METRICS)
    registry.register(*build_pattern_metrics(pattern_names))
    return registry


def build_selection_catalog(pattern_names: list[str] | None = None) -> dict:
    registry = build_selection_registry(pattern_names)
    groups: dict[str, dict] = {}
    for metric in registry.all():
        group = groups.setdefault(
            metric.category,
            {
                "key": metric.category,
                "label": CATEGORY_LABELS.get(metric.category, metric.category),
                "items": [],
            },
        )
        group["items"].append(metric.to_dict())

    ordered_groups = []
    for key in ("price", "volume", "technical", "fundamental", "pattern"):
        if key in groups:
            groups[key]["items"].sort(key=lambda item: item["label"])
            ordered_groups.append(groups[key])

    return {
        "version": 1,
        "periods": PERIOD_DEFINITIONS,
        "operators": OPERATOR_DEFINITIONS,
        "time_rules": TIME_RULE_DEFINITIONS,
        "groups": ordered_groups,
    }
