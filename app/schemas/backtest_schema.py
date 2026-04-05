from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BacktestCurvePoint(BaseModel):
    date: str
    equity: float
    benchmark: float


class BacktestTradeItem(BaseModel):
    id: int
    date: str
    type: str
    price: float
    quantity: int
    profit: float
    return_pct: float
    hold_days: int


class BacktestPerformanceSummary(BaseModel):
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    profit_factor: float
    avg_win: float
    avg_loss: float


class BacktestBenchmarkSummary(BaseModel):
    name: str
    code: str | None = None
    source: str
    description: str
    initial_value: float
    final_value: float
    total_return: float
    excess_return: float
    series: list[dict[str, Any]] = Field(default_factory=list)
    period: dict[str, str | None] = Field(default_factory=dict)


class BacktestRiskSummary(BaseModel):
    max_drawdown: float
    max_consecutive_loss_days: int
    max_single_day_loss: float
    closed_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float
    profit_factor: float
    risk_level: str
    risk_notes: list[str] = Field(default_factory=list)


class BacktestReport(BaseModel):
    performance: BacktestPerformanceSummary
    benchmark: BacktestBenchmarkSummary
    risk: BacktestRiskSummary
    equity_curve: list[BacktestCurvePoint] = Field(default_factory=list)
    trades: list[BacktestTradeItem] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class BacktestHistoryItem(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float | None = None
    total_return: float | None = None
    annual_return: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    code: str | None = None
    stock_name: str | None = None
    strategy: str | None = None
    benchmark_name: str | None = None
    risk_level: str | None = None
    report: BacktestReport | None = None
    created_at: datetime | None = None


class BacktestHistoryResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[BacktestHistoryItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BacktestDetailResponse(BaseModel):
    backtest_id: str | None = None
    id: str | None = None
    status: str = "completed"
    summary: BacktestPerformanceSummary | None = None
    report: BacktestReport | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
