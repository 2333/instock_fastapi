from pydantic import BaseModel


class StrategyResponse(BaseModel):
    name: str
    display_name: str
    description: str | None = None


class StrategyResultResponse(BaseModel):
    id: int
    date: str | None = None
    strategy_name: str | None = None
    code: str | None = None
    name: str | None = None
    score: float | None = None
    signal: str | None = None
    new_price: float | None = None
    change_rate: float | None = None
