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


def _build_column_metric(key: str, label: str, column: str, description: str) -> SelectionMetricDefinition:
    def compute(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
        return _numeric_series(frame, column)

    return SelectionMetricDefinition(
        key=key,
        label=label,
        category="price",
        description=description,
        compute=compute,
        outputs=(SelectionOutputDefinition(key="value", label=label),),
        operators=RELATIONAL_OPERATORS,
    )


METRICS = [
    _build_column_metric("open", "开盘价", "open", "原始开盘价序列"),
    _build_column_metric("high", "最高价", "high", "原始最高价序列"),
    _build_column_metric("low", "最低价", "low", "原始最低价序列"),
    _build_column_metric("close", "收盘价", "close", "原始收盘价序列"),
    _build_column_metric("pct_chg", "涨跌幅", "pct_chg", "周期涨跌幅百分比"),
]
