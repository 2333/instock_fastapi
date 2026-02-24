#!/usr/bin/env python3
"""
Pattern Recognition Module

Uses TA-Lib for reliable candlestick pattern recognition.
Chart patterns are implemented with custom algorithms.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import talib as tl

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Pattern types supported by TA-Lib and custom implementations"""

    # Candlestick patterns (TA-Lib)
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    DOJI = "doji"
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    SPINNING_TOP = "spinning_top"
    MARUBOZU = "marubozu"
    SHOOTING_STAR = "shooting_star"
    BULLISH_HARAMI = "bullish_harami"
    BEARISH_HARAMI = "bearish_harami"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    PIERCING = "piercing"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    HANGING_MAN = "hanging_man"
    THRISTAR = "tristar"
    TAKURI = "takuri"

    # Chart patterns (Custom implementation)
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIANGLE_SYMMETRIC = "triangle_symmetric"
    TRIANGLE_ASCENDING = "triangle_ascending"
    TRIANGLE_DESCENDING = "triangle_descending"
    FLAG_BULLISH = "flag_bullish"
    FLAG_BEARISH = "flag_bearish"


class PatternSignal(Enum):
    """Pattern signal direction"""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


# TA-Lib function mapping - only for candlestick patterns
_TALIB_PATTERNS = {
    PatternType.HAMMER: tl.CDLHAMMER,
    PatternType.INVERTED_HAMMER: tl.CDLINVERTEDHAMMER,
    PatternType.DOJI: tl.CDLDOJI,
    PatternType.BULLISH_ENGULFING: tl.CDLENGULFING,
    PatternType.BEARISH_ENGULFING: tl.CDLENGULFING,
    PatternType.MORNING_STAR: tl.CDLMORNINGSTAR,
    PatternType.EVENING_STAR: tl.CDLEVENINGSTAR,
    PatternType.THREE_WHITE_SOLDIERS: tl.CDL3WHITESOLDIERS,
    PatternType.THREE_BLACK_CROWS: tl.CDL3BLACKCROWS,
    PatternType.SPINNING_TOP: tl.CDLSPINNINGTOP,
    PatternType.MARUBOZU: tl.CDLMARUBOZU,
    PatternType.SHOOTING_STAR: tl.CDLSHOOTINGSTAR,
    PatternType.BULLISH_HARAMI: tl.CDLHARAMI,
    PatternType.BEARISH_HARAMI: tl.CDLHARAMI,
    PatternType.DRAGONFLY_DOJI: tl.CDLDRAGONFLYDOJI,
    PatternType.GRAVESTONE_DOJI: tl.CDLGRAVESTONEDOJI,
    PatternType.PIERCING: tl.CDLPIERCING,
    PatternType.DARK_CLOUD_COVER: tl.CDLDARKCLOUDCOVER,
    PatternType.HANGING_MAN: tl.CDLHANGINGMAN,
    PatternType.THRISTAR: tl.CDLTRISTAR,
    PatternType.TAKURI: tl.CDLTAKURI,
}

# Chart patterns that need custom implementation
_CHART_PATTERNS = {
    PatternType.HEAD_SHOULDERS,
    PatternType.INVERSE_HEAD_SHOULDERS,
    PatternType.DOUBLE_TOP,
    PatternType.DOUBLE_BOTTOM,
    PatternType.TRIANGLE_SYMMETRIC,
    PatternType.TRIANGLE_ASCENDING,
    PatternType.TRIANGLE_DESCENDING,
    PatternType.FLAG_BULLISH,
    PatternType.FLAG_BEARISH,
}


@dataclass
class PatternConfig:
    """Pattern recognition configuration"""

    min_confidence: float = 50.0
    min_bars: int = 30
    only_recent: bool = True
    recent_days: int = 5


