from datetime import datetime

from pydantic import BaseModel


class StockSpotResponse(BaseModel):
    date: str | None = None
    code: str | None = None
    name: str | None = None
    new_price: float | None = None
    change_rate: float | None = None
    ups_downs: float | None = None
    volume: int | None = None
    deal_amount: int | None = None
    turnoverrate: float | None = None
    industry: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    pre_close: float | None = None
    vol: float | None = None
    amount: float | None = None
    ts_code: str | None = None
    symbol: str | None = None
    exchange: str | None = None
    area: str | None = None
    market: str | None = None
    list_status: str | None = None
    list_date: str | None = None
    is_etf: bool | None = None
    bars: list | None = None
    adjust_requested: str | None = None
    adjust_applied: str | None = None
    adjust_note: str | None = None


class StockDetailResponse(StockSpotResponse):
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    pre_close_price: float | None = None
    pe9: float | None = None
    pbnewmrq: float | None = None
    total_market_cap: int | None = None
    free_cap: int | None = None
    listing_date: str | None = None


class EtfSpotResponse(BaseModel):
    date: str | None = None
    code: str | None = None
    name: str | None = None
    new_price: float | None = None
    change_rate: float | None = None
    volume: int | None = None
    deal_amount: int | None = None


class FundFlowResponse(BaseModel):
    time: str | None = None
    code: str
    name: str | None = None
    fund_amount: int | None = None
    fund_rate: float | None = None


class AttentionResponse(BaseModel):
    id: int
    code: str | None = None
    name: str | None = None
    created_at: datetime | None = None
    ts_code: str | None = None
    stock_name: str | None = None
