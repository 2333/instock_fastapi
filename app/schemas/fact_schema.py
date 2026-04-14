from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DailyBasicResponse(BaseModel):
    id: int
    ts_code: str
    trade_date: str
    trade_date_dt: date
    turnover_rate: float | None = None
    turnover_rate_f: float | None = None
    volume_ratio: float | None = None
    pe: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None
    ps_ttm: float | None = None
    dv_ratio: float | None = None
    dv_ttm: float | None = None
    total_share: float | None = None
    float_share: float | None = None
    free_share: float | None = None
    total_mv: float | None = None
    circ_mv: float | None = None
    created_at: datetime | None = None


class StockSTResponse(BaseModel):
    id: int
    ts_code: str
    trade_date: str
    trade_date_dt: date
    name: str | None = None
    st_type: str | None = None
    reason: str | None = None
    begin_date: str | None = None
    end_date: str | None = None
    created_at: datetime | None = None


class TechnicalFactorResponse(BaseModel):
    id: int
    ts_code: str
    trade_date: str
    trade_date_dt: date
    factors: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
