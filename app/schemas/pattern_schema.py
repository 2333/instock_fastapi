from pydantic import BaseModel
from datetime import date
from typing import Optional


class PatternResponse(BaseModel):
    time: Optional[date] = None
    code: str
    hammer: Optional[int] = None
    engulfing_pattern: Optional[int] = None
    morning_star: Optional[int] = None
    evening_star: Optional[int] = None
    doji: Optional[int] = None
