from __future__ import annotations

import re

import pandas as pd

from app.selection.catalog.base import (
    DEFAULT_COMPARISON_OPERATORS,
    SelectionMetricDefinition,
    SelectionOutputDefinition,
)
from core.pattern.recognizer import PatternType

EXTRA_PATTERNS = (
    "BREAKTHROUGH_HIGH",
    "BREAKDOWN_LOW",
    "CONTINUOUS_RISE",
    "CONTINUOUS_FALL",
    "MA_GOLDEN_CROSS",
    "MA_DEATH_CROSS",
)


def _labelize(name: str) -> str:
    text = name.replace("_", " ").title()
    return re.sub(r"\s+", " ", text)


def _build_metric(pattern_name: str) -> SelectionMetricDefinition:
    def compute(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
        if output_key == "confidence":
            column = f"pattern_conf__{pattern_name}"
            source = frame[column] if column in frame.columns else pd.Series(index=frame.index, dtype="float64")
            return pd.to_numeric(source, errors="coerce")
        column = f"pattern__{pattern_name}"
        source = frame[column] if column in frame.columns else pd.Series(False, index=frame.index, dtype="bool")
        return source.fillna(False).astype(bool)

    label = _labelize(pattern_name)
    return SelectionMetricDefinition(
        key=f"pattern__{pattern_name}",
        label=label,
        category="pattern",
        description=f"形态信号 {label}",
        compute=compute,
        outputs=(
            SelectionOutputDefinition(key="occurred", label="出现", kind="boolean"),
            SelectionOutputDefinition(key="confidence", label="置信度", kind="number"),
        ),
        operators=DEFAULT_COMPARISON_OPERATORS,
        default_output="occurred",
    )


def build_pattern_metrics(pattern_names: list[str] | None = None) -> list[SelectionMetricDefinition]:
    names = pattern_names or [pattern.name for pattern in PatternType] + list(EXTRA_PATTERNS)
    ordered = []
    seen: set[str] = set()
    for item in names:
        normalized = str(item or "").strip().upper()
        if not normalized or normalized in seen:
            continue
        ordered.append(_build_metric(normalized))
        seen.add(normalized)
    return ordered