@dataclass
class DetectedPattern:
    """Detected pattern result"""

    pattern_type: PatternType
    signal: PatternSignal
    date: str
    confidence: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PatternRecognizer:
    """Pattern recognizer using TA-Lib and custom algorithms"""

    def __init__(
        self, data: Optional[List[Dict[str, Any]]] = None, config: Optional[PatternConfig] = None
    ):
        self.config = config or PatternConfig()
        self.df: pd.DataFrame = pd.DataFrame()
        if data:
            self.load_data(data)

    def load_data(self, data: List[Dict[str, Any]]):
        """Load K-line data"""
        if not data:
            self.df = pd.DataFrame()
            return

        self.df = pd.DataFrame(data)
        required_cols = ["trade_date", "open", "high", "low", "close", "volume"]

        for col in required_cols:
            if col not in self.df.columns:
                self.df[col] = 0

        if "trade_date" in self.df.columns:
            self.df["trade_date"] = pd.to_datetime(self.df["trade_date"])
            self.df = self.df.sort_values("trade_date").reset_index(drop=True)

    def recognize_all(
        self,
        pattern_types: Optional[List[PatternType]] = None,
    ) -> List[DetectedPattern]:
        """Recognize all specified patterns"""
        if self.df.empty:
            return []

        if pattern_types is None:
            pattern_types = list(PatternType)

        results = []
        for pattern_type in pattern_types:
            if pattern_type in _TALIB_PATTERNS:
                patterns = self._recognize_talib_pattern(pattern_type)
                results.extend(patterns)
            elif pattern_type in _CHART_PATTERNS:
                patterns = self._recognize_chart_pattern(pattern_type)
                results.extend(patterns)

        results.sort(key=lambda p: p.date, reverse=True)
        return results

    def _recognize_talib_pattern(self, pattern_type: PatternType) -> List[DetectedPattern]:
        """Recognize a single pattern using TA-Lib"""
        func = _TALIB_PATTERNS.get(pattern_type)
        if func is None:
            return []

        open_price = self.df["open"].values.astype(float)
        high_price = self.df["high"].values.astype(float)
        low_price = self.df["low"].values.astype(float)
        close_price = self.df["close"].values.astype(float)

        try:
            results = func(open_price, high_price, low_price, close_price)
        except Exception as e:
            logger.error(f"TA-Lib pattern recognition failed for {pattern_type}: {e}")
            return []

        patterns = []
        min_confidence = self.config.min_confidence

        for i, signal in enumerate(results):
            if signal == 0:
                continue

            if self.config.only_recent:
                recent_mask = self.df["trade_date"] >= pd.Timestamp.now() - pd.Timedelta(
                    days=self.config.recent_days
                )
                if not recent_mask.iloc[i]:
                    continue

            if abs(signal) * 2 < min_confidence:
                continue

            # Determine signal direction based on pattern type and signal value
            direction = self._get_signal_direction(pattern_type, signal)

            date_str = (
                str(self.df.iloc[i]["trade_date"])[:10] if "trade_date" in self.df.columns else ""
            )

            patterns.append(
                DetectedPattern(
                    pattern_type=pattern_type,
                    signal=direction,
                    date=date_str,
                    confidence=abs(signal) * 2,
                    open_price=open_price[i],
                    high_price=high_price[i],
                    low_price=low_price[i],
                    close_price=close_price[i],
                    description=self._get_description(pattern_type, direction),
                    metadata={"talib_signal": int(signal)},
                )
            )

        return patterns

    def _get_signal_direction(self, pattern_type: PatternType, signal: int) -> PatternSignal:
        """Determine signal direction from pattern type and TA-Lib signal"""
        # Engulfing patterns: positive = bullish, negative = bearish
        if pattern_type in (
            PatternType.BULLISH_ENGULFING,
            PatternType.BULLISH_HARAMI,
            PatternType.MORNING_STAR,
            PatternType.PIERCING,
            PatternType.DRAGONFLY_DOJI,
            PatternType.THRISTAR,
            PatternType.TAKURI,
        ):
            return PatternSignal.BULLISH if signal > 0 else PatternSignal.BEARISH

        # Bearish patterns
        if pattern_type in (
            PatternType.BEARISH_ENGULFING,
            PatternType.BEARISH_HARAMI,
            PatternType.EVENING_STAR,
            PatternType.DARK_CLOUD_COVER,
            PatternType.SHOOTING_STAR,
            PatternType.GRAVESTONE_DOJI,
            PatternType.HANGING_MAN,
        ):
            return PatternSignal.BEARISH if signal < 0 else PatternSignal.BULLISH

        # Three soldiers/crows
        if pattern_type == PatternType.THREE_WHITE_SOLDIERS:
            return PatternSignal.BULLISH if signal > 0 else PatternSignal.NEUTRAL
        if pattern_type == PatternType.THREE_BLACK_CROWS:
            return PatternSignal.BEARISH if signal < 0 else PatternSignal.NEUTRAL

        # Simple patterns
        if pattern_type in (
            PatternType.HAMMER,
            PatternType.INVERTED_HAMMER,
            PatternType.DOJI,
            PatternType.SPINNING_TOP,
            PatternType.MARUBOZU,
        ):
            return (
                PatternSignal.BULLISH
                if signal > 0
                else PatternSignal.BEARISH
                if signal < 0
                else PatternSignal.NEUTRAL
            )

        return PatternSignal.NEUTRAL

    def _recognize_chart_pattern(self, pattern_type: PatternType) -> List[DetectedPattern]:
        """Recognize chart patterns using custom algorithms"""
        highs = self.df["high"].values.astype(float)
        lows = self.df["low"].values.astype(float)
        closes = self.df["close"].values.astype(float)
        dates = (
            self.df["trade_date"].values if "trade_date" in self.df.columns else ["" for _ in highs]
        )

        patterns = []
        min_bars = self.config.min_bars
        n = len(highs)

        if n < min_bars:
            return []

        if pattern_type == PatternType.HEAD_SHOULDERS:
            patterns = self._find_head_shoulders(highs, lows, closes, dates, bullish=False)
        elif pattern_type == PatternType.INVERSE_HEAD_SHOULDERS:
            patterns = self._find_head_shoulders(highs, lows, closes, dates, bullish=True)
        elif pattern_type == PatternType.DOUBLE_TOP:
            patterns = self._find_double_pattern(highs, lows, closes, dates, bullish=False)
        elif pattern_type == PatternType.DOUBLE_BOTTOM:
            patterns = self._find_double_pattern(highs, lows, closes, dates, bullish=True)

        return patterns

    def _find_head_shoulders(
        self, highs, lows, closes, dates, bullish: bool = True
    ) -> List[DetectedPattern]:
        """Find head and shoulders pattern"""
        patterns = []
        n = len(highs)
        tolerance = 0.03

        for i in range(20, n):
            if bullish:
                troughs = self._find_local_minima(lows, max(0, i - 60), i)
                if len(troughs) >= 3:
                    left_shoulder = troughs[0]
                    head = troughs[-1]
                    right_shoulder = troughs[1] if len(troughs) > 1 else None
                    if right_shoulder and left_shoulder < head and right_shoulder < head:
                        neckline = min(lows[left_shoulder : right_shoulder + 10])
                        if left_shoulder > neckline * 1.02 and right_shoulder > neckline * 1.02:
                            patterns.append(
                                DetectedPattern(
                                    pattern_type=PatternType.INVERSE_HEAD_SHOULDERS
                                    if bullish
                                    else PatternType.HEAD_SHOULDERS,
                                    signal=PatternSignal.BULLISH
                                    if bullish
                                    else PatternSignal.BEARISH,
                                    date=str(dates[i])[:10],
                                    confidence=75.0,
                                    open_price=closes[i - 5],
                                    high_price=head,
                                    low_price=neckline,
                                    close_price=closes[i],
                                    description="头肩底形态" if bullish else "头肩顶形态",
                                )
                            )
            else:
                peaks = self._find_local_maxima(highs, max(0, i - 60), i)
                if len(peaks) >= 3:
                    left_shoulder = peaks[0]
                    head = peaks[-1]
                    right_shoulder = peaks[1] if len(peaks) > 1 else None
                    if right_shoulder and left_shoulder > head and right_shoulder > head:
                        neckline = max(highs[left_shoulder : right_shoulder + 10])
                        if left_shoulder < neckline * 0.98 and right_shoulder < neckline * 0.98:
                            patterns.append(
                                DetectedPattern(
                                    pattern_type=PatternType.HEAD_SHOULDERS,
                                    signal=PatternSignal.BEARISH,
                                    date=str(dates[i])[:10],
                                    confidence=75.0,
                                    open_price=closes[i - 5],
                                    high_price=neckline,
                                    low_price=head,
                                    close_price=closes[i],
                                    description="头肩顶形态",
                                )
                            )
        return patterns

    def _find_double_pattern(
        self, highs, lows, closes, dates, bullish: bool = True
    ) -> List[DetectedPattern]:
        """Find double top or double bottom pattern"""
        patterns = []
        tolerance = 0.02

        for i in range(20, len(highs)):
            if bullish:
                troughs = self._find_local_minima(lows, max(0, i - 60), i)
                if len(troughs) >= 2:
                    first = troughs[-2]
                    second = troughs[-1]
                    if first and second:
                        diff = abs(first - second) / first
                        if diff < tolerance:
                            patterns.append(
                                DetectedPattern(
                                    pattern_type=PatternType.DOUBLE_BOTTOM,
                                    signal=PatternSignal.BULLISH,
                                    date=str(dates[i])[:10],
                                    confidence=70.0,
                                    open_price=closes[i - 5],
                                    high_price=max(highs[first : second + 5]),
                                    low_price=min(lows[first : second + 5]),
                                    close_price=closes[i],
                                    description="双底形态",
                                )
                            )
            else:
                peaks = self._find_local_maxima(highs, max(0, i - 60), i)
                if len(peaks) >= 2:
                    first = peaks[-2]
                    second = peaks[-1]
                    if first and second:
                        diff = abs(first - second) / first
                        if diff < tolerance:
                            patterns.append(
                                DetectedPattern(
                                    pattern_type=PatternType.DOUBLE_TOP,
                                    signal=PatternSignal.BEARISH,
                                    date=str(dates[i])[:10],
                                    confidence=70.0,
                                    open_price=closes[i - 5],
                                    high_price=max(highs[first : second + 5]),
                                    low_price=min(lows[first : second + 5]),
                                    close_price=closes[i],
                                    description="双顶形态",
                                )
                            )
        return patterns

    def _find_local_maxima(self, arr, start, end, window=5):
        """Find local maxima indices"""
        maxima = []
        for i in range(start + window, end - window):
            is_max = True
            for j in range(max(start, i - window), min(end, i + window + 1)):
                if j != i and arr[j] >= arr[i]:
                    is_max = False
                    break
            if is_max:
                maxima.append(i)
        return maxima

    def _find_local_minima(self, arr, start, end, window=5):
        """Find local minima indices"""
        minima = []
        for i in range(start + window, end - window):
            is_min = True
            for j in range(max(start, i - window), min(end, i + window + 1)):
                if j != i and arr[j] <= arr[i]:
                    is_min = False
                    break
            if is_min:
                minima.append(i)
        return minima

    def _get_description(self, pattern_type: PatternType, signal: PatternSignal) -> str:
        """Get human-readable pattern description"""
        names = {
            PatternType.HAMMER: "锤子线",
            PatternType.INVERTED_HAMMER: "倒锤子线",
            PatternType.DOJI: "十字星",
            PatternType.BULLISH_ENGULFING: "看涨吞没",
            PatternType.BEARISH_ENGULFING: "看跌吞没",
            PatternType.MORNING_STAR: "晨星",
            PatternType.EVENING_STAR: "夜星",
            PatternType.THREE_WHITE_SOLDIERS: "红三兵",
            PatternType.THREE_BLACK_CROWS: "黑三鸦",
            PatternType.SPINNING_TOP: "纺锤线",
            PatternType.MARUBOZU: "光头光脚",
            PatternType.SHOOTING_STAR: "射击之星",
            PatternType.BULLISH_HARAMI: "看涨孕线",
            PatternType.BEARISH_HARAMI: "看跌孕线",
            PatternType.HEAD_SHOULDERS: "头肩顶",
            PatternType.INVERSE_HEAD_SHOULDERS: "头肩底",
            PatternType.DOUBLE_TOP: "双顶",
            PatternType.DOUBLE_BOTTOM: "双底",
        }

        name = names.get(pattern_type, pattern_type.value)
        direction = (
            "看涨"
            if signal == PatternSignal.BULLISH
            else "看跌"
            if signal == PatternSignal.BEARISH
            else "中性"
        )
        return f"{direction} {name}形态"

    def get_summary(self, patterns: List[DetectedPattern]) -> Dict[str, Any]:
        """Get pattern recognition summary"""
        if not patterns:
            return {"total": 0, "bullish": 0, "bearish": 0, "neutral": 0}

        return {
            "total": len(patterns),
            "bullish": len([p for p in patterns if p.signal == PatternSignal.BULLISH]),
            "bearish": len([p for p in patterns if p.signal == PatternSignal.BEARISH]),
            "neutral": len([p for p in patterns if p.signal == PatternSignal.NEUTRAL]),
        }


def recognize_patterns(
    data: List[Dict[str, Any]],
    pattern_types: Optional[List[PatternType]] = None,
    min_confidence: float = 50.0,
    only_recent: bool = True,
) -> List[DetectedPattern]:
    """Convenience function for pattern recognition"""
    config = PatternConfig(min_confidence=min_confidence, only_recent=only_recent)
    recognizer = PatternRecognizer(data, config)
    return recognizer.recognize_all(pattern_types)
