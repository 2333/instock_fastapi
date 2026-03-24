from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

MetricComputer = Callable[[pd.DataFrame, dict[str, Any], str], pd.Series]

DEFAULT_COMPARISON_OPERATORS = ("gt", "gte", "lt", "lte", "eq", "ne")
RELATIONAL_OPERATORS = DEFAULT_COMPARISON_OPERATORS + ("crosses_above", "crosses_below")


@dataclass(frozen=True)
class SelectionOptionDefinition:
    value: Any
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "label": self.label}


@dataclass(frozen=True)
class SelectionParamDefinition:
    key: str
    label: str
    type: str = "number"
    default: Any = None
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    options: tuple[SelectionOptionDefinition, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "default": self.default,
        }
        if self.minimum is not None:
            payload["minimum"] = self.minimum
        if self.maximum is not None:
            payload["maximum"] = self.maximum
        if self.step is not None:
            payload["step"] = self.step
        if self.options:
            payload["options"] = [option.to_dict() for option in self.options]
        return payload


@dataclass(frozen=True)
class SelectionOutputDefinition:
    key: str
    label: str
    kind: str = "number"

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label, "kind": self.kind}


@dataclass(frozen=True)
class SelectionMetricDefinition:
    key: str
    label: str
    category: str
    description: str
    compute: MetricComputer
    outputs: tuple[SelectionOutputDefinition, ...]
    operators: tuple[str, ...]
    params: tuple[SelectionParamDefinition, ...] = ()
    default_output: str = "value"
    right_operand_modes: tuple[str, ...] = ("value", "indicator")

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "outputs": [output.to_dict() for output in self.outputs],
            "operators": list(self.operators),
            "params": [param.to_dict() for param in self.params],
            "default_output": self.default_output,
            "right_operand_modes": list(self.right_operand_modes),
        }


class SelectionCatalogRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, SelectionMetricDefinition] = {}

    def register(self, *metrics: SelectionMetricDefinition) -> None:
        for metric in metrics:
            self._metrics[metric.key] = metric

    def get(self, key: str) -> SelectionMetricDefinition:
        return self._metrics[key]

    def all(self) -> list[SelectionMetricDefinition]:
        return list(self._metrics.values())
