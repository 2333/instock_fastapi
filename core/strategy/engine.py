#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略回测模块

提供完整的策略回测功能
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from collections import deque

import numpy as np
import pandas as pd

from ..kline.processor import KlineData
from ..indicator.calculator import IndicatorCalculator, IndicatorSet

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """持仓方向"""

    LONG = "long"
    SHORT = "short"
    NONE = "none"


class OrderType(Enum):
    """订单类型"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderAction(Enum):
    """订单动作"""

    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"


class TradeStatus(Enum):
    """交易状态"""

    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class TradeConfig:
    """回测配置"""

    initial_capital: float = 100000  # 初始资金
    position_size: float = 0.1  # 单次仓位比例
    max_position: float = 0.5  # 最大仓位
    stop_loss: Optional[float] = 0.05  # 止损比例
    take_profit: Optional[float] = 0.15  # 止盈比例
    slippage: float = 0.001  # 滑点
    commission_rate: float = 0.0003  # 佣金费率
    stamp_tax_rate: float = 0.001  # 印花税
    min_commission: float = 5.0  # 最低佣金

    # 交易频率限制
    min_hold_days: int = 1  # 最小持仓天数
    max_trades_per_day: int = 3  # 每日最大交易次数

    # 手续费模式
    commission_mode: str = "both"  # "both"买入卖出, "sell"仅卖出, "none"无手续费


@dataclass
class Order:
    """订单"""

    id: str
    action: OrderAction
    order_type: OrderType
    code: str
    quantity: int
    price: float
    stop_price: Optional[float] = None
    created_at: str = ""
    filled_at: Optional[str] = None
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    status: TradeStatus = TradeStatus.PENDING
    commission: float = 0
    remark: str = ""


@dataclass
class Trade:
    """成交记录"""

    id: str
    order_id: str
    code: str
    action: OrderAction
    quantity: int
    price: float
    total_value: float
    commission: float
    profit: float = 0
    created_at: str = ""
    closed_at: Optional[str] = None


@dataclass
class Position:
    """持仓"""

    code: str
    side: PositionSide
    quantity: int
    avg_price: float
    open_date: str
    open_price: float
    unrealized_profit: float = 0
    unrealized_profit_pct: float = 0


@dataclass
class BacktestResult:
    """回测结果"""

    # 基本信息
    backtest_id: str
    code: str
    start_date: str
    end_date: str
    total_days: int

    # 资金信息
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float

    # 收益率指标
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float

    # 交易统计
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float

    # 持仓信息
    max_position_held: int
    avg_position_held: float
    time_in_market: float

    # 详细信息
    trades: List[Trade] = field(default_factory=list)
    daily_returns: List[Dict] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "backtest_id": self.backtest_id,
            "code": self.code,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_days": self.total_days,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct * 100,
            "annualized_return": self.annualized_return * 100,
            "volatility": self.volatility * 100,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct * 100,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate * 100,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "max_position_held": self.max_position_held,
            "avg_position_held": self.avg_position_held,
            "time_in_market": self.time_in_market * 100,
        }


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        data: List[Dict[str, Any]],
        config: Optional[TradeConfig] = None,
    ):
        self.df = pd.DataFrame(data)
        if "date" in self.df.columns:
            self.df["date"] = pd.to_datetime(self.df["date"])
            self.df = self.df.sort_values("date").reset_index(drop=True)

        self.config = config or TradeConfig()
        self.indicator_calculator = IndicatorCalculator(data)

        # 回测状态
        self.cash: float = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[Dict] = []

        # 交易统计
        self.winning_trades: List[Trade] = []
        self.losing_trades: List[Trade] = []
        self.daily_trade_count: Dict[str, int] = {}
        self.last_trade_date: Optional[str] = None

        # 生成回测ID
        self.backtest_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def run(self) -> BacktestResult:
        """运行回测"""
        if self.df.empty:
            return self._create_empty_result()

        # 初始化权益曲线
        self.equity_curve = [
            {
                "date": str(self.df.iloc[0]["date"]),
                "equity": self.config.initial_capital,
                "cash": self.cash,
                "position_value": 0,
            }
        ]

        # 逐日回测
        for i, row in self.df.iterrows():
            date_str = str(row["date"])
            self._process_day(row, date_str)

            # 记录每日权益
            position_value = sum(pos.quantity * row["close"] for pos in self.positions.values())
            equity = self.cash + position_value

            self.equity_curve.append(
                {
                    "date": date_str,
                    "equity": equity,
                    "cash": self.cash,
                    "position_value": position_value,
                }
            )

        return self._calculate_result()

    def _process_day(self, row, date_str: str):
        """处理每日数据"""
        # 更新未实现盈亏
        for pos in self.positions.values():
            pos.unrealized_profit = (row["close"] - pos.avg_price) * pos.quantity
            pos.unrealized_profit_pct = (row["close"] - pos.avg_price) / pos.avg_price

        # 检查止损止盈
        self._check_stop_conditions(row, date_str)

        # 检查挂单
        self._check_orders(row, date_str)

        # 重置当日交易计数
        self.daily_trade_count[date_str] = 0

    def _check_stop_conditions(self, row, date_str: str):
        """检查止损止盈条件"""
        for pos_id, pos in list(self.positions.items()):
            if pos.side == PositionSide.LONG:
                # 多头止损
                if self.config.stop_loss and pos.unrealized_profit_pct <= -self.config.stop_loss:
                    self._close_position(pos_id, row, date_str, "止损")

                # 多头止盈
                elif (
                    self.config.take_profit and pos.unrealized_profit_pct >= self.config.take_profit
                ):
                    self._close_position(pos_id, row, date_str, "止盈")

            elif pos.side == PositionSide.SHORT:
                # 空头止损
                if self.config.stop_loss and pos.unrealized_profit_pct <= -self.config.stop_loss:
                    self._close_position(pos_id, row, date_str, "止损")

                # 空头止盈
                elif (
                    self.config.take_profit and pos.unrealized_profit_pct >= self.config.take_profit
                ):
                    self._close_position(pos_id, row, date_str, "止盈")

    def _close_position(
        self,
        pos_id: str,
        row,
        date_str: str,
        reason: str,
    ):
        """平仓"""
        pos = self.positions.get(pos_id)
        if not pos:
            return

        # 计算平仓价格（考虑滑点）
        if pos.side == PositionSide.LONG:
            close_price = row["close"] * (1 - self.config.slippage)
        else:
            close_price = row["close"] * (1 + self.config.slippage)

        # 计算手续费
        close_value = close_price * pos.quantity
        commission = self._calculate_commission(close_value)

        # 计算盈亏
        if pos.side == PositionSide.LONG:
            profit = (close_price - pos.avg_price) * pos.quantity - commission
        else:
            profit = (pos.avg_price - close_price) * pos.quantity - commission

        # 记录交易
        trade = Trade(
            id=f"t_{len(self.trades) + 1}",
            order_id="",
            code=pos.code,
            action=OrderAction.COVER if pos.side == PositionSide.SHORT else OrderAction.SELL,
            quantity=pos.quantity,
            price=close_price,
            total_value=close_value,
            commission=commission,
            profit=profit,
            created_at=pos.open_date,
            closed_at=date_str,
        )
        self.trades.append(trade)

        if profit > 0:
            self.winning_trades.append(trade)
        else:
            self.losing_trades.append(trade)

        # 更新资金
        self.cash += close_value - commission

        # 移除持仓
        del self.positions[pos_id]

    def _calculate_commission(self, value: float) -> float:
        """计算手续费"""
        if self.config.commission_mode == "none":
            return 0

        commission = value * self.config.commission_rate

        # 卖出时加印花税
        if self.config.commission_mode == "both":
            commission += value * self.config.stamp_tax_rate

        return max(commission, self.config.min_commission)

    def _check_orders(self, row, date_str: str):
        """检查挂单"""
        for order in list(self.orders):
            if order.status != TradeStatus.PENDING:
                continue

            # 限价单
            if order.order_type == OrderType.LIMIT:
                if order.action == OrderAction.BUY and row["low"] <= order.price:
                    self._fill_order(order, row["low"], date_str)
                elif (
                    order.action in [OrderAction.SELL, OrderAction.COVER]
                    and row["high"] >= order.price
                ):
                    self._fill_order(order, row["high"], date_str)

            # 止损单
            elif order.order_type == OrderType.STOP:
                if order.action == OrderAction.SELL and row["low"] <= order.stop_price:
                    self._fill_order(order, order.stop_price, date_str, is_stop=True)
                elif order.action == OrderAction.COVER and row["high"] >= order.stop_price:
                    self._fill_order(order, order.stop_price, date_str, is_stop=True)

    def _fill_order(self, order: Order, price: float, date_str: str, is_stop: bool = False):
        """执行订单"""
        # 检查每日交易次数
        if self.daily_trade_count.get(date_str, 0) >= self.config.max_trades_per_day:
            order.status = TradeStatus.CANCELLED
            return

        # 考虑滑点
        if order.action == OrderAction.BUY:
            fill_price = price * (1 + self.config.slippage)
        else:
            fill_price = price * (1 - self.config.slippage)

        # 计算买入金额
        order_value = fill_price * order.quantity

        # 检查资金
        if order.action == OrderAction.BUY and order_value > self.cash:
            order.status = TradeStatus.REJECTED
            return

        # 记录手续费
        commission = self._calculate_commission(order_value)

        # 更新资金
        self.cash -= order_value + commission

        # 创建持仓
        if order.action in [OrderAction.BUY, OrderAction.SHORT]:
            position = Position(
                code=order.code,
                side=PositionSide.LONG if order.action == OrderAction.BUY else PositionSide.SHORT,
                quantity=order.quantity,
                avg_price=fill_price,
                open_date=date_str,
                open_price=fill_price,
            )
            self.positions[order.code] = position

        # 更新订单状态
        order.status = TradeStatus.FILLED
        order.filled_at = date_str
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.commission = commission

        # 增加当日交易计数
        self.daily_trade_count[date_str] = self.daily_trade_count.get(date_str, 0) + 1
        self.last_trade_date = date_str

    def buy(
        self,
        code: str,
        quantity: int,
        price: float,
        date_str: str,
    ):
        """买入"""
        # 计算买入金额
        order_value = price * quantity

        # 检查仓位限制
        current_value = self.cash + sum(pos.quantity * price for pos in self.positions.values())
        target_value = current_value * self.config.position_size

        # 限制最大仓位
        target_value = min(target_value, self.config.initial_capital * self.config.max_position)

        # 计算实际买入数量
        quantity = min(quantity, int(target_value / price))

        if quantity <= 0:
            return None

        order = Order(
            id=f"o_{len(self.orders) + 1}",
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            code=code,
            quantity=quantity,
            price=price,
            created_at=date_str,
        )

        self.orders.append(order)
        return order

    def sell(
        self,
        code: str,
        quantity: int,
        price: float,
        date_str: str,
    ):
        """卖出"""
        if code not in self.positions:
            return None

        pos = self.positions[code]
        quantity = min(quantity, pos.quantity)

        if quantity <= 0:
            return None

        order = Order(
            id=f"o_{len(self.orders) + 1}",
            action=OrderAction.SELL,
            order_type=OrderType.MARKET,
            code=code,
            quantity=quantity,
            price=price,
            created_at=date_str,
        )

        self.orders.append(order)
        return order

    def _calculate_result(self) -> BacktestResult:
        """计算回测结果"""
        final_capital = self.cash + sum(
            pos.quantity * self.df.iloc[-1]["close"] for pos in self.positions.values()
        )

        total_return = final_capital - self.config.initial_capital
        total_return_pct = total_return / self.config.initial_capital

        # 计算年化收益率
        total_days = (self.df.iloc[-1]["date"] - self.df.iloc[0]["date"]).days
        annualized_return = (1 + total_return_pct) ** (365 / max(total_days, 1)) - 1

        # 计算波动率
        equity = [e["equity"] for e in self.equity_curve]
        returns = np.diff(equity) / equity[:-1]
        volatility = np.std(returns) * np.sqrt(252)

        # 计算夏普比率
        sharpe_ratio = (annualized_return - 0.03) / volatility if volatility > 0 else 0

        # 计算最大回撤
        peak = 0
        max_drawdown = 0
        for e in equity:
            if e > peak:
                peak = e
            drawdown = (peak - e) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 交易统计
        total_trades = len(self.trades)
        winning_trades = len(self.winning_trades)
        losing_trades = len(self.losing_trades)

        avg_win = np.mean([t.profit for t in self.winning_trades]) if self.winning_trades else 0
        avg_loss = np.mean([t.profit for t in self.losing_trades]) if self.losing_trades else 0

        profit_factor = (
            (avg_win * winning_trades) / abs(avg_loss * losing_trades)
            if losing_trades > 0
            else float("inf")
        )

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # 持仓统计
        max_position_held = max(len(self.positions.values()) if self.positions else 0)
        avg_position_held = total_trades / max(1, total_days)

        # 市场时间占比
        positions_held = sum(
            (self.df.iloc[min(i + 1, len(self.df) - 1)]["date"] - self.df.iloc[i]["date"]).days
            for i, e in enumerate(self.equity_curve[:-1])
            if i > 0 and any(p.unrealized_profit != 0 for p in self.positions.values())
        )
        time_in_market = positions_held / max(total_days, 1)

        return BacktestResult(
            backtest_id=self.backtest_id,
            code=self.df.iloc[-1].get("ts_code", ""),
            start_date=str(self.df.iloc[0]["date"]),
            end_date=str(self.df.iloc[-1]["date"]),
            total_days=total_days,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_position_held=max_position_held,
            avg_position_held=avg_position_held,
            time_in_market=time_in_market,
            trades=self.trades,
            daily_returns=self.daily_returns,
            equity_curve=self.equity_curve,
        )

    def _create_empty_result(self) -> BacktestResult:
        """创建空结果"""
        return BacktestResult(
            backtest_id=self.backtest_id,
            code="",
            start_date="",
            end_date="",
            total_days=0,
            initial_capital=self.config.initial_capital,
            final_capital=self.config.initial_capital,
            total_return=0,
            total_return_pct=0,
            annualized_return=0,
            volatility=0,
            sharpe_ratio=0,
            max_drawdown=0,
            max_drawdown_pct=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            avg_win=0,
            avg_loss=0,
            profit_factor=0,
            max_position_held=0,
            avg_position_held=0,
            time_in_market=0,
        )
