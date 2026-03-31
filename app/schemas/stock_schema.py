from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
    latest_trade_date: str | None = None
    latest_bar: "StockLatestBar | None" = None
    data_freshness: "StockDataFreshness | None" = None
    latest_indicator_snapshot: "StockIndicatorSnapshot | None" = None
    recent_patterns: "StockRecentPatternSummary | None" = None
    validation_context: "StockValidationContext | None" = None


class StockLatestBar(BaseModel):
    trade_date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    pre_close: float | None = None
    change: float | None = None
    change_rate: float | None = None
    vol: float | None = None
    amount: float | None = None


class StockDataFreshness(BaseModel):
    price_trade_date: str | None = None
    indicator_trade_date: str | None = None
    pattern_trade_date: str | None = None
    latest_trade_date: str | None = None
    price_current: bool = False
    indicator_current: bool = False
    pattern_current: bool = False


class StockIndicatorSnapshot(BaseModel):
    trade_date: str | None = None
    values: dict[str, float | None] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)


class StockPatternHit(BaseModel):
    trade_date: str | None = None
    pattern_name: str
    pattern_type: str | None = None
    confidence: float | None = None
    signal: str = "neutral"
    summary: str


class StockRecentPatternSummary(BaseModel):
    latest_trade_date: str | None = None
    hit_count: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    latest_hits: list[StockPatternHit] = Field(default_factory=list)


class StockValidationEvidence(BaseModel):
    metric: str
    trade_date: str | None = None
    value: str | int | float | bool | None = None
    summary: str
    source: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class StockValidationContext(BaseModel):
    as_of_trade_date: str | None = None
    screening_metrics: list[StockValidationEvidence] = Field(default_factory=list)
    pattern_annotations: list[StockValidationEvidence] = Field(default_factory=list)


StockDetailResponse.model_rebuild()


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
    group: str = Field(default="watch", description="Watchlist group")
    notes: str | None = None
    alert_conditions: dict[str, Any] | None = Field(default_factory=dict, description="Alert thresholds")
