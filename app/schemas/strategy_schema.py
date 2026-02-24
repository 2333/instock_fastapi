from pydantic import BaseModel
from typing import Optional, List


class StrategyResponse(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None


class StrategyResultResponse(BaseModel):
    id: int
    date: Optional[str] = None
    strategy_name: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    score: Optional[float] = None
    signal: Optional[str] = None
    new_price: Optional[float] = None
    change_rate: Optional[float] = None
