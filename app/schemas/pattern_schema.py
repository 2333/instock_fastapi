from pydantic import BaseModel
from datetime import date
from typing import Optional


class PatternResponse(BaseModel):
    id: Optional[int] = None
    ts_code: Optional[str] = None
    trade_date: Optional[str] = None
    pattern_name: Optional[str] = None
    pattern_type: Optional[str] = None
    confidence: Optional[float] = None
    stock_name: Optional[str] = None
    code: Optional[str] = None
