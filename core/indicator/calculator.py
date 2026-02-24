#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标计算模块

提供各种技术指标的计算功能
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
from functools import wraps

import numpy as np
import pandas as pd
import talib as tl

logger = logging.getLogger(__name__)


class IndicatorType(Enum):
    """指标类型"""

    # 趋势指标
    MA = "ma"  # 移动平均线
    EMA = "ema"  # 指数移动平均线
    MACD = "macd"  # MACD
    ADX = "adx"  # Average Directional Index
    AROON = "aroon"  # Aroon
    AD = "ad"  # Accumulation/Distribution
    OBV = "obv"  # On-Balance Volume

    # 动量指标
    RSI = "rsi"  # Relative Strength Index
    KDJ = "kdj"  # Stochastic Oscillator
    CCI = "cci"  # Commodity Channel Index
    ROC = "roc"  # Rate of Change
    MOM = "momentum"  # Momentum
    WILLR = "williams_%r"  # Williams %R

    # 波动率指标
    BOLL = "boll"  # Bollinger Bands
    ATR = "atr"  # Average True Range
    KC = "kc"  # Keltner Channel
    VR = "vr"  # Volatility Ratio

    # 量能指标
    VOL = "volume"  # 成交量
    VOL_MA = "volume_ma"  # 成交量均线
    VR_SIMPLE = "vr"  #  VR指标

    # 综合评分
    SCORE = "score"  # 综合评分


@dataclass
class IndicatorConfig:
    """指标配置"""

    name: str
    period: int = 20
    param1: float = 2.0
    param2: float = 3.0
    enabled: bool = True


@dataclass
class IndicatorResult:
    """指标计算结果"""

    name: str
    value: float
    signal: str = "neutral"  # buy, sell, neutral
    timestamp: str = ""


@dataclass
class IndicatorSet:
    """指标集合"""

    code: str
    trade_date: str
    # 趋势指标
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ma120: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    adx: Optional[float] = None

    # 动量指标
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None
    cci: Optional[float] = None
    roc: Optional[float] = None
    mom: Optional[float] = None
    willr: Optional[float] = None

    # 波动率指标
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None
    atr: Optional[float] = None

    # 量能指标
    volume: Optional[int] = None
    volume_ma5: Optional[float] = None
    volume_ma10: Optional[float] = None
    vr: Optional[float] = None

    # 综合评分
    score: float = 50
    signal: str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result

    def to_list(self, columns: List[str]) -> List[Any]:
        """转换为列表"""
        return [self.__dict__.get(col) for col in columns]


