from datetime import date

from pydantic import BaseModel


class IndicatorResponse(BaseModel):
    time: date | None = None
    code: str
    macd: float | None = None
    macds: float | None = None
    macdh: float | None = None
    kdjk: float | None = None
    kdjd: float | None = None
    kdjj: float | None = None
    boll_ub: float | None = None
    boll: float | None = None
    boll_lb: float | None = None
    rsi_6: float | None = None
    rsi_12: float | None = None
    rsi_24: float | None = None
    cr: float | None = None
    atr: float | None = None
    sar: float | None = None
