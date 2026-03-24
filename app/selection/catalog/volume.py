from __future__ import annotations

import pandas as pd

from app.selection.backends import compute_vectorbt_metric
from app.selection.catalog.base import (
    RELATIONAL_OPERATORS,
    SelectionMetricDefinition,
    SelectionOutputDefinition,
    SelectionParamDefinition,
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
        category="volume",
        description=description,
        compute=compute,
        outputs=(SelectionOutputDefinition(key="value", label=label),),
        operators=RELATIONAL_OPERATORS,
    )


def _compute_volume_ma(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("volume_ma", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    period = max(int(params.get("period", 5) or 5), 1)
    return _numeric_series(frame, "volume").rolling(period).mean()


METRICS = [
    _build_column_metric("volume", "成交量", "volume", "成交量序列"),
    _build_column_metric("amount", "成交额", "amount", "成交额序列"),
    _build_column_metric("turnover_rate", "换手率", "turnover_rate", "daily_basic 换手率"),
    _build_column_metric("volume_ratio", "量比", "volume_ratio", "daily_basic 量比"),
    SelectionMetricDefinition(
        key="volume_ma",
        label="成交量均线",
        category="volume",
        description="成交量移动平均线",
        compute=_compute_volume_ma,
        outputs=(SelectionOutputDefinition(key="value", label="成交量均线"),),
        operators=RELATIONAL_OPERATORS,
        params=(SelectionParamDefinition(key="period", label="周期", default=5, minimum=1, maximum=120, step=1),),
    ),
]