class IndicatorCalculator:
    """技术指标计算器"""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        self.df: pd.DataFrame = pd.DataFrame()
        self._columns = ["trade_date", "open", "high", "low", "close", "volume"]

        if data:
            self.load_data(data)

    def load_data(self, data: List[Dict[str, Any]]):
        """加载数据"""
        if not data:
            self.df = pd.DataFrame()
            return

        # 确保所需列存在
        df = pd.DataFrame(data)
        for col in self._columns:
            if col not in df.columns:
                df[col] = 0

        # 排序
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df = df.sort_values("trade_date").reset_index(drop=True)

        self.df = df

    def _ensure_columns(self):
        """确保所需列存在"""
        if self.df.empty:
            return

        for col in self._columns:
            if col not in self.df.columns:
                self.df[col] = 0

    def _validate_data(func: Callable) -> Callable:
        """数据验证装饰器"""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._ensure_columns()
            if self.df.empty:
                return None
            return func(self, *args, **kwargs)

        return wrapper

    @_validate_data
    def calculate_all(self) -> IndicatorSet:
        """计算所有指标"""
        if self.df.empty:
            return IndicatorSet(code="", trade_date="")

        result = IndicatorSet(
            code=self.df.iloc[-1].get("ts_code", ""),
            trade_date=str(self.df.iloc[-1]["trade_date"])
            if "trade_date" in self.df.columns
            else "",
        )

        close = self.df["close"].values
        high = self.df["high"].values
        low = self.df["low"].values
        volume = self.df["volume"].values.astype(float)

        # 移动平均线
        result.ma5 = float(tl.MA(close, timeperiod=5)[-1]) if len(close) >= 5 else None
        result.ma10 = float(tl.MA(close, timeperiod=10)[-1]) if len(close) >= 10 else None
        result.ma20 = float(tl.MA(close, timeperiod=20)[-1]) if len(close) >= 20 else None
        result.ma60 = float(tl.MA(close, timeperiod=60)[-1]) if len(close) >= 60 else None
        result.ma120 = float(tl.MA(close, timeperiod=120)[-1]) if len(close) >= 120 else None

        # EMA
        result.ema12 = float(tl.EMA(close, timeperiod=12)[-1]) if len(close) >= 12 else None
        result.ema26 = float(tl.EMA(close, timeperiod=26)[-1]) if len(close) >= 26 else None

        # MACD
        if len(close) >= 26:
            macd, signal, hist = tl.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            result.macd = float(macd[-1])
            result.macd_signal = float(signal[-1])
            result.macd_hist = float(hist[-1])

        # ADX
        if len(close) >= 14:
            result.adx = float(tl.ADX(high, low, close, timeperiod=14)[-1])

        # RSI
        result.rsi6 = float(tl.RSI(close, timeperiod=6)[-1]) if len(close) >= 6 else None
        result.rsi12 = float(tl.RSI(close, timeperiod=12)[-1]) if len(close) >= 12 else None
        result.rsi24 = float(tl.RSI(close, timeperiod=24)[-1]) if len(close) >= 24 else None

        # KDJ
        if len(close) >= 9:
            k, d = tl.STOCH(
                high,
                low,
                close,
                fastk_period=9,
                slowk_period=3,
                slowk_matype=0,
                slowd_period=3,
                slowd_matype=0,
            )
            result.k = float(k[-1])
            result.d = float(d[-1])
            result.j = 3 * result.k - 2 * result.d if result.k and result.d else None

        # CCI
        if len(close) >= 14:
            result.cci = float(tl.CCI(high, low, close, timeperiod=14)[-1])

        # ROC
        result.roc = float(tl.ROC(close, timeperiod=10)[-1]) if len(close) >= 10 else None

        # Momentum
        result.mom = float(tl.MOM(close, timeperiod=10)[-1]) if len(close) >= 10 else None

        # Williams %R
        if len(close) >= 14:
            result.willr = float(tl.WILLR(high, low, close, timeperiod=14)[-1])

        # Bollinger Bands
        if len(close) >= 20:
            upper, mid, lower = tl.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
            result.boll_upper = float(upper[-1])
            result.boll_mid = float(mid[-1])
            result.boll_lower = float(lower[-1])

        # ATR
        if len(close) >= 14:
            result.atr = float(tl.ATR(high, low, close, timeperiod=14)[-1])

        # 成交量
        result.volume = int(self.df["volume"].iloc[-1]) if "volume" in self.df.columns else None

        # 成交量均线
        if len(volume) >= 5:
            result.volume_ma5 = float(tl.MA(volume, timeperiod=5)[-1])
        if len(volume) >= 10:
            result.volume_ma10 = float(tl.MA(volume, timeperiod=10)[-1])

        # VR指标
        if len(close) >= 24:
            vr = self._calculate_vr(volume, close)
            result.vr = vr

        # 综合评分
        result.score = self._calculate_score(result)
        result.signal = self._generate_signal(result)

        return result

    def _calculate_vr(self, volume: np.ndarray, close: np.ndarray) -> Optional[float]:
        """计算VR指标"""
        if len(close) < 24:
            return None

        change = np.diff(close)
        up = np.sum(change[change > 0])
        down = abs(np.sum(change[change < 0]))

        if down == 0:
            return None

        vr = up / (up + down) * 100
        return float(vr)

    def _calculate_score(self, indicators: IndicatorSet) -> float:
        """计算综合评分 (0-100)"""
        score = 50  # 基础分

        # 趋势评分 (MA)
        if indicators.ma5 and indicators.ma20:
            if indicators.ma5 > indicators.ma20:
                score += 5

        # RSI评分
        if indicators.rsi6:
            if indicators.rsi6 < 30:
                score += 5  # 超卖
            elif indicators.rsi6 > 70:
                score -= 5  # 超买
            elif 40 <= indicators.rsi6 <= 60:
                score += 3  # 中性

        # MACD评分
        if indicators.macd and indicators.macd_signal:
            if indicators.macd > indicators.macd_signal:
                score += 5
            if indicators.macd_hist > 0:
                score += 3

        # KDJ评分
        if indicators.k and indicators.d:
            if indicators.k < 20 and indicators.d < 20:
                score += 3  # 超卖
            elif indicators.k > 80 and indicators.d > 80:
                score -= 3  # 超买

        # 限制范围
        return max(0, min(100, score))

    def _generate_signal(self, indicators: IndicatorSet) -> str:
        """生成交易信号"""
        score = indicators.score

        if score >= 70:
            return "buy"
        elif score <= 30:
            return "sell"
        return "neutral"

    @_validate_data
    def calculate_ma(self, period: int) -> np.ndarray:
        """计算MA"""
        return tl.MA(self.df["close"].values, timeperiod=period)

    @_validate_data
    def calculate_ema(self, period: int) -> np.ndarray:
        """计算EMA"""
        return tl.EMA(self.df["close"].values, timeperiod=period)

    @_validate_data
    def calculate_macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """计算MACD"""
        return tl.MACD(
            self.df["close"].values,
            fastperiod=fast,
            slowperiod=slow,
            signalperiod=signal,
        )

    @_validate_data
    def calculate_rsi(self, period: int = 14) -> np.ndarray:
        """计算RSI"""
        return tl.RSI(self.df["close"].values, timeperiod=period)

    @_validate_data
    def calculate_kdj(
        self,
        fastk: int = 9,
        slowk: int = 3,
        slowd: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """计算KDJ"""
        return tl.STOCH(
            self.df["high"].values,
            self.df["low"].values,
            self.df["close"].values,
            fastk_period=fastk,
            slowk_period=slowk,
            slowk_matype=0,
            slowd_period=slowd,
            slowd_matype=0,
        )

    @_validate_data
    def calculate_boll(
        self,
        period: int = 20,
        std_dev: float = 2,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """计算布林带"""
        return tl.BBANDS(
            self.df["close"].values,
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev,
            matype=0,
        )

    @_validate_data
    def calculate_atr(self, period: int = 14) -> np.ndarray:
        """计算ATR"""
        return tl.ATR(
            self.df["high"].values,
            self.df["low"].values,
            self.df["close"].values,
            timeperiod=period,
        )

    @_validate_data
    def calculate_cci(self, period: int = 20) -> np.ndarray:
        """计算CCI"""
        return tl.CCI(
            self.df["high"].values,
            self.df["low"].values,
            self.df["close"].values,
            timeperiod=period,
        )

    @_validate_data
    def calculate_adx(self, period: int = 14) -> np.ndarray:
        """计算ADX"""
        return tl.ADX(
            self.df["high"].values,
            self.df["low"].values,
            self.df["close"].values,
            timeperiod=period,
        )

    @_validate_data
    def calculate_obv(self) -> np.ndarray:
        """计算OBV"""
        return tl.OBV(
            self.df["close"].values,
            self.df["volume"].values.astype(float),
        )

    @_validate_data
    def calculate_custom(
        self,
        indicator_type: IndicatorType,
        **params,
    ) -> np.ndarray:
        """计算自定义指标"""
        if indicator_type == IndicatorType.MA:
            return self.calculate_ma(params.get("period", 20))
        elif indicator_type == IndicatorType.EMA:
            return self.calculate_ema(params.get("period", 20))
        elif indicator_type == IndicatorType.MACD:
            macd, signal, _ = self.calculate_macd(
                params.get("fast", 12),
                params.get("slow", 26),
                params.get("signal", 9),
            )
            return macd
        elif indicator_type == IndicatorType.RSI:
            return self.calculate_rsi(params.get("period", 14))
        elif indicator_type == IndicatorType.BOLL:
            _, mid, _ = self.calculate_boll(
                params.get("period", 20),
                params.get("std_dev", 2),
            )
            return mid
        elif indicator_type == IndicatorType.ATR:
            return self.calculate_atr(params.get("period", 14))
        elif indicator_type == IndicatorType.CCI:
            return self.calculate_cci(params.get("period", 20))
        else:
            return np.array([])

    @property
    def latest(self) -> IndicatorSet:
        """获取最新指标"""
        return self.calculate_all()

    def to_pandas(self) -> pd.DataFrame:
        """转换为Pandas DataFrame"""
        if self.df.empty:
            return pd.DataFrame()

        result = self.df.copy()

        # 添加指标列
        result["ma5"] = self.calculate_ma(5)
        result["ma20"] = self.calculate_ma(20)
        result["ma60"] = self.calculate_ma(60)
        result["rsi"] = self.calculate_rsi(14)

        macd, signal, hist = self.calculate_macd()
        result["macd"] = macd
        result["macd_signal"] = signal
        result["macd_hist"] = hist

        upper, mid, lower = self.calculate_boll()
        result["boll_upper"] = upper
        result["boll_mid"] = mid
        result["boll_lower"] = lower

        result["atr"] = self.calculate_atr(14)

        return result
