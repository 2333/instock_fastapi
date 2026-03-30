from datetime import datetime

from pydantic import BaseModel, Field


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
    created_at: datetime | None = None


class BacktestHistoryResponse(BaseModel):
    success: bool = True
    code: str = "SUCCESS"
    message: str = "OK"
    data: list[BacktestHistoryItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
