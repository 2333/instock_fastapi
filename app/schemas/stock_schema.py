from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class StockSpotResponse(BaseModel):
    date: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    new_price: Optional[float] = None
    change_rate: Optional[float] = None
    ups_downs: Optional[float] = None
    volume: Optional[int] = None
    deal_amount: Optional[int] = None
    turnoverrate: Optional[float] = None
    industry: Optional[str] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    pre_close: Optional[float] = None
    vol: Optional[float] = None
    amount: Optional[float] = None
    ts_code: Optional[str] = None
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    area: Optional[str] = None
    market: Optional[str] = None
    list_status: Optional[str] = None
    list_date: Optional[str] = None
    is_etf: Optional[bool] = None
    bars: Optional[list] = None
    adjust_requested: Optional[str] = None
    adjust_applied: Optional[str] = None
    adjust_note: Optional[str] = None


class StockDetailResponse(StockSpotResponse):
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    pre_close_price: Optional[float] = None
    pe9: Optional[float] = None
    pbnewmrq: Optional[float] = None
    total_market_cap: Optional[int] = None
    free_cap: Optional[int] = None
    listing_date: Optional[str] = None


class EtfSpotResponse(BaseModel):
    date: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    new_price: Optional[float] = None
    change_rate: Optional[float] = None
    volume: Optional[int] = None
    deal_amount: Optional[int] = None


class FundFlowResponse(BaseModel):
    time: Optional[str] = None
    code: str
    name: Optional[str] = None
    fund_amount: Optional[int] = None
    fund_rate: Optional[float] = None


class AttentionResponse(BaseModel):
    id: int
    code: Optional[str] = None
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    ts_code: Optional[str] = None
    stock_name: Optional[str] = None
