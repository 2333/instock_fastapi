from __future__ import annotations

import numpy as np
import pandas as pd

from app.selection.backends import compute_vectorbt_metric
from app.selection.catalog.base import (
    DEFAULT_COMPARISON_OPERATORS,
    RELATIONAL_OPERATORS,
    SelectionMetricDefinition,
    SelectionOutputDefinition,
    SelectionParamDefinition,
)


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    source = frame[column] if column in frame.columns else pd.Series(index=frame.index, dtype="float64")
    return pd.to_numeric(source, errors="coerce")


def _ma_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    period = max(int(params.get("period", 20) or 20), 1)
    return _numeric_series(frame, "close").rolling(period).mean()


def _ma(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("ma", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _ma_pandas(frame, params, output_key)


def _ema_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    period = max(int(params.get("period", 20) or 20), 1)
    return _numeric_series(frame, "close").ewm(span=period, adjust=False).mean()


def _ema(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("ema", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _ema_pandas(frame, params, output_key)


def _macd_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    fast = max(int(params.get("fast", 12) or 12), 1)
    slow = max(int(params.get("slow", 26) or 26), fast + 1)
    signal = max(int(params.get("signal", 9) or 9), 1)
    close = _numeric_series(frame, "close")
    macd_line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    mapping = {
        "macd": macd_line,
        "signal": signal_line,
        "hist": hist,
    }
    return mapping[output_key]


def _macd(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("macd", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _macd_pandas(frame, params, output_key)


def _rsi_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    period = max(int(params.get("period", 14) or 14), 1)
    close = _numeric_series(frame, "close")
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0)


def _rsi(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("rsi", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _rsi_pandas(frame, params, output_key)


def _kdj_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    fastk = max(int(params.get("fastk", 9) or 9), 1)
    slowk = max(int(params.get("slowk", 3) or 3), 1)
    slowd = max(int(params.get("slowd", 3) or 3), 1)
    high = _numeric_series(frame, "high")
    low = _numeric_series(frame, "low")
    close = _numeric_series(frame, "close")
    lowest = low.rolling(fastk).min()
    highest = high.rolling(fastk).max()
    rsv = ((close - lowest) / (highest - lowest).replace(0, np.nan) * 100).fillna(0)
    k = rsv.ewm(alpha=1 / slowk, adjust=False).mean()
    d = k.ewm(alpha=1 / slowd, adjust=False).mean()
    j = 3 * k - 2 * d
    mapping = {"k": k, "d": d, "j": j}
    return mapping[output_key]


def _kdj(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("kdj", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _kdj_pandas(frame, params, output_key)


def _boll_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    period = max(int(params.get("period", 20) or 20), 1)
    std_mult = float(params.get("std", 2.0) or 2.0)
    close = _numeric_series(frame, "close")
    mid = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    mapping = {"upper": upper, "mid": mid, "lower": lower}
    return mapping[output_key]


def _boll(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("boll", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _boll_pandas(frame, params, output_key)


def _atr_pandas(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    period = max(int(params.get("period", 14) or 14), 1)
    high = _numeric_series(frame, "high")
    low = _numeric_series(frame, "low")
    close = _numeric_series(frame, "close")
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _atr(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    vectorbt_series = compute_vectorbt_metric("atr", frame, params, output_key)
    if vectorbt_series is not None:
        return vectorbt_series
    return _atr_pandas(frame, params, output_key)


def _cci(frame: pd.DataFrame, params: dict, output_key: str) -> pd.Series:
    period = max(int(params.get("period", 14) or 14), 1)
    high = _numeric_series(frame, "high")
    low = _numeric_series(frame, "low")
    close = _numeric_series(frame, "close")
    tp = (high + low + close) / 3
    sma = tp.rolling(period).mean()
    mad = (tp - sma).abs().rolling(period).mean()
    return (tp - sma) / (0.015 * mad.replace(0, np.nan))


METRICS = [
    SelectionMetricDefinition(
        key="ma",
        label="MA",
        category="technical",
        description="简单移动平均线",
        compute=_ma,
        outputs=(SelectionOutputDefinition(key="value", label="MA"),),
        operators=RELATIONAL_OPERATORS,
        params=(SelectionParamDefinition(key="period", label="周期", default=20, minimum=1, maximum=250, step=1),),
    ),
    SelectionMetricDefinition(
        key="ema",
        label="EMA",
        category="technical",
        description="指数移动平均线",
        compute=_ema,
        outputs=(SelectionOutputDefinition(key="value", label="EMA"),),
        operators=RELATIONAL_OPERATORS,
        params=(SelectionParamDefinition(key="period", label="周期", default=20, minimum=1, maximum=250, step=1),),
    ),
    SelectionMetricDefinition(
        key="macd",
        label="MACD",
        category="technical",
        description="MACD 指标，支持 line/signal/hist 三输出",
        compute=_macd,
        outputs=(
            SelectionOutputDefinition(key="macd", label="MACD"),
            SelectionOutputDefinition(key="signal", label="Signal"),
            SelectionOutputDefinition(key="hist", label="Hist"),
        ),
        operators=RELATIONAL_OPERATORS,
        params=(
            SelectionParamDefinition(key="fast", label="快线", default=12, minimum=1, maximum=120, step=1),
            SelectionParamDefinition(key="slow", label="慢线", default=26, minimum=2, maximum=250, step=1),
            SelectionParamDefinition(key="signal", label="信号线", default=9, minimum=1, maximum=120, step=1),
        ),
        default_output="macd",
    ),
    SelectionMetricDefinition(
        key="rsi",
        label="RSI",
        category="technical",
        description="相对强弱指标",
        compute=_rsi,
        outputs=(SelectionOutputDefinition(key="value", label="RSI"),),
        operators=DEFAULT_COMPARISON_OPERATORS,
        params=(SelectionParamDefinition(key="period", label="周期", default=14, minimum=1, maximum=120, step=1),),
    ),
    SelectionMetricDefinition(
        key="kdj",
        label="KDJ",
        category="technical",
        description="随机指标，支持 K/D/J 输出",
        compute=_kdj,
        outputs=(
            SelectionOutputDefinition(key="k", label="K"),
            SelectionOutputDefinition(key="d", label="D"),
            SelectionOutputDefinition(key="j", label="J"),
        ),
        operators=RELATIONAL_OPERATORS,
        params=(
            SelectionParamDefinition(key="fastk", label="RSV 周期", default=9, minimum=1, maximum=120, step=1),
            SelectionParamDefinition(key="slowk", label="K 平滑", default=3, minimum=1, maximum=20, step=1),
            SelectionParamDefinition(key="slowd", label="D 平滑", default=3, minimum=1, maximum=20, step=1),
        ),
        default_output="k",
    ),
    SelectionMetricDefinition(
        key="boll",
        label="BOLL",
        category="technical",
        description="布林带，支持 upper/mid/lower 输出",
        compute=_boll,
        outputs=(
            SelectionOutputDefinition(key="upper", label="上轨"),
            SelectionOutputDefinition(key="mid", label="中轨"),
            SelectionOutputDefinition(key="lower", label="下轨"),
        ),
        operators=RELATIONAL_OPERATORS,
        params=(
            SelectionParamDefinition(key="period", label="周期", default=20, minimum=1, maximum=250, step=1),
            SelectionParamDefinition(key="std", label="标准差", default=2.0, minimum=0.5, maximum=5.0, step=0.1),
        ),
        default_output="mid",
    ),
    SelectionMetricDefinition(
        key="atr",
        label="ATR",
        category="technical",
        description="平均真实波幅",
        compute=_atr,
        outputs=(SelectionOutputDefinition(key="value", label="ATR"),),
        operators=DEFAULT_COMPARISON_OPERATORS,
        params=(SelectionParamDefinition(key="period", label="周期", default=14, minimum=1, maximum=120, step=1),),
    ),
    SelectionMetricDefinition(
        key="cci",
        label="CCI",
        category="technical",
        description="顺势指标",
        compute=_cci,
        outputs=(SelectionOutputDefinition(key="value", label="CCI"),),
        operators=DEFAULT_COMPARISON_OPERATORS,
        params=(SelectionParamDefinition(key="period", label="周期", default=14, minimum=1, maximum=120, step=1),),
    ),
]
