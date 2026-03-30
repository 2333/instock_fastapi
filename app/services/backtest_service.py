from decimal import Decimal
from math import sqrt
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import BacktestResult


class BacktestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(
        self, params: dict[str, Any], user_id: int | None = None
    ) -> dict[str, Any]:
        code = str(params.get("stock_code") or params.get("code") or "").strip()
        start_date = str(params.get("start_date") or "").strip()
        end_date = str(params.get("end_date") or "").strip()
        initial_capital = float(params.get("initial_capital") or 100000)
        strategy_name = str(params.get("strategy") or "buy_hold")
        strategy_params = params.get("strategy_params") or {}

        if not code or not start_date or not end_date:
            return {
                "backtest_id": None,
                "status": "failed",
                "error": "missing_required_params",
                "debug_user_id": user_id,
            }

        stock_sql = text("""
            SELECT ts_code, symbol, name
            FROM stocks
            WHERE symbol = :code OR ts_code = :code
            LIMIT 1
            """)
        stock_row = (await self.db.execute(stock_sql, {"code": code})).mappings().first()
        if not stock_row:
            return {"backtest_id": None, "status": "failed", "error": "stock_not_found"}

        # 获取完整日线数据
        bars_sql = text("""
            SELECT trade_date, open, high, low, close, vol
            FROM daily_bars
            WHERE ts_code = :ts_code
            AND trade_date BETWEEN :start_date AND :end_date
            ORDER BY trade_date ASC
            """)
        bars = (
            (
                await self.db.execute(
                    bars_sql,
                    {
                        "ts_code": stock_row["ts_code"],
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
            )
            .mappings()
            .all()
        )

        if len(bars) < 2:
            return {
                "backtest_id": None,
                "status": "completed",
                "summary": {
                    "initial_capital": initial_capital,
                    "final_capital": initial_capital,
                    "total_return": 0.0,
                    "annual_return": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "win_rate": 0.0,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "profit_factor": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                },
                "equity_curve": [],
                "trades": [],
                "note": "not_enough_bars",
            }

        # 根据策略生成信号
        if strategy_name == "buy_hold":
            signals = self._buy_hold_signals(bars)
        elif strategy_name == "ma_crossover":
            signals = self._ma_crossover_signals(bars, strategy_params)
        elif strategy_name == "rsi_oversold":
            signals = self._rsi_oversold_signals(bars, strategy_params)
        else:
            # 未知策略回退到买入持有
            signals = self._buy_hold_signals(bars)

        # 执行回测模拟
        equity_curve, trades = self._simulate_backtest(bars, signals, initial_capital)

        # 计算汇总指标
        final_capital = equity_curve[-1]["equity"] if equity_curve else initial_capital
        total_return = ((final_capital - initial_capital) / initial_capital) if initial_capital else 0.0
        years = max(len(bars) / 252.0, 1 / 252.0)
        annual_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1.0

        # 计算最大回撤和每日收益
        max_equity = initial_capital
        max_drawdown = 0.0
        daily_returns = []
        last_equity = initial_capital
        for point in equity_curve:
            equity = point["equity"]
            if equity > max_equity:
                max_equity = equity
            dd = (equity - max_equity) / max_equity if max_equity > 0 else 0.0
            if dd < max_drawdown:
                max_drawdown = dd
            # 计算每日收益（从第二个点开始）
            if last_equity > 0 and equity != last_equity:
                daily_returns.append((equity - last_equity) / last_equity)
            last_equity = equity

        # 计算夏普比率
        sharpe = 0.0
        if daily_returns:
            mean_ret = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
            std = sqrt(variance)
            if std > 0:
                sharpe = (mean_ret / std) * sqrt(252)

        # 统计交易
        winning_trades = sum(1 for t in trades if t["type"] == "SELL" and t["profit"] > 0)
        losing_trades = sum(1 for t in trades if t["type"] == "SELL" and t["profit"] < 0)
        total_trades = winning_trades + losing_trades
        profit_factor = 0.0
        total_profit = sum(t["profit"] for t in trades if t["type"] == "SELL" and t["profit"] > 0)
        total_loss = abs(sum(t["profit"] for t in trades if t["type"] == "SELL" and t["profit"] < 0))
        if total_loss > 0:
            profit_factor = total_profit / total_loss
        avg_win = total_profit / winning_trades if winning_trades else 0.0
        avg_loss = -total_loss / losing_trades if losing_trades else 0.0
        win_rate = (winning_trades / total_trades * 100) if total_trades else 0.0

        result = {
            "backtest_id": f"bt_{stock_row['symbol']}_{start_date}_{end_date}",
            "status": "completed",
            "summary": {
                "initial_capital": round(initial_capital, 2),
                "final_capital": round(final_capital, 2),
                "total_return": round(total_return * 100, 4),
                "annual_return": round(annual_return * 100, 4),
                "max_drawdown": round(max_drawdown * 100, 4),
                "sharpe_ratio": round(sharpe, 4),
                "win_rate": round(win_rate, 4),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "profit_factor": round(profit_factor, 4),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
            },
            "equity_curve": equity_curve,
            "trades": trades,
            "meta": {
                "code": stock_row["symbol"],
                "name": stock_row["name"],
                "strategy": strategy_name,
                "strategy_params": strategy_params,
            },
        }

        if user_id:
            try:
                backtest_record = BacktestResult(
                    user_id=user_id,
                    name=f"{stock_row['symbol']} {start_date}~{end_date}",
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=Decimal(str(round(initial_capital, 2))),
                    final_capital=Decimal(str(round(final_capital, 2))),
                    total_return=Decimal(str(round(total_return * 100, 4))),
                    annual_return=Decimal(str(round(annual_return * 100, 4))),
                    max_drawdown=Decimal(str(round(max_drawdown * 100, 4))),
                    sharpe_ratio=Decimal(str(round(sharpe, 4))),
                    win_rate=Decimal(str(round(win_rate, 4))),
                    total_trades=total_trades,
                    result_data={
                        "equity_curve": equity_curve,
                        "trades": trades,
                        "summary": result["summary"],
                        "meta": result["meta"],
                    },
                )
                self.db.add(backtest_record)
                await self.db.commit()
                await self.db.refresh(backtest_record)
                result["backtest_id"] = str(backtest_record.id)
                result["saved_to_db"] = True
            except Exception as e:
                result["saved_to_db"] = False
                result["save_error"] = str(e)
        else:
            result["saved_to_db"] = False

        return result

    async def list_results(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        query = text("""
            SELECT
                id,
                name,
                start_date,
                end_date,
                initial_capital,
                final_capital,
                total_return,
                annual_return,
                max_drawdown,
                sharpe_ratio,
                win_rate,
                total_trades,
                created_at,
                result_data
            FROM backtest_results
            WHERE user_id = :user_id
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"user_id": user_id, "limit": limit})
        rows = result.mappings().all()
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = row.get("result_data") or {}
            summary = payload.get("summary") or {}
            meta = payload.get("meta") or {}
            items.append(
                {
                    "id": str(row.get("id")),
                    "name": row.get("name") or meta.get("strategy") or "backtest",
                    "start_date": row.get("start_date"),
                    "end_date": row.get("end_date"),
                    "initial_capital": float(row.get("initial_capital"))
                    if row.get("initial_capital") is not None
                    else 0.0,
                    "final_capital": float(row.get("final_capital"))
                    if row.get("final_capital") is not None
                    else None,
                    "strategy": meta.get("strategy"),
                    "code": meta.get("code"),
                    "stock_name": meta.get("name"),
                    "total_return": float(row.get("total_return"))
                    if row.get("total_return") is not None
                    else summary.get("total_return"),
                    "annual_return": float(row.get("annual_return"))
                    if row.get("annual_return") is not None
                    else summary.get("annual_return"),
                    "max_drawdown": float(row.get("max_drawdown"))
                    if row.get("max_drawdown") is not None
                    else summary.get("max_drawdown"),
                    "sharpe_ratio": float(row.get("sharpe_ratio"))
                    if row.get("sharpe_ratio") is not None
                    else summary.get("sharpe_ratio"),
                    "win_rate": float(row.get("win_rate"))
                    if row.get("win_rate") is not None
                    else summary.get("win_rate"),
                    "total_trades": row.get("total_trades")
                    if row.get("total_trades") is not None
                    else summary.get("total_trades"),
                    "created_at": row.get("created_at"),
                }
            )
        return items

    async def get_result(self, backtest_id: str, user_id: int | None = None) -> dict[str, Any]:
        if user_id:
            query = text("""
                SELECT * FROM backtest_results
                WHERE user_id = :user_id
                AND (
                    CAST(id AS TEXT) = :backtest_id
                    OR result_data->>'external_backtest_id' = :backtest_id
                )
                LIMIT 1
            """)
            result = await self.db.execute(
                query,
                {"user_id": user_id, "backtest_id": backtest_id},
            )
            row = result.fetchone()
            if row:
                return {"backtest_id": str(row[0]), "status": "completed", "data": row._mapping}
        return {"backtest_id": backtest_id, "status": "not_found"}

    # 策略信号生成方法

    def _buy_hold_signals(self, bars: list[dict]) -> list[dict]:
        """买入持有策略：第一天买入，最后一天卖出"""
        signals = []
        for i, bar in enumerate(bars):
            signal = "HOLD"
            if i == 0:
                signal = "BUY"
            elif i == len(bars) - 1:
                signal = "SELL"
            signals.append({"date": bar["trade_date"], "signal": signal, "price": float(bar["close"])})
        return signals

    def _ma_crossover_signals(self, bars: list[dict], params: dict) -> list[dict]:
        """移动平均交叉策略"""
        fast = int(params.get("fast_ma", 5))
        slow = int(params.get("slow_ma", 20))
        closes = [float(bar["close"]) for bar in bars]
        signals = []
        position = 0  # 0=空仓, 1=持仓

        for i, bar in enumerate(bars):
            if i < slow - 1:
                # 数据不足时保持HOLD
                signals.append({"date": bar["trade_date"], "signal": "HOLD", "price": float(bar["close"])})
                continue

            fast_ma = sum(closes[i-fast+1:i+1]) / fast
            slow_ma = sum(closes[i-slow+1:i+1]) / slow

            signal = "HOLD"
            if fast_ma > slow_ma and position == 0:
                signal = "BUY"
                position = 1
            elif fast_ma < slow_ma and position == 1:
                signal = "SELL"
                position = 0

            signals.append({"date": bar["trade_date"], "signal": signal, "price": float(bar["close"])})

        # 如果整个周期都没有产生任何买卖信号（数据不足），回退到买入持有
        if not any(s["signal"] in ("BUY", "SELL") for s in signals):
            return self._buy_hold_signals(bars)

        # 最后一天强制卖出
        if position == 1:
            signals[-1]["signal"] = "SELL"
        return signals

    def _rsi_oversold_signals(self, bars: list[dict], params: dict) -> list[dict]:
        """RSI超卖策略：RSI低于超卖线买入，高于阈值卖出"""
        period = int(params.get("rsi_period", 14))
        oversold = float(params.get("oversold_level", 30))
        overbought = float(params.get("overbought_level", 70))
        closes = [float(bar["close"]) for bar in bars]
        signals = []
        position = 0

        for i, bar in enumerate(bars):
            if i < period:
                signals.append({"date": bar["trade_date"], "signal": "HOLD", "price": float(bar["close"])})
                continue

            gains = []
            losses = []
            for j in range(i - period + 1, i + 1):
                change = closes[j] - closes[j-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            avg_gain = sum(gains) / period if gains else 0
            avg_loss = sum(losses) / period if losses else 0.0001
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            signal = "HOLD"
            if rsi <= oversold and position == 0:
                signal = "BUY"
                position = 1
            elif rsi >= overbought and position == 1:
                signal = "SELL"
                position = 0

            signals.append({"date": bar["trade_date"], "signal": signal, "price": float(bar["close"])})

        # 如果整个周期都没有产生任何买卖信号，回退到买入持有
        if not any(s["signal"] in ("BUY", "SELL") for s in signals):
            return self._buy_hold_signals(bars)

        if position == 1:
            signals[-1]["signal"] = "SELL"
        return signals

    def _simulate_backtest(self, bars: list[dict], signals: list[dict], initial_capital: float) -> tuple[list[dict], list[dict]]:
        """根据信号模拟回测，返回资金曲线和交易记录"""
        equity_curve = []
        trades = []
        cash = initial_capital
        shares = 0
        last_equity = initial_capital
        max_equity = initial_capital
        trade_id = 0

        for i, bar in enumerate(bars):
            date = bar["trade_date"]
            price = float(bar["close"])
            signal = signals[i]["signal"]

            # 执行交易（T+1逻辑简化：信号当日收盘价成交）
            if signal == "BUY" and shares == 0:
                # 全仓买入
                buy_shares = int(cash // price)
                if buy_shares > 0:
                    cost = buy_shares * price
                    cash -= cost
                    shares = buy_shares
                    trade_id += 1
                    trades.append({
                        "id": trade_id,
                        "date": date,
                        "type": "BUY",
                        "price": round(price, 4),
                        "quantity": buy_shares,
                        "profit": 0.0,
                        "return_pct": 0.0,
                        "hold_days": 0,
                    })
            elif signal == "SELL" and shares > 0:
                # 全仓卖出
                proceeds = shares * price
                cash += proceeds
                # 计算这笔交易的盈亏
                # 找到对应的买入交易
                buy_trades = [t for t in trades if t["type"] == "BUY" and t["id"] <= trade_id]
                if buy_trades:
                    last_buy = buy_trades[-1]
                    profit = proceeds - (last_buy["price"] * last_buy["quantity"])
                    return_pct = ((price - last_buy["price"]) / last_buy["price"]) * 100 if last_buy["price"] else 0.0
                    hold_days = i - next((idx for idx, t in enumerate(trades) if t["id"] == last_buy["id"]), 0)
                else:
                    profit = 0.0
                    return_pct = 0.0
                    hold_days = 0
                trade_id += 1
                trades.append({
                    "id": trade_id,
                    "date": date,
                    "type": "SELL",
                    "price": round(price, 4),
                    "quantity": shares,
                    "profit": round(profit, 2),
                    "return_pct": round(return_pct, 4),
                    "hold_days": hold_days,
                })
                shares = 0

            equity = cash + shares * price
            equity_curve.append({
                "date": date,
                "equity": round(equity, 2),
                "benchmark": 0.0,  # 后面再填充
            })
            last_equity = equity
            max_equity = max(max_equity, equity)

        # 填充benchmark（买入持有基准）和equity_curve的benchmark字段
        if bars:
            first_price = float(bars[0]["close"])
            for point in equity_curve:
                # 假设当天价格相对于首日的涨幅
                price = float(next((b["close"] for b in bars if b["trade_date"] == point["date"]), first_price))
                if first_price > 0:
                    point["benchmark"] = round(initial_capital * (price / first_price), 2)
                else:
                    point["benchmark"] = initial_capital

        return equity_curve, trades
