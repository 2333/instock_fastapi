from pydantic import BaseModel
from datetime import date
from typing import Optional


class IndicatorResponse(BaseModel):
    time: Optional[date] = None
    code: str
    macd: Optional[float] = None
    macds: Optional[float] = None
    macdh: Optional[float] = None
    kdjk: Optional[float] = None
    kdjd: Optional[float] = None
    kdjj: Optional[float] = None
    boll_ub: Optional[float] = None
    boll: Optional[float] = None
    boll_lb: Optional[float] = None
    rsi_6: Optional[float] = None
    rsi_12: Optional[float] = None
    rsi_24: Optional[float] = None
    cr: Optional[float] = None
    atr: Optional[float] = None
    sar: Optional[float] = None
