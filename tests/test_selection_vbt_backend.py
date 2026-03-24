import numpy as np
import pandas as pd
import pandas.testing as pdt

from app.selection.backends.vectorbt import compute_vectorbt_metric, get_vectorbt_backend
from app.selection.catalog import technical, volume


def make_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=40, freq="D")
    close = pd.Series(np.linspace(10, 20, 40) + np.sin(np.arange(40)), index=index)
    return pd.DataFrame(
        {
            "open": close - 0.4,
            "high": close + 1.2,
            "low": close - 1.1,
            "close": close,
            "volume": np.linspace(1000, 10000, 40),
        },
        index=index,
    )


def test_vectorbt_backend_computes_core_metrics():
    frame = make_frame()
    backend = get_vectorbt_backend()

    assert backend is not None

    ma = compute_vectorbt_metric("ma", frame, {"period": 5}, "value")
    ema = compute_vectorbt_metric("ema", frame, {"period": 5}, "value")
    macd = compute_vectorbt_metric("macd", frame, {"fast": 12, "slow": 26, "signal": 9}, "macd")
    kdj_j = compute_vectorbt_metric("kdj", frame, {"fastk": 9, "slowk": 3, "slowd": 3}, "j")
    volume_ma = compute_vectorbt_metric("volume_ma", frame, {"period": 5}, "value")

    assert ma is not None and ema is not None and macd is not None and kdj_j is not None and volume_ma is not None
    assert ma.index.equals(frame.index)
    assert ema.index.equals(frame.index)
    assert macd.index.equals(frame.index)
    assert kdj_j.index.equals(frame.index)
    assert volume_ma.index.equals(frame.index)
    assert ma.notna().sum() > 0
    assert ema.notna().sum() > 0
    assert macd.notna().sum() > 0
    assert kdj_j.notna().sum() > 0
    assert volume_ma.notna().sum() > 0


def test_technical_wrappers_prefer_vectorbt_backend(monkeypatch):
    frame = make_frame()
    expected = pd.Series(np.arange(len(frame), dtype=float), index=frame.index)

    monkeypatch.setattr(technical, "compute_vectorbt_metric", lambda *args, **kwargs: expected)

    result = technical.METRICS[0].compute(frame, {"period": 5}, "value")

    assert result is expected


def test_volume_ma_wrapper_falls_back_without_vectorbt(monkeypatch):
    frame = make_frame()

    monkeypatch.setattr(volume, "compute_vectorbt_metric", lambda *args, **kwargs: None)

    result = volume.METRICS[-1].compute(frame, {"period": 5}, "value")
    expected = frame["volume"].rolling(5).mean()

    pdt.assert_series_equal(result, expected)
