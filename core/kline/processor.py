#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线处理模块

提供K线数据处理和分析功能
"""

import logging
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Trend(Enum):
    """趋势方向"""

    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class CandleType(Enum):
    """蜡烛形态"""

    DOJI = "doji"  # 十字星
    HAMMER = "hammer"  # 锤子线
    INVERTED_HAMMER = "inverted_hammer"  # 倒锤子线
    BULLISH_ENGULFING = "bullish_engulfing"  #  bullish engulfing
    BEARISH_ENGULFING = "bearish_engulfing"  # bearish engulfing
    MORNING_STAR = "morning_star"  #  morning star
    EVENING_STAR = "evening_star"  #  evening star
    THREE_WHITE_SOLDIERS = "three_white_soldiers"  #  three white soldiers
    THREE_BLACK_CROWS = "three_black_crows"  #  three black crows
    SHOOTING_STAR = "shooting_star"  #  shooting star
    HANGING_MAN = "hanging_man"  #  hanging man


@dataclass
class KlineData:
    """K线数据"""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float = 0
    change_pct: float = 0
    turnover_rate: float = 0

    @property
    def body(self) -> float:
        """K线实体大小"""
        return abs(self.close - self.open)

    @property
    def body_top(self) -> float:
        """实体顶部"""
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        """实体底部"""
        return min(self.open, self.close)

    @property
    def upper_shadow(self) -> float:
        """上影线"""
        return self.high - self.body_top

    @property
    def lower_shadow(self) -> float:
        """下影线"""
        return self.body_bottom - self.low

    @property
    def is_bullish(self) -> bool:
        """是否阳线"""
        return self.close >= self.open

    @property
    def is_bearish(self) -> bool:
        """是否阴线"""
        return self.close < self.open

    @property
    def body_ratio(self) -> float:
        """实体占比"""
        total = self.high - self.low
        if total == 0:
            return 0
        return self.body / total

    @property
    def upper_shadow_ratio(self) -> float:
        """上影线占比"""
        total = self.high - self.low
        if total == 0:
            return 0
        return self.upper_shadow / total

    @property
    def lower_shadow_ratio(self) -> float:
        """下影线占比"""
        total = self.high - self.low
        if total == 0:
            return 0
        return self.lower_shadow / total

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "change_pct": self.change_pct,
            "turnover_rate": self.turnover_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KlineData":
        """从字典创建"""
        return cls(
            date=data.get("date", ""),
            open=float(data.get("open", 0)),
            high=float(data.get("high", 0)),
            low=float(data.get("low", 0)),
            close=float(data.get("close", 0)),
            volume=int(data.get("volume", 0)),
            amount=float(data.get("amount", 0)),
            change_pct=float(data.get("change_pct", 0)),
            turnover_rate=float(data.get("turnover_rate", 0)),
        )


class KlineProcessor:
    """K线处理器"""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        self.df: pd.DataFrame = pd.DataFrame()
        if data:
            self.load_data(data)

    def load_data(self, data: List[Dict[str, Any]]):
        """加载数据"""
        if not data:
            self.df = pd.DataFrame()
            return

        self.df = pd.DataFrame(data)
        if "date" in self.df.columns:
            self.df["date"] = pd.to_datetime(self.df["date"])
            self.df = self.df.sort_values("date").reset_index(drop=True)

    def to_klines(self) -> List[KlineData]:
        """转换为KlineData列表"""
        if self.df.empty:
            return []

        result = []
        for _, row in self.df.iterrows():
            result.append(
                KlineData(
                    date=row["date"].strftime("%Y-%m-%d")
                    if isinstance(row["date"], pd.Timestamp)
                    else str(row["date"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    amount=float(row.get("amount", 0)),
                    change_pct=float(row.get("change_pct", 0)),
                    turnover_rate=float(row.get("turnover_rate", 0)),
                )
            )
        return result

    def resample(
        self,
        target_period: str,
        agg_func: Optional[Dict[str, str]] = None,
    ) -> "KlineProcessor":
        """
        重采样K线

        Args:
            target_period: 目标周期 (5min, 15min, 30min, 60min, daily, weekly, monthly)
            agg_func: 聚合函数
        """
        if self.df.empty:
            return KlineProcessor()

        period_map = {
            "5min": "5T",
            "15min": "15T",
            "30min": "30T",
            "60min": "60T",
            "daily": "D",
            "weekly": "W",
            "monthly": "M",
            "quarterly": "Q",
            "yearly": "Y",
        }

        target = period_map.get(target_period, "D")

        default_agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "amount": "sum",
            "change_pct": "last",
            "turnover_rate": "last",
        }
        if agg_func:
            default_agg.update(agg_func)

        resampled = self.df.set_index("date").resample(target).agg(default_agg)
        resampled = resampled.dropna().reset_index()

        return KlineProcessor(resampled.to_dict("records"))

    def merge_klines(
        self,
        small_klines: List[KlineData],
        target_count: int,
    ) -> List[KlineData]:
        """
        合并小周期K线为大周期

        Args:
            small_klines: 小周期K线列表
            target_count: 每几条合并为一条
        """
        if not small_klines or target_count <= 1:
            return small_klines

        merged = []
        for i in range(0, len(small_klines), target_count):
            group = small_klines[i : i + target_count]
            if not group:
                continue

            first = group[0]
            last = group[-1]

            merged.append(
                KlineData(
                    date=last.date,
                    open=first.open,
                    high=max(k.high for k in group),
                    low=min(k.low for k in group),
                    close=last.close,
                    volume=sum(k.volume for k in group),
                    amount=sum(k.amount for k in group),
                )
            )

        return merged

    def detect_trend(self, window: int = 20) -> Trend:
        """
        检测趋势

        Args:
            window: 窗口大小
        """
        if len(self.df) < window:
            return Trend.SIDEWAYS

        prices = self.df["close"].tail(window).values
        if len(prices) < 2:
            return Trend.SIDEWAYS

        # 计算斜率
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)

        # 计算波动率
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)

        # 趋势阈值
        if slope > volatility * 0.5:
            return Trend.UP
        elif slope < -volatility * 0.5:
            return Trend.DOWN
        return Trend.SIDEWAYS

    def detect_support_resistance(
        self,
        window: int = 20,
        tolerance: float = 0.02,
    ) -> Tuple[List[float], List[float]]:
        """
        检测支撑和阻力位

        Args:
            window: 窗口大小
            tolerance: 容差比例
        """
        if len(self.df) < window:
            return [], []

        prices = self.df["close"].values
        supports = []
        resistances = []

        # 找局部最低和最高
        for i in range(window, len(prices) - window):
            left = prices[i - window : i]
            right = prices[i : i + window]
            current = prices[i]

            # 支撑：局部最低
            if current <= min(left) and current <= min(right):
                supports.append(current)

            # 阻力：局部最高
            if current >= max(left) and current >= max(right):
                resistances.append(current)

        # 聚类相近的价格
        supports = self._cluster_prices(supports, tolerance)
        resistances = self._cluster_prices(resistances, tolerance)

        return sorted(supports)[:10], sorted(resistances)[:10]

    def _cluster_prices(
        self,
        prices: List[float],
        tolerance: float = 0.02,
    ) -> List[float]:
        """聚类相近价格"""
        if not prices:
            return []

        prices = sorted(prices)
        clusters = []

        for price in prices:
            added = False
            for cluster in clusters:
                if abs(price - cluster) / cluster <= tolerance:
                    cluster = (cluster + price) / 2
                    clusters[clusters.index(cluster) - 1] = cluster
                    added = True
                    break
            if not added:
                clusters.append(price)

        return clusters

    def detect_gaps(self, min_gap: float = 0.02) -> List[Dict[str, Any]]:
        """
        检测跳空缺口

        Args:
            min_gap: 最小缺口比例
        """
        gaps = []

        for i in range(1, len(self.df)):
            prev_close = self.df.iloc[i - 1]["close"]
            curr_open = self.df.iloc[i]["open"]

            gap = (curr_open - prev_close) / prev_close

            if abs(gap) >= min_gap:
                gaps.append(
                    {
                        "date": str(self.df.iloc[i]["date"]),
                        "gap_pct": gap * 100,
                        "gap_type": "up" if gap > 0 else "down",
                        "size": abs(gap) * 100,
                    }
                )

        return gaps

    def calculate_volatility(
        self,
        window: int = 20,
        method: str = "std",
    ) -> float:
        """
        计算波动率

        Args:
            window: 窗口大小
            method: 计算方法 std/atr
        """
        if len(self.df) < window:
            return 0

        if method == "std":
            returns = self.df["close"].pct_change().tail(window)
            return returns.std() * np.sqrt(252)  # 年化波动率
        elif method == "atr":
            return self._calculate_atr(window)
        return 0

    def _calculate_atr(self, window: int = 14) -> float:
        """计算ATR"""
        if len(self.df) < window + 1:
            return 0

        high = self.df["high"].values
        low = self.df["low"].values
        close = self.df["close"].values

        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                abs(high[1:] - close[:-1]),
                abs(low[1:] - close[:-1]),
            ),
        )
        return np.mean(tr[-window:])

    def find_pivots(
        self,
        window: int = 5,
        tolerance: float = 0.001,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        寻找极值点（枢轴）

        Args:
            window: 前后窗口大小
            tolerance: 容差
        """
        highs = []
        lows = []

        for i in range(window, len(self.df) - window):
            current_high = self.df.iloc[i]["high"]
            current_low = self.df.iloc[i]["low"]

            # 局部最高
            left_highs = self.df.iloc[i - window : i]["high"].values
            right_highs = self.df.iloc[i + 1 : i + window + 1]["high"].values

            if current_high >= max(left_highs) and current_high >= max(right_highs):
                highs.append(
                    {
                        "index": i,
                        "date": str(self.df.iloc[i]["date"]),
                        "price": current_high,
                        "pivot_type": "high",
                    }
                )

            # 局部最低
            left_lows = self.df.iloc[i - window : i]["low"].values
            right_lows = self.df.iloc[i + 1 : i + window + 1]["low"].values

            if current_low <= min(left_lows) and current_low <= min(right_lows):
                lows.append(
                    {
                        "index": i,
                        "date": str(self.df.iloc[i]["date"]),
                        "price": current_low,
                        "pivot_type": "low",
                    }
                )

        return highs, lows

    @property
    def body_ratio(self) -> float:
        """K线实体占比"""
        if self.df.empty:
            return 0
        total = self.df["high"] - self.df["low"]
        body = abs(self.df["close"] - self.df["open"])
        return (body / total.replace(0, 1)).mean()
