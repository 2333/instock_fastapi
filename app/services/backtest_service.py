from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
from math import sqrt


class BacktestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        code = str(params.get("stock_code") or params.get("code") or "").strip()
        start_date = str(params.get("start_date") or "").strip()
        end_date = str(params.get("end_date") or "").strip()
        initial_capital = float(params.get("initial_capital") or 100000)

        if not code or not start_date or not end_date:
            return {
                "backtest_id": None,
                "status": "failed",
                "error": "missing_required_params",
            }

        stock_sql = text(
            """
            SELECT ts_code, symbol, name
            FROM stocks
            WHERE symbol = :code OR ts_code = :code
            LIMIT 1
            """
        )
        stock_row = (await self.db.execute(stock_sql, {"code": code})).mappings().first()
        if not stock_row:
            return {"backtest_id": None, "status": "failed", "error": "stock_not_found"}

        bars_sql = text(
            """
            SELECT trade_date, close
            FROM daily_bars
            WHERE ts_code = :ts_code
              AND trade_date BETWEEN :start_date AND :end_date
            ORDER BY trade_date ASC
            """
        )
        bars = (
            await self.db.execute(
                bars_sql,
                {
                    "ts_code": stock_row["ts_code"],
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        ).mappings().all()

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

        first_price = float(bars[0]["close"])
        shares = int(initial_capital // first_price) if first_price > 0 else 0
        cash = initial_capital - shares * first_price

        equity_curve = []
        daily_returns = []
        last_equity = initial_capital
        max_equity = initial_capital
        max_drawdown = 0.0

        for i, bar in enumerate(bars):
            close = float(bar["close"])
            equity = cash + shares * close
            benchmark = initial_capital * (close / first_price) if first_price > 0 else initial_capital
            equity_curve.append(
                {
                    "date": bar["trade_date"],
                    "equity": round(equity, 2),
                    "benchmark": round(benchmark, 2),
                }
            )
            if i > 0 and last_equity > 0:
                daily_returns.append((equity - last_equity) / last_equity)
            last_equity = equity
            if equity > max_equity:
                max_equity = equity
            if max_equity > 0:
                dd = (equity - max_equity) / max_equity
                if dd < max_drawdown:
                    max_drawdown = dd

        final_capital = equity_curve[-1]["equity"]
        total_return = (final_capital - initial_capital) / initial_capital if initial_capital else 0.0
        years = max(len(bars) / 252.0, 1 / 252.0)
        annual_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1.0

        sharpe = 0.0
        if daily_returns:
            mean_ret = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
            std = sqrt(variance)
            if std > 0:
                sharpe = (mean_ret / std) * sqrt(252)

        buy_trade = {
            "id": 1,
            "date": bars[0]["trade_date"],
            "type": "BUY",
            "price": round(first_price, 4),
            "quantity": shares,
            "profit": 0.0,
            "return_pct": 0.0,
            "hold_days": 0,
        }
        sell_price = float(bars[-1]["close"])
        trade_profit = (sell_price - first_price) * shares
        sell_trade = {
            "id": 2,
            "date": bars[-1]["trade_date"],
            "type": "SELL",
            "price": round(sell_price, 4),
            "quantity": shares,
            "profit": round(trade_profit, 2),
            "return_pct": round(((sell_price - first_price) / first_price) * 100 if first_price else 0.0, 4),
            "hold_days": max(len(bars) - 1, 0),
        }

        winning_trades = 1 if trade_profit > 0 else 0
        losing_trades = 1 if trade_profit < 0 else 0
        profit_factor = abs(trade_profit) / abs(trade_profit) if trade_profit != 0 else 0.0
        if trade_profit <= 0:
            profit_factor = 0.0

        return {
            "backtest_id": f"bt_{stock_row['symbol']}_{start_date}_{end_date}",
            "status": "completed",
            "summary": {
                "initial_capital": round(initial_capital, 2),
                "final_capital": round(final_capital, 2),
                "total_return": round(total_return * 100, 4),
                "annual_return": round(annual_return * 100, 4),
                "max_drawdown": round(max_drawdown * 100, 4),
                "sharpe_ratio": round(sharpe, 4),
                "win_rate": round((winning_trades / max(winning_trades + losing_trades, 1)) * 100, 4),
                "total_trades": 1,
                "winning_trades": winning_trades,
                "profit_factor": round(profit_factor, 4),
                "avg_win": round(trade_profit if trade_profit > 0 else 0.0, 2),
                "avg_loss": round(trade_profit if trade_profit < 0 else 0.0, 2),
            },
            "equity_curve": equity_curve,
            "trades": [buy_trade, sell_trade],
            "meta": {
                "code": stock_row["symbol"],
                "name": stock_row["name"],
                "strategy": params.get("strategy") or "buy_hold",
            },
        }

    async def get_result(self, backtest_id: str) -> Dict[str, Any]:
        return {"backtest_id": backtest_id, "status": "completed"}
