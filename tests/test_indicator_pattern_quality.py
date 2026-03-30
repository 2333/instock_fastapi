from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import numpy as np

from app.jobs.tasks.indicator_task import _build_moving_average_indicators
from app.jobs.tasks import pattern_task


def _make_bar(index: int) -> SimpleNamespace:
    trade_date_dt = date(2024, 1, 1) + timedelta(days=index)
    close = Decimal(str(index + 1))
    return SimpleNamespace(
        trade_date=trade_date_dt.strftime("%Y%m%d"),
        trade_date_dt=trade_date_dt,
        close=close,
        open=close,
        high=close + Decimal("1"),
        low=close - Decimal("1"),
    )


def test_moving_average_records_require_full_window_and_use_correct_span():
    bars = [_make_bar(index) for index in range(60)]
    closes = np.array([float(bar.close) for bar in bars], dtype=np.float64)

    indicators = _build_moving_average_indicators("000001.SZ", bars, closes)

    latest_values = {
        item["indicator_name"]: item["indicator_value"]
        for item in indicators
        if item["trade_date"] == "20240229"
    }
    ma60_dates = [item["trade_date"] for item in indicators if item["indicator_name"] == "MA60"]

    assert latest_values == {
        "MA5": Decimal("58.0"),
        "MA10": Decimal("55.5"),
        "MA20": Decimal("50.5"),
        "MA60": Decimal("30.5"),
    }
    assert ma60_dates == ["20240229"]


def test_detect_patterns_marks_simple_uptrend_as_bullish_without_bearish_hits(monkeypatch):
    bars = []
    for index in range(30):
        base = Decimal(str(10 + index))
        bars.append(
            SimpleNamespace(
                open=base,
                high=base + Decimal("1.5"),
                low=base - Decimal("0.5"),
                close=base + Decimal("1"),
            )
        )

    zeros = np.zeros(len(bars), dtype=np.float64)
    talib_stub = SimpleNamespace(
        CDLHAMMER=lambda *_args: zeros,
        CDLINVERTEDHAMMER=lambda *_args: zeros,
        CDLDOJI=lambda *_args: zeros,
        CDLENGULFING=lambda *_args: zeros,
        CDLMORNINGSTAR=lambda *_args: zeros,
        CDLEVENINGSTAR=lambda *_args: zeros,
        CDL3WHITESOLDIERS=lambda *_args: zeros,
        CDL3BLACKCROWS=lambda *_args: zeros,
        CDLSPINNINGTOP=lambda *_args: zeros,
        CDLMARUBOZU=lambda *_args: zeros,
        CDLSHOOTINGSTAR=lambda *_args: zeros,
        CDLHARAMI=lambda *_args: zeros,
        CDLDRAGONFLYDOJI=lambda *_args: zeros,
        CDLGRAVESTONEDOJI=lambda *_args: zeros,
        CDLPIERCING=lambda *_args: zeros,
        CDLDARKCLOUDCOVER=lambda *_args: zeros,
        CDLHANGINGMAN=lambda *_args: zeros,
        CDLTRISTAR=lambda *_args: zeros,
        CDLTAKURI=lambda *_args: zeros,
    )
    monkeypatch.setattr(pattern_task, "tl", talib_stub)

    patterns = pattern_task.detect_patterns(bars)
    pattern_names = {item["pattern_name"] for item in patterns}

    assert {"BREAKTHROUGH_HIGH", "CONTINUOUS_RISE", "MA_GOLDEN_CROSS"} <= pattern_names
    assert "BREAKDOWN_LOW" not in pattern_names
    assert "CONTINUOUS_FALL" not in pattern_names
    assert "MA_DEATH_CROSS" not in pattern_names
