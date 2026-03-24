from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    source = frame[column] if column in frame.columns else pd.Series(index=frame.index, dtype="float64")
    return pd.to_numeric(source, errors="coerce")


class VectorBTMetricBackend:
    name = "vectorbtpro"
    supported_metrics = frozenset({"ma", "ema", "volume_ma", "macd", "rsi", "kdj", "boll", "atr"})

    def __init__(self, module: Any) -> None:
        self.vbt = module

    def compute(
        self,
        metric_key: str,
        frame: pd.DataFrame,
        params: dict[str, Any],
        output_key: str,
    ) -> pd.Series | None:
        if metric_key not in self.supported_metrics:
            return None
        try:
            if metric_key == "ma":
                period = max(int(params.get("period", 20) or 20), 1)
                return self._as_series(self.vbt.MA.run(_numeric_series(frame, "close"), window=period).ma, frame.index)
            if metric_key == "ema":
                period = max(int(params.get("period", 20) or 20), 1)
                return self._as_series(
                    self.vbt.MA.run(_numeric_series(frame, "close"), window=period, wtype="exp").ma,
                    frame.index,
                )
            if metric_key == "volume_ma":
                period = max(int(params.get("period", 5) or 5), 1)
                return self._as_series(self.vbt.MA.run(_numeric_series(frame, "volume"), window=period).ma, frame.index)
            if metric_key == "macd":
                fast = max(int(params.get("fast", 12) or 12), 1)
                slow = max(int(params.get("slow", 26) or 26), fast + 1)
                signal = max(int(params.get("signal", 9) or 9), 1)
                macd = self.vbt.MACD.run(
                    _numeric_series(frame, "close"),
                    fast_window=fast,
                    slow_window=slow,
                    signal_window=signal,
                    wtype="exp",
                )
                mapping = {
                    "macd": macd.macd,
                    "signal": macd.signal,
                    "hist": macd.hist,
                }
                return self._as_series(mapping[output_key], frame.index)
            if metric_key == "rsi":
                period = max(int(params.get("period", 14) or 14), 1)
                return self._as_series(self.vbt.RSI.run(_numeric_series(frame, "close"), window=period).rsi, frame.index)
            if metric_key == "kdj":
                fastk = max(int(params.get("fastk", 9) or 9), 1)
                slowk = max(int(params.get("slowk", 3) or 3), 1)
                slowd = max(int(params.get("slowd", 3) or 3), 1)
                stoch = self.vbt.STOCH.run(
                    _numeric_series(frame, "high"),
                    _numeric_series(frame, "low"),
                    _numeric_series(frame, "close"),
                    fast_k_window=fastk,
                    slow_k_window=slowk,
                    slow_d_window=slowd,
                    slow_k_wtype="wilder",
                    slow_d_wtype="wilder",
                )
                slow_k = self._as_series(stoch.slow_k, frame.index)
                slow_d = self._as_series(stoch.slow_d, frame.index)
                mapping = {
                    "k": slow_k,
                    "d": slow_d,
                    "j": 3 * slow_k - 2 * slow_d,
                }
                return self._as_series(mapping[output_key], frame.index)
            if metric_key == "boll":
                period = max(int(params.get("period", 20) or 20), 1)
                std_mult = float(params.get("std", 2.0) or 2.0)
                bands = self.vbt.BBANDS.run(_numeric_series(frame, "close"), window=period, alpha=std_mult)
                mapping = {
                    "upper": bands.upper,
                    "mid": bands.middle,
                    "lower": bands.lower,
                }
                return self._as_series(mapping[output_key], frame.index)
            if metric_key == "atr":
                period = max(int(params.get("period", 14) or 14), 1)
                return self._as_series(
                    self.vbt.ATR.run(
                        _numeric_series(frame, "high"),
                        _numeric_series(frame, "low"),
                        _numeric_series(frame, "close"),
                        window=period,
                    ).atr,
                    frame.index,
                )
        except Exception:
            logger.debug("vectorbtpro metric compute failed for %s", metric_key, exc_info=True)
            return None
        return None

    @staticmethod
    def _as_series(value: Any, index: pd.Index) -> pd.Series:
        if isinstance(value, pd.Series):
            return value.reindex(index)
        if isinstance(value, pd.DataFrame):
            if value.shape[1] != 1:
                raise ValueError("Expected a single column DataFrame from vectorbtpro output")
            return value.iloc[:, 0].reindex(index)
        return pd.Series(value, index=index)


@lru_cache(maxsize=1)
def get_vectorbt_backend() -> VectorBTMetricBackend | None:
    try:
        import vectorbtpro as vbt
    except Exception:
        logger.debug("vectorbtpro is not available", exc_info=True)
        return None
    return VectorBTMetricBackend(vbt)


def compute_vectorbt_metric(
    metric_key: str,
    frame: pd.DataFrame,
    params: dict[str, Any],
    output_key: str,
) -> pd.Series | None:
    backend = get_vectorbt_backend()
    if backend is None:
        return None
    return backend.compute(metric_key, frame, params, output_key)
