from __future__ import annotations

import pandas as pd

from app.selection.catalog.base import (
    RELATIONAL_OPERATORS,
    SelectionMetricDefinition,
    SelectionOutputDefinition,
)


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    source = frame[column] if column in frame.columns else pd.Series(index=frame.index, dtype="float64")
    return pd.to_numeric(source, errors="coerce")


def _build_metric(key: str, label: str, description: str) -> SelectionMetricDefinition:
    def compute(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
        return _numeric_series(frame, key)

    return SelectionMetricDefinition(
        key=key,
        label=label,
        category="fundamental",
        description=description,
        compute=compute,
        outputs=(SelectionOutputDefinition(key="value", label=label),),
        operators=RELATIONAL_OPERATORS,
    )


METRICS = [
    _build_metric("pe", "PE", "市盈率"),
    _build_metric("pe_ttm", "PE(TTM)", "滚动市盈率"),
    _build_metric("pb", "PB", "市净率"),
    _build_metric("ps", "PS", "市销率"),
    _build_metric("ps_ttm", "PS(TTM)", "滚动市销率"),
    _build_metric("dv_ratio", "股息率", "股息率"),
    _build_metric("dv_ttm", "股息率(TTM)", "滚动股息率"),
    _build_metric("total_mv", "总市值", "总市值"),
    _build_metric("circ_mv", "流通市值", "流通市值"),
]
